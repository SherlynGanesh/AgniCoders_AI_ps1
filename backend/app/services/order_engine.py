import logging
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status

from backend.app.models.entities import (
    Order, OrderItem, Inventory, ProductVariant, Product,
    Clarification, AIDecision, Alias
)
from backend.app.schemas.domain import (
    BillDiffItem, OrderExplanationResponse, WhatIfResponse, WhatIfOption
)
from backend.app.services.ai_service import ai_service
from backend.app.services.product_matching import product_matcher
from backend.app.services.clarification_service import clarification_service
from backend.app.services.billing_service import billing_service
from backend.app.services.inventory_service import inventory_service
from backend.data_ingestion.normalization import normalize_text

logger = logging.getLogger("dukaanmitra.order_engine")


class OrderEngine:

    def create_and_analyze_order(
        self,
        db: Session,
        shop_id: int,
        raw_input: str,
        customer_id: Optional[int] = None
    ) -> Order:
        """
        Orchestrates full order lifecycle:
        Input -> AI Parse -> Entity Match -> Ambiguity -> DB Persist.
        """
        parsed_result = ai_service.parse_order(raw_input)

        order = Order(
            shop_id=shop_id,
            customer_id=customer_id,
            status="DRAFT",
            subtotal=Decimal("0.00"),
            discount=Decimal("0.00"),
            tax=Decimal("0.00"),
            total=Decimal("0.00"),
            raw_input=raw_input,
            confidence=Decimal("0.90")
        )
        db.add(order)
        db.flush()  # Assign order.id

        has_clarifications = False
        min_confidence = Decimal("1.00")

        for item in parsed_result.items:
            best_match, alternatives, match_status = product_matcher.match_item(db, shop_id, item)

            item_conf = Decimal(str(round(item.confidence, 3)))
            if item_conf < min_confidence:
                min_confidence = item_conf

            # Log AI decision
            ai_decision = AIDecision(
                order_id=order.id,
                raw_text=item.raw_text,
                parsed_output=item.model_dump(),
                confidence=item_conf,
                decision=match_status,
                reason=f"Status: {match_status} via matching engine."
            )
            db.add(ai_decision)

            if match_status == "MATCHED" and best_match:
                # Add item to order
                item_total = billing_service.quantize_money(best_match.price * Decimal(item.quantity))
                order_item = OrderItem(
                    order_id=order.id,
                    variant_id=best_match.variant_id,
                    quantity=item.quantity,
                    unit_price=best_match.price,
                    total_price=item_total,
                    confidence=Decimal(str(best_match.match_score))
                )
                db.add(order_item)

            elif match_status in {"AMBIGUOUS", "OUT_OF_STOCK"}:
                has_clarifications = True
                clarification_service.create_clarification(
                    db,
                    order_id=order.id,
                    ambiguous_text=item.product or item.raw_text,
                    candidates=alternatives
                )

        # Set final status
        order.status = "CLARIFICATION_REQUIRED" if has_clarifications else "READY"
        order.confidence = min_confidence

        db.commit()
        db.refresh(order)

        # Recalculate bill
        billing_service.recalculate_order_bill(db, order.id)
        db.refresh(order)
        order._ai_parsed = parsed_result
        return order

    def resolve_order_clarification(
        self,
        db: Session,
        order_id: int,
        clarification_id: int,
        selected_variant_id: int
    ) -> Order:
        """
        Resolves an ambiguity question, updates order items, updates shop memory.
        """
        order = db.query(Order).filter_by(id=order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        clarification = db.query(Clarification).filter_by(id=clarification_id, order_id=order_id).first()
        if not clarification:
            raise HTTPException(status_code=404, detail="Clarification not found for this order")

        variant = db.query(ProductVariant).filter_by(id=selected_variant_id).first()
        if not variant:
            raise HTTPException(status_code=404, detail="Selected variant does not exist")

        # Resolve clarification
        clarification.selected_variant_id = selected_variant_id
        clarification.resolved = True
        clarification.resolved_at = func.now()

        # Add OrderItem for resolved variant (default quantity 1)
        item_total = billing_service.quantize_money(variant.price * Decimal(1))
        order_item = OrderItem(
            order_id=order.id,
            variant_id=variant.id,
            quantity=1,
            unit_price=variant.price,
            total_price=item_total,
            confidence=Decimal("0.98")
        )
        db.add(order_item)

        # -------------------------------------------------------------
        # Shop Memory (Alias) Learning
        # -------------------------------------------------------------
        norm_alias = normalize_text(clarification.ambiguous_text)
        alias = (
            db.query(Alias)
            .filter_by(shop_id=order.shop_id, normalized_alias=norm_alias, variant_id=variant.id)
            .first()
        )
        if alias:
            alias.usage_count += 1
            alias.confidence = min(Decimal("0.98"), alias.confidence + Decimal("0.05"))
            alias.last_used_at = func.now()
        else:
            new_alias = Alias(
                shop_id=order.shop_id,
                variant_id=variant.id,
                alias_text=clarification.ambiguous_text,
                normalized_alias=norm_alias,
                confidence=Decimal("0.85"),
                source="SHOPKEEPER",
                usage_count=1
            )
            db.add(new_alias)

        # Check remaining unresolved clarifications
        unresolved = (
            db.query(Clarification)
            .filter(Clarification.order_id == order_id, Clarification.resolved == False)
            .count()
        )
        if unresolved <= 1:  # Current one is resolved
            order.status = "READY"

        db.commit()
        billing_service.recalculate_order_bill(db, order.id)
        db.refresh(order)
        return order

    def confirm_order_with_transaction(self, db: Session, order_id: int) -> Order:
        """
        Executes ACID PostgreSQL transaction:
        1. Row locks inventory with SELECT ... FOR UPDATE.
        2. Validates stock for all items.
        3. Deducts inventory.
        4. Marks order CONFIRMED.
        5. Commits or Rollbacks on error.
        """
        order = db.query(Order).filter_by(id=order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        if order.status == "CONFIRMED":
            raise HTTPException(status_code=400, detail="Order is already confirmed")

        if order.status == "CLARIFICATION_REQUIRED":
            raise HTTPException(
                status_code=400,
                detail="Cannot confirm order with pending ambiguities. Please resolve clarifications first."
            )

        if not order.items:
            raise HTTPException(status_code=400, detail="Cannot confirm order with zero items")

        try:
            # Build list of items to deduct
            requested_items = [(itm.variant_id, itm.quantity) for itm in order.items]

            # Lock rows and verify stock
            locked_inventories = inventory_service.check_and_lock_inventory(
                db, order.shop_id, requested_items
            )

            # Deduct stock
            inventory_service.deduct_stock(locked_inventories, requested_items)

            # Update order status
            order.status = "CONFIRMED"
            order.confirmed_at = func.now()

            # Record AI decision log
            confirm_decision = AIDecision(
                order_id=order.id,
                raw_text=order.raw_input,
                parsed_output={"status": "CONFIRMED", "items_count": len(order.items)},
                confidence=Decimal("1.00"),
                decision="CONFIRMED",
                reason="Order verified and confirmed via PostgreSQL transaction."
            )
            db.add(confirm_decision)

            db.commit()
            db.refresh(order)
            return order

        except Exception as e:
            db.rollback()
            logger.error(f"Transaction failed for order {order_id}: {e}")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=500, detail=f"Database transaction failure: {str(e)}")

    def explain_order(self, db: Session, order_id: int) -> OrderExplanationResponse:
        """
        Generates Bill Diff Explainability:
        Customer Said vs AI Understood vs Catalog Match vs Stock vs Price vs Confidence.
        """
        order = db.query(Order).filter_by(id=order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        diff_items = []
        for item in order.items:
            variant = item.variant
            prod = variant.product
            inv = db.query(Inventory).filter_by(shop_id=order.shop_id, variant_id=variant.id).first()
            stock = inv.quantity if inv else 0

            diff_items.append(BillDiffItem(
                customer_said=order.raw_input,
                ai_understood=f"{prod.name} ({variant.variant_label}), Qty: {item.quantity}",
                catalog_match=f"{prod.name} - {prod.brand or ''} [{variant.variant_label}]",
                variant_id=variant.id,
                stock=stock,
                unit_price=item.unit_price,
                quantity=item.quantity,
                item_total=item.total_price,
                confidence=float(item.confidence or 0.95),
                status="MATCHED"
            ))

        return OrderExplanationResponse(
            order_id=order.id,
            raw_input=order.raw_input,
            overall_status=order.status,
            diff_items=diff_items,
            clarifications=order.clarifications
        )

    def what_if_comparison(self, db: Session, order_id: int) -> WhatIfResponse:
        """
        Compares price implications between ambiguous variants before user confirms.
        """
        order = db.query(Order).filter_by(id=order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        clarification = db.query(Clarification).filter_by(order_id=order_id, resolved=False).first()
        if not clarification:
            raise HTTPException(status_code=400, detail="No active ambiguity for What-If comparison")

        options = []
        for opt in clarification.options:
            price_dec = Decimal(str(opt["price"]))
            options.append(WhatIfOption(
                variant_id=opt["variant_id"],
                variant_label=opt["label"],
                price=price_dec,
                quantity=1,
                total_price=price_dec,
                stock=opt.get("stock", 0)
            ))

        return WhatIfResponse(
            order_id=order_id,
            ambiguous_item=clarification.ambiguous_text,
            options=options
        )


order_engine = OrderEngine()
