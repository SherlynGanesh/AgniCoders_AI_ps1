import re
from typing import Optional, Tuple
from decimal import Decimal

# Price extraction regex
PRICE_PATTERN = re.compile(r'(?:₹|rs\.?|inr)?\s*([0-9]+(?:\.[0-9]+)?)', re.IGNORECASE)

# Unit & Pack size normalization
UNIT_MAP = {
    'g': 'g',
    'gm': 'g',
    'gms': 'g',
    'gram': 'g',
    'grams': 'g',
    'kg': 'kg',
    'kgs': 'kg',
    'kilo': 'kg',
    'kilogram': 'kg',
    'kilograms': 'kg',
    'l': 'l',
    'ltr': 'l',
    'litre': 'l',
    'litres': 'l',
    'liter': 'l',
    'liters': 'l',
    'ml': 'ml',
    'millilitre': 'ml',
    'millilitres': 'ml',
    'pc': 'pc',
    'pcs': 'pc',
    'piece': 'pc',
    'pieces': 'pc',
    'packet': 'packet',
    'pkt': 'packet',
    'pack': 'packet',
    'sachet': 'packet',
    'bottle': 'bottle',
    'can': 'can',
    'box': 'box',
    'pouch': 'pouch',
    'unit': 'unit'
}

SIZE_UNIT_PATTERN = re.compile(
    r'([0-9]+(?:\.[0-9]+)?)\s*([a-zA-Z]+)', re.IGNORECASE
)


def normalize_text(text: Optional[str]) -> str:
    """Lowercases, removes special characters, and trims extra spaces."""
    if not text:
        return ""
    # Remove excessive punctuation but keep alphanumerics
    cleaned = re.sub(r'[^a-zA-Z0-9\s]', ' ', str(text))
    # Replace multiple spaces with a single space
    return re.sub(r'\s+', ' ', cleaned).strip().lower()


def normalize_brand(brand: Optional[str]) -> Optional[str]:
    """Cleans and title-cases brand names."""
    if not brand or str(brand).strip().lower() in {'nan', 'none', 'null', 'generic'}:
        return None
    cleaned = str(brand).strip()
    return cleaned.title()


def normalize_category(cat: Optional[str]) -> str:
    """Normalizes category name to standardized categories."""
    if not cat or str(cat).strip().lower() in {'nan', 'none', 'null'}:
        return "Grocery"
    cleaned = str(cat).strip()
    return cleaned.title()


def normalize_price(price_val) -> Decimal:
    """Extracts numeric price and returns Decimal with 2 places."""
    if price_val is None:
        return Decimal('0.00')
    if isinstance(price_val, (int, float, Decimal)):
        try:
            return Decimal(str(price_val)).quantize(Decimal('0.01'))
        except Exception:
            return Decimal('0.00')
    val_str = str(price_val).strip()
    match = PRICE_PATTERN.search(val_str)
    if match:
        try:
            return Decimal(match.group(1)).quantize(Decimal('0.01'))
        except Exception:
            pass
    return Decimal('0.00')


def parse_pack_size(raw_quantity: Optional[str]) -> Tuple[Optional[float], Optional[str], str]:
    """
    Parses strings like '500 gm', '0.5 KG', '1 Litre', '100g', '2 x 500g'
    Returns: (size_value, normalized_unit, variant_label)
    Example:
      '500 gm' -> (500.0, 'g', '500 g')
      '0.5 KG' -> (0.5, 'kg', '500 g') or (0.5, 'kg', '0.5 kg')
      '1 Ltr' -> (1.0, 'l', '1 L')
    """
    if not raw_quantity or str(raw_quantity).strip().lower() in {'nan', 'none', 'null'}:
        return None, None, "Standard"

    raw = str(raw_quantity).strip()
    
    # Check for multiplier like '2 x 500g'
    multi_match = re.search(r'([0-9]+)\s*x\s*([0-9]+(?:\.[0-9]+)?)\s*([a-zA-Z]+)', raw, re.IGNORECASE)
    if multi_match:
        count = float(multi_match.group(1))
        unit_val = float(multi_match.group(2))
        unit_str = multi_match.group(3).lower()
        total_size = count * unit_val
        norm_unit = UNIT_MAP.get(unit_str, unit_str)
        return total_size, norm_unit, f"{total_size:g} {norm_unit}"

    match = SIZE_UNIT_PATTERN.search(raw)
    if match:
        size_num = float(match.group(1))
        unit_raw = match.group(2).lower()
        norm_unit = UNIT_MAP.get(unit_raw, unit_raw)

        # Standardize labels
        label_unit = norm_unit.upper() if norm_unit in {'l', 'ml'} else norm_unit
        if norm_unit == 'l':
            label_unit = 'L'
        elif norm_unit == 'ml':
            label_unit = 'ml'
        label = f"{size_num:g} {label_unit}"
        return size_num, norm_unit, label

    return None, None, raw
