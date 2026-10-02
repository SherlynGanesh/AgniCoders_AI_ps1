import logging
from decimal import Decimal
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.models.entities import Product, ProductVariant, Inventory, Alias
from backend.app.schemas.domain import ParsedOrderItem, ProductMatchCandidate
from backend.app.services.semantic_search import semantic_engine
from backend.data_ingestion.normalization import normalize_text

logger = logging.getLogger("dukaanmitra.matching")

# Known Hinglish semantic synonyms
HINGLISH_SYNONYMS = {
    "makkhan": "butter",
    "makhan": "butter",
    "tel": "oil",
    "namak": "salt",
    "cheeni": "sugar",
    "shakkar": "sugar",
    "doodh": "milk",
    "dahi": "curd",
    "chawal": "rice",
    "dal": "dal",
    "daal": "pulses",
    "haldi": "turmeric",
    "mirch": "chilli",
    "dhaniya": "coriander",
    "chai": "tea",
    "biskut": "biscuit"
}


class ProductMatchingEngine:

    def match_item(
        self,
        db: Session,
        shop_id: int,
        item: ParsedOrderItem
    ) -> Tuple[Optional[ProductMatchCandidate], List[ProductMatchCandidate], str]:
        """
        Executes hybrid matching:
        1. Shop Memory (Aliases)
        2. Direct Brand & Catalog Match
        3. Semantic & Lexical Hybrid Search
        4. Ambiguity & Inventory Checks

        Returns: (best_match_candidate, alternative_candidates, match_status)
        match_status can be: MATCHED, AMBIGUOUS, OUT_OF_STOCK, UNKNOWN_PRODUCT
        """
        raw_text_norm = normalize_text(item.raw_text)
        prod_norm = normalize_text(item.product)
        brand_norm = normalize_text(item.brand) if item.brand else None

        # Resolve Hinglish synonym if applicable
        translated_prod = HINGLISH_SYNONYMS.get(prod_norm, prod_norm)

        # -------------------------------------------------------------
        # STEP 1: Shop Memory / Alias Check
        # -------------------------------------------------------------
        alias = (
            db.query(Alias)
            .filter(
                Alias.shop_id == shop_id,
                Alias.normalized_alias.in_([raw_text_norm, prod_norm, f"{brand_norm} {prod_norm}"])
            )
            .order_by(Alias.confidence.desc(), Alias.usage_count.desc())
            .first()
        )
        if alias and float(alias.confidence) >= 0.80:
            variant = (
                db.query(ProductVariant)
                .join(Product)
                .filter(ProductVariant.id == alias.variant_id)
                .first()
            )
            if variant:
                inv = db.query(Inventory).filter_by(shop_id=shop_id, variant_id=variant.id).first()
                stock = inv.quantity if inv else 0
                status = "OUT_OF_STOCK" if stock < item.quantity else "MATCHED"

                candidate = ProductMatchCandidate(
                    variant_id=variant.id,
                    product_id=variant.product_id,
                    product_name=variant.product.name,
                    brand=variant.product.brand,
                    variant_label=variant.variant_label,
                    size=float(variant.size) if variant.size else None,
                    unit=variant.unit,
                    price=variant.price,
                    mrp=variant.mrp,
                    stock=stock,
                    match_score=float(alias.confidence),
                    match_type="SHOP_MEMORY",
                    is_ambiguous=False,
                    is_out_of_stock=(stock < item.quantity)
                )
                return candidate, [candidate], status

        # -------------------------------------------------------------
        # STEP 2: Hybrid Search (Lexical + Semantic)
        # -------------------------------------------------------------
        search_query = f"{item.brand or ''} {translated_prod}".strip()
        candidates_raw = semantic_engine.search_candidates(db, search_query, shop_id=shop_id, limit=6)

        if not candidates_raw:
            candidates_raw = semantic_engine.search_candidates(db, translated_prod, shop_id=shop_id, limit=6)

        if not candidates_raw:
            return None, [], "UNKNOWN_PRODUCT"

        # Check for explicit pack size match (e.g., 2 kilo atta -> variant size=2, unit=kg)
        for c in candidates_raw:
            if item.unit and c["unit"] and c["unit"].lower() == item.unit.lower():
                if c["size"] and float(c["size"]) == float(item.quantity):
                    c["match_score"] = min(0.99, c["match_score"] + 0.15)
                    c["match_type"] = "SIZE_MATCH"

        candidates_raw.sort(key=lambda x: (x["match_score"], x["stock"] > 0), reverse=True)
        candidates = [ProductMatchCandidate(**c) for c in candidates_raw]

        # -------------------------------------------------------------
        # STEP 3: Ambiguity Detection
        # -------------------------------------------------------------
        top = candidates[0]
        if len(candidates) > 1:
            second = candidates[1]
            score_diff = abs(top.match_score - second.match_score)
            is_generic = prod_norm in {"tel", "oil"}

            # If user said generic 'tel'/'oil' without brand, or scores are tied and products differ
            if (not item.brand and is_generic) or (score_diff <= 0.05 and top.product_name != second.product_name):
                top.is_ambiguous = True
                return None, candidates, "AMBIGUOUS"

        # -------------------------------------------------------------
        # STEP 4: Inventory & Stock Check
        # -------------------------------------------------------------
        if top.stock < item.quantity:
            top.is_out_of_stock = True
            return top, candidates, "OUT_OF_STOCK"

        return top, candidates, "MATCHED"


product_matcher = ProductMatchingEngine()
