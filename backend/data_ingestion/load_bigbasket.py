import os
import pandas as pd
from typing import List, Dict, Any, Tuple
from backend.data_ingestion.cleaning import clean_dataframe, inspect_schema
from backend.data_ingestion.normalization import (
    normalize_text,
    normalize_brand,
    normalize_category,
    normalize_price,
    parse_pack_size
)
from backend.data_ingestion.deduplication import deduplicate_products, deduplicate_variants


def load_bigbasket_dataset(file_path: str = "data/raw/bigbasket/bigbasket_products.csv") -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
    """
    Ingests and normalizes the BigBasket dataset.
    Returns: (products, variants, categories)
    """
    if not os.path.exists(file_path):
        if os.path.exists("bigbasket_products.csv"):
            file_path = "bigbasket_products.csv"
        else:
            raise FileNotFoundError(f"BigBasket dataset not found at {file_path} or bigbasket_products.csv")

    df = pd.read_csv(file_path)
    inspect_schema(df, "BigBasket Products")

    column_mapping = {
        'product': 'name',
        'brand': 'brand',
        'category': 'category',
        'sub_category': 'sub_category',
        'sale_price': 'price',
        'market_price': 'mrp',
        'description': 'description',
        'type': 'type',
        'eancode': 'barcode',
        'Unnamed: 0': 'record_id'
    }

    cleaned_df = clean_dataframe(df, column_mapping)

    categories_set = set()
    raw_products = []
    raw_variants = []

    for idx, row in cleaned_df.iterrows():
        raw_name = row.get('name')
        if not raw_name or str(raw_name).strip() == '':
            continue

        brand = normalize_brand(row.get('brand'))
        norm_name = normalize_text(raw_name)
        norm_brand = normalize_text(brand) if brand else None
        category = normalize_category(row.get('category'))
        categories_set.add(category)

        mrp_dec = normalize_price(row.get('mrp'))
        price_dec = normalize_price(row.get('price'))
        if price_dec == 0 and mrp_dec > 0:
            price_dec = mrp_dec
        if mrp_dec == 0 and price_dec > 0:
            mrp_dec = price_dec

        # Try to parse pack size from product name or type
        size, unit, variant_label = parse_pack_size(raw_name)
        if not unit and row.get('type'):
            s2, u2, l2 = parse_pack_size(row.get('type'))
            if u2:
                size, unit, variant_label = s2, u2, l2

        if not unit and (not variant_label or len(variant_label) > 50):
            variant_label = "Standard Pack"
        else:
            variant_label = str(variant_label)[:100].strip()

        rec_id = str(row.get('record_id') or idx)

        prod_dict = {
            "name": str(raw_name).strip(),
            "brand": brand,
            "normalized_name": norm_name,
            "normalized_brand": norm_brand,
            "category_name": category,
            "description": row.get('description'),
            "sku": f"BB-{rec_id}",
            "data_source": "KAGGLE_BIGBASKET",
            "source_dataset": "bigbasket",
            "source_record_id": rec_id,
            "active": True
        }
        raw_products.append(prod_dict)

        var_dict = {
            "product_key": (norm_name, norm_brand or "", category),
            "size": size,
            "unit": unit,
            "normalized_unit": unit,
            "variant_label": variant_label,
            "price": price_dec,
            "mrp": mrp_dec,
            "barcode": str(row.get('barcode')) if row.get('barcode') else None,
            "data_source": "KAGGLE_BIGBASKET",
            "source_dataset": "bigbasket",
            "source_record_id": rec_id,
            "active": True
        }
        raw_variants.append(var_dict)

    products = deduplicate_products(raw_products)
    variants = deduplicate_variants(raw_variants)

    print(f"[BigBasket Ingestion] Extracted {len(products)} products, {len(variants)} variants, {len(categories_set)} categories.")
    return products, variants, sorted(list(categories_set))
