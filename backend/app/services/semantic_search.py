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
        Hybrid search combining Lexical Fuzzy matching and Vector similarity.
        """
        query_norm = query.strip().lower()
        candidates: List[Dict[str, Any]] = []

        # 1. Fetch available variants in stock or in catalog
        q = (
            db.query(ProductVariant, Product, Inventory)
            .join(Product, ProductVariant.product_id == Product.id)
            .outerjoin(Inventory, (Inventory.variant_id == ProductVariant.id) & (Inventory.shop_id == shop_id))
        )
        results = q.limit(300).all()

        for variant, product, inv in results:
            stock = inv.quantity if inv else 0
            prod_name = product.name
            brand_name = product.brand or ""
            variant_str = f"{prod_name} {brand_name} {variant.variant_label}".lower()

            # RapidFuzz similarity
            ratio = fuzz.token_set_ratio(query_norm, variant_str) / 100.0
            partial = fuzz.partial_ratio(query_norm, variant_str) / 100.0
            fuzzy_score = max(ratio, partial)

            # Boost exact substring matches
            if query_norm in variant_str:
                fuzzy_score = max(fuzzy_score, 0.88)

            # Boost brand match if brand matches
            if product.brand and query_norm and product.brand.lower() in query_norm:
                fuzzy_score += 0.08

            # In-stock preference boost
            if stock > 0:
                fuzzy_score += 0.04

            if fuzzy_score > 0.40:
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
                    "match_type": "LEXICAL_FALLBACK" if not self._model_available else "HYBRID"
                })

        # Sort by match score descending
        candidates.sort(key=lambda x: (x["match_score"], x["stock"] > 0), reverse=True)
        return candidates[:limit]


semantic_engine = SemanticSearchEngine()
