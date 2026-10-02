import os
import sys
from decimal import Decimal
from sqlalchemy.orm import Session

# Add project root to sys.path
sys.path.insert(0, os.path.abspath("."))
from backend.app.database.session import SessionLocal
from backend.app.models.entities import Category, Product, ProductVariant
from backend.data_ingestion.load_dmart import load_dmart_dataset
from backend.data_ingestion.normalization import normalize_text


def ingest_dmart(sample_limit: int = 2500):
    print("==================================================")
    print("Ingesting DMart Public Product Catalog")
    print("==================================================")

    db: Session = SessionLocal()
    try:
        products_data, variants_data, categories_data = load_dmart_dataset()

        # 1. Ingest Categories
        category_map = {}
        for cat_name in categories_data:
            cat = db.query(Category).filter_by(name=cat_name).first()
            if not cat:
                cat = Category(
                    name=cat_name,
                    normalized_name=normalize_text(cat_name),
                    description=f"Public catalog category: {cat_name}",
                    data_source="KAGGLE_DMART"
                )
                db.add(cat)
                db.flush()
            category_map[cat_name] = cat.id

        db.commit()
        print(f"Categories synchronized ({len(category_map)} categories).")

        # 2. Ingest Products & Variants
        prod_key_to_id = {}
        inserted_prods = 0
        inserted_vars = 0

        # Subsample for snappy demo performance if dataset is huge
        selected_prods = products_data[:sample_limit]
        for p in selected_prods:
            norm_name = p["normalized_name"]
            norm_brand = p["normalized_brand"] or ""
            cat_name = p["category_name"]
            p_key = (norm_name, norm_brand, cat_name)

            existing_prod = db.query(Product).filter_by(
                normalized_name=norm_name,
                normalized_brand=norm_brand,
                category_id=category_map.get(cat_name)
            ).first()

            if not existing_prod:
                prod = Product(
                    category_id=category_map.get(cat_name),
                    name=p["name"],
                    brand=p["brand"],
                    sku=p["sku"],
                    description=p["description"],
                    normalized_name=norm_name,
                    normalized_brand=norm_brand,
                    data_source=p["data_source"],
                    source_dataset=p["source_dataset"],
                    source_record_id=p["source_record_id"]
                )
                db.add(prod)
                db.flush()
                prod_key_to_id[p_key] = prod.id
                inserted_prods += 1
            else:
                prod_key_to_id[p_key] = existing_prod.id

        db.commit()
        print(f"Products ingested: {inserted_prods} new products added.")

        # Ingest variants corresponding to ingested products
        for v in variants_data:
            p_key = v["product_key"]
            prod_id = prod_key_to_id.get(p_key)
            if not prod_id:
                continue

            existing_var = db.query(ProductVariant).filter_by(
                product_id=prod_id,
                variant_label=v["variant_label"]
            ).first()

            if not existing_var:
                var = ProductVariant(
                    product_id=prod_id,
                    size=v["size"],
                    unit=v["unit"],
                    price=v["price"],
                    mrp=v["mrp"],
                    barcode=v["barcode"],
                    normalized_unit=v["normalized_unit"],
                    variant_label=v["variant_label"],
                    data_source=v["data_source"],
                    source_dataset=v["source_dataset"],
                    source_record_id=v["source_record_id"]
                )
                db.add(var)
                inserted_vars += 1

        db.commit()
        print(f"Product variants ingested: {inserted_vars} new variants added.")
        print("DMart ingestion complete!\n")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] DMart ingestion failed: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    ingest_dmart()
