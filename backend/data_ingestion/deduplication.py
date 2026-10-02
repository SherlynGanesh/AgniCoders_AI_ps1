from typing import List, Dict, Any


def deduplicate_products(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Carefully deduplicates products based on composite key:
    (normalized_name, normalized_brand, category_name)
    Does NOT merge two products merely because names are similar.
    Preserves original source dataset and reference IDs.
    """
    seen = {}
    deduped = []

    for item in products:
        norm_name = item.get("normalized_name")
        norm_brand = item.get("normalized_brand") or ""
        cat = item.get("category_name") or ""
        key = (norm_name, norm_brand, cat)

        if key not in seen:
            seen[key] = item
            deduped.append(item)
        else:
            # If current item has better description or metadata, enrich
            existing = seen[key]
            if not existing.get("description") and item.get("description"):
                existing["description"] = item.get("description")

    return deduped


def deduplicate_variants(variants: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicates variants for a given product by (product_id or temp_prod_key, variant_label).
    """
    seen = {}
    deduped = []

    for var in variants:
        prod_key = var.get("product_key") or var.get("product_id")
        label = var.get("variant_label") or "Standard"
        key = (prod_key, label)

        if key not in seen:
            seen[key] = var
            deduped.append(var)

    return deduped
