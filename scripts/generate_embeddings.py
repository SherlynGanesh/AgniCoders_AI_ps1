import os
import sys
from sqlalchemy.orm import Session

# Add project root to sys.path
sys.path.insert(0, os.path.abspath("."))
from backend.app.database.session import SessionLocal
from backend.app.models.entities import ProductVariant, Product, ProductEmbedding
from backend.app.services.semantic_search import semantic_engine
from backend.app.config import settings


def generate_embeddings(limit: int = 150):
    print("==================================================")
    print("DUKAANMITRA — Generating Product Embeddings")
    print("==================================================")

    db: Session = SessionLocal()
    try:
        variants = db.query(ProductVariant).join(Product).limit(limit).all()
        if not variants:
            print("No product variants found in database. Ingest catalog or generate demo data first.")
            return

        print(f"Target variants to embed: {len(variants)}")
        print(f"Model configured: {settings.EMBEDDING_MODEL}")

        if not semantic_engine.is_vector_available:
            print("[INFO] Embedding model is downloading or currently unavailable.")
            print("Lexical fallback search (RapidFuzz token-set & trigram) is fully active and ready.")
            print("To generate vector embeddings later, run this script once SentenceTransformers model downloads.")
            return

        count = 0
        for var in variants:
            prod = var.product
            text_desc = f"{prod.name} {prod.brand or ''} {var.variant_label}".strip()

            existing_emb = db.query(ProductEmbedding).filter_by(variant_id=var.id).first()
            if not existing_emb:
                vec = semantic_engine.generate_embedding(text_desc)
                if vec:
                    emb = ProductEmbedding(
                        variant_id=var.id,
                        text_for_embedding=text_desc,
                        embedding=vec,
                        model_name=settings.EMBEDDING_MODEL
                    )
                    db.add(emb)
                    count += 1

        db.commit()
        print(f"Generated embeddings for {count} product variants.")
        print("Embeddings generation complete!\n")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Embedding generation failed: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    generate_embeddings()
