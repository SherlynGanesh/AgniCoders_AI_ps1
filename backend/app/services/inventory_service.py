import logging
from typing import Dict, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import HTTPException, status
from backend.app.models.entities import Inventory, ProductVariant

logger = logging.getLogger("dukaanmitra.inventory")


class InventoryService:

    def check_and_lock_inventory(
        self,
        db: Session,
        shop_id: int,
        requested_items: List[Tuple[int, int]]  # List of (variant_id, requested_qty)
    ) -> Dict[int, Inventory]:
        """
        Locks inventory rows using SELECT ... FOR UPDATE within a transaction.
        Verifies stock availability for every requested item.
        Raises HTTPException 400 if any product is out of stock.
        """
        locked_inventories: Dict[int, Inventory] = {}

        for variant_id, qty in requested_items:
            # PostgreSQL row-level lock
            inv = (
                db.query(Inventory)
                .filter(Inventory.shop_id == shop_id, Inventory.variant_id == variant_id)
                .with_for_update()
                .first()
            )

            if not inv:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Inventory record for variant_id {variant_id} does not exist in shop {shop_id}."
                )

            if inv.quantity < qty:
                variant = db.query(ProductVariant).filter_by(id=variant_id).first()
                label = variant.variant_label if variant else str(variant_id)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient stock for '{label}'. Available: {inv.quantity}, Requested: {qty}."
                )

            locked_inventories[variant_id] = inv

        return locked_inventories

    def deduct_stock(
        self,
        locked_inventories: Dict[int, Inventory],
        requested_items: List[Tuple[int, int]]
    ):
        """
        Deducts verified inventory quantities safely.
        Must be followed by db.commit() in calling transaction block.
        """
        for variant_id, qty in requested_items:
            inv = locked_inventories[variant_id]
            inv.quantity -= qty


inventory_service = InventoryService()
