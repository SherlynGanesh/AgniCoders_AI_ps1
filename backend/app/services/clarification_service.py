from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.models.entities import Clarification, Order, ProductVariant
from backend.app.schemas.domain import ProductMatchCandidate


class ClarificationService:

    def create_clarification(
        self,
        db: Session,
        order_id: int,
        ambiguous_text: str,
        candidates: List[ProductMatchCandidate]
    ) -> Clarification:
        """
        Creates a clarification question with minimal viable options.
        Example: 'Kaunsa tel chahiye?' with options for variants.
        """
        # Build options payload
        options_data = []
        for c in candidates[:5]:
            options_data.append({
                "variant_id": c.variant_id,
                "label": f"{c.product_name} {c.brand or ''} ({c.variant_label})",
                "price": float(c.price),
                "stock": c.stock
            })

        # Generate contextual question
        cleaned_term = ambiguous_text.strip().title()
        question = f"Kaunsa {cleaned_term} chahiye? Kripya option chunein:"

        clarification = Clarification(
            order_id=order_id,
            ambiguous_text=ambiguous_text,
            question=question,
            options=options_data,
            resolved=False
        )
        db.add(clarification)
        db.commit()
        db.refresh(clarification)
        return clarification

    def resolve_clarification(
        self,
        db: Session,
        clarification_id: int,
        selected_variant_id: int
    ) -> Optional[Clarification]:
        """
        Marks clarification as resolved with selected variant.
        """
        clarification = db.query(Clarification).filter_by(id=clarification_id).first()
        if not clarification:
            return None

        clarification.selected_variant_id = selected_variant_id
        clarification.resolved = True
        clarification.resolved_at = func.now() if hasattr(func, 'now') else None
        db.commit()
        db.refresh(clarification)
        return clarification


clarification_service = ClarificationService()
