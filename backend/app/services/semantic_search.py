import logging
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
from rapidfuzz import fuzz
from backend.app.config import settings
from backend.app.models.entities import Product, ProductVariant, Inventory, ProductEmbedding

logger = logging.getLogger("dukaanmitra.semantic_search")


class SemanticSearchEngine:
    def __init__(self):
        self.model = None
        self._model_load_attempted = False
        self._model_available = False

    def _lazy_load_model(self):
        if self._model_load_attempted:
            return
        self._model_load_attempted = True
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
            self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
            self._model_available = True
            logger.info("Embedding model loaded successfully.")
        except Exception as e:
            logger.warning(f"Could not load SentenceTransformer model ({e}). Lexical fallback will be utilized.")
            self._model_available = False

    @property
    def is_vector_available(self) -> bool:
        self._lazy_load_model()
        return self._model_available

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        self._lazy_load_model()
        if not self._model_available or not self.model:
            return None
        try:
            emb = self.model.encode(text, convert_to_numpy=True)
            return emb.tolist()
        except Exception as e:
            logger.warning(f"Embedding generation failed: {e}")
            return None

    def search_candidates(
        self,
        db: Session,
        query: str,
        shop_id: Optional[int] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Targeted SQL + Fuzzy Lexical Search across the ENTIRE product catalog.
        """
        import re
        from sqlalchemy import or_

        query_norm = query.strip().lower()
        if not query_norm:
            return []

        tokens = [t for t in re.findall(r'\b[a-zA-Z0-9]+\b', query_norm) if len(t) > 1]
        if not tokens:
            tokens = [query_norm]

        # 1. Target SQL across ALL 5,500+ variants
        clauses = []
        for t in tokens:
            t_pat = f"%{t}%"
            clauses.append(Product.name.ilike(t_pat))
            clauses.append(Product.normalized_name.ilike(t_pat))
            clauses.append(Product.brand.ilike(t_pat))
            clauses.append(ProductVariant.variant_label.ilike(t_pat))

        q = (
            db.query(ProductVariant, Product, Inventory)
            .join(Product, ProductVariant.product_id == Product.id)
            .outerjoin(Inventory, (Inventory.variant_id == ProductVariant.id) & (Inventory.shop_id == shop_id))
            .filter(or_(*clauses))
        )
        results = q.limit(100).all()

        # If strict token match has fewer than 5 results, add general inventory pool
        if len(results) < 5:
            fallback_q = (
                db.query(ProductVariant, Product, Inventory)
                .join(Product, ProductVariant.product_id == Product.id)
                .outerjoin(Inventory, (Inventory.variant_id == ProductVariant.id) & (Inventory.shop_id == shop_id))
            )
            more = fallback_q.limit(100).all()
            existing_ids = {r[0].id for r in results}
            results.extend([m for m in more if m[0].id not in existing_ids])

        candidates: List[Dict[str, Any]] = []
        query_words = set(tokens)

        for variant, product, inv in results:
            stock = inv.quantity if inv else 0
            prod_name = product.name
            brand_name = product.brand or ""
            variant_str = f"{prod_name} {brand_name} {variant.variant_label}".lower()
            variant_words = set(re.findall(r'\b[a-zA-Z0-9]+\b', variant_str))

            # Exact whole word overlap
            exact_overlap = query_words.intersection(variant_words)
            overlap_ratio = len(exact_overlap) / len(query_words) if query_words else 0.0

            # Token set ratio
            ratio = fuzz.token_set_ratio(query_norm, variant_str) / 100.0

            # Penalize accidental partial substring match (like 'atta' in 'tata')
            if overlap_ratio > 0:
                fuzzy_score = max(ratio, 0.85 + (0.10 * overlap_ratio))
            else:
                fuzzy_score = ratio * 0.70

            # Exact whole word match boost
            if any(w in variant_words for w in query_words if len(w) >= 3):
                fuzzy_score = max(fuzzy_score, 0.90)

            # Exact phrase match boost
            if query_norm in variant_str:
                fuzzy_score = max(fuzzy_score, 0.95)

            # Brand match boost
            if product.brand and query_norm and product.brand.lower() in query_norm:
                fuzzy_score = min(0.99, fuzzy_score + 0.05)

            # In-stock preference
            if stock > 0:
                fuzzy_score = min(0.99, fuzzy_score + 0.03)

            if fuzzy_score >= 0.50:
                candidates.append({
                    "variant_id": variant.id,
                    "product_id": product.id,
                    "product_name": product.name,
                    "brand": product.brand,
                    "variant_label": variant.variant_label,
                    "size": float(variant.size) if variant.size else None,
                    "unit": variant.unit,
                    "price": variant.price,
                    "mrp": variant.mrp,
                    "stock": stock,
                    "match_score": round(float(min(0.99, fuzzy_score)), 3),
                    "match_type": "CATALOG_MATCH"
                })

        candidates.sort(key=lambda x: (x["match_score"], x["stock"] > 0), reverse=True)
        return candidates[:limit]


semantic_engine = SemanticSearchEngine()
