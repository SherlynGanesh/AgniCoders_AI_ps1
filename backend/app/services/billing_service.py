from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from backend.app.models.entities import OrderItem


class BillingService:

    @staticmethod
    def quantize_money(amount: Decimal) -> Decimal:
        """Rounds amount to 2 decimal places using standard financial round half up."""
        return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def calculate_bill(
        self,
        items: List[Dict[str, Any]],
        discount_pct: Decimal = Decimal("0.00"),
        tax_pct: Decimal = Decimal("0.00")
    ) -> Tuple[Decimal, Decimal, Decimal, Decimal]:
        """
        Calculates server-side financial totals with absolute precision.
        Returns: (subtotal, discount, tax, total)
        """
        subtotal = Decimal("0.00")

        for itm in items:
            unit_price = Decimal(str(itm.get("unit_price", "0.00")))
            qty = Decimal(str(itm.get("quantity", 1)))
            item_total = self.quantize_money(unit_price * qty)
            subtotal += item_total

        discount = self.quantize_money(subtotal * (discount_pct / Decimal("100.00")))
        taxable = subtotal - discount
        tax = self.quantize_money(taxable * (tax_pct / Decimal("100.00")))
        total = self.quantize_money(taxable + tax)

        return subtotal, discount, tax, total

    def recalculate_order_bill(self, db: Session, order_id: int):
        """Fetches stored OrderItem records and recomputes the order total in DB."""
        from backend.app.models.entities import Order
        order = db.query(Order).filter_by(id=order_id).first()
        if not order:
            return

        subtotal = Decimal("0.00")
        for item in order.items:
            item_total = self.quantize_money(Decimal(str(item.unit_price)) * Decimal(str(item.quantity)))
            item.total_price = item_total
            subtotal += item_total

        order.subtotal = subtotal
        order.discount = Decimal("0.00")
        order.tax = Decimal("0.00")
        order.total = subtotal
        db.commit()


billing_service = BillingService()
