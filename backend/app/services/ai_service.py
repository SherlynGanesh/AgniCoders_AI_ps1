import re
from typing import List, Dict, Any, Optional
from backend.app.schemas.domain import AIParsedInput, ParsedOrderItem


# Hinglish number mappings
HINDI_NUMBERS = {
    'ek': 1,
    'do': 2,
    'teen': 3,
    'char': 4,
    'chaar': 4,
    'paanch': 5,
    'panch': 5,
    'chhe': 6,
    'che': 6,
    'saat': 7,
    'aath': 8,
    'nau': 9,
    'das': 10,
    'gyarah': 11,
    'barah': 12,
    'aadha': 0.5,
    'adhaa': 0.5,
    'one': 1,
    'two': 2,
    'three': 3,
    'four': 4,
    'five': 5
}

# Known Indian grocery brands
KNOWN_BRANDS = [
    "amul", "fortune", "aashirvaad", "tata", "parle", "britannia", "saffola",
    "dharampal", "mdh", "everest", "surf excel", "ariel", "rin", "dettol",
    "lifebuoy", "colgate", "pepsodent", "nestle", "maggi", "haldiram",
    "kissan", "sunfeast", "cadbury", "horlicks", "bournvita", "bru", "nescafe",
    "premia", "gemini", "dhara"
]


class BaseAIAdapter:
    """Abstract interface for AI parsing adapter."""
    def parse_hinglish_order(self, text: str) -> AIParsedInput:
        raise NotImplementedError


class RuleBasedHinglishAIAdapter(BaseAIAdapter):
    """
    Robust local rule-based Hinglish entity extractor.
    Parses conversational Indian shop inputs like:
    'Bhaiya 2 kilo atta, ek Amul butter aur woh wala tel.'
    """

    def parse_hinglish_order(self, text: str) -> AIParsedInput:
        if not text or not text.strip():
            return AIParsedInput(items=[])

        # Strip conversational filler prefixes & suffixes
        cleaned = text.strip()
        cleaned = re.sub(r'^(bhaiya|bhai|sunona|suno|kaka|uncle|chachu)\b[,:\s]*', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\b(dena|dedo|de do|chahiye|pack karna|bhejo|nikal do)\b.*$', '', cleaned, flags=re.IGNORECASE)

        # Split multi-item clauses by 'aur', 'tatha', commas, semicolons, 'and'
        clauses = re.split(r'\s*(?:,|\baur\b|\band\b|\btatha\b|;)\s*', cleaned, flags=re.IGNORECASE)
        items: List[ParsedOrderItem] = []

        for clause in clauses:
            clause = clause.strip()
            if not clause:
                continue

            parsed_item = self._extract_item_from_clause(clause)
            if parsed_item:
                items.append(parsed_item)

        return AIParsedInput(items=items)

    def _extract_item_from_clause(self, clause: str) -> Optional[ParsedOrderItem]:
        raw_snippet = clause.strip()
        words = raw_snippet.split()
        if not words:
            return None

        quantity = 1
        unit = None
        brand = None

        # Check first 1-2 words for quantity
        matched_idx = 0
        w0 = words[0].lower()
        if w0.isdigit():
            quantity = int(w0)
            matched_idx = 1
        elif w0 in HINDI_NUMBERS:
            quantity = int(HINDI_NUMBERS[w0]) if HINDI_NUMBERS[w0] >= 1 else 1
            matched_idx = 1

        # Check next word for unit
        remaining_words = words[matched_idx:]
        if remaining_words:
            w_unit = remaining_words[0].lower()
            if w_unit in {'kilo', 'kg', 'kgs', 'gram', 'gm', 'g', 'litre', 'liter', 'l', 'packet', 'pkt', 'piece', 'pcs', 'bottle', 'dabbi'}:
                unit = 'kg' if w_unit in {'kilo', 'kg', 'kgs'} else (
                    'g' if w_unit in {'gram', 'gm', 'g'} else (
                        'l' if w_unit in {'litre', 'liter', 'l'} else w_unit
                    )
                )
                remaining_words = remaining_words[1:]

        remaining_str = " ".join(remaining_words).strip()
        rem_lower = remaining_str.lower()

        # Extract brand if present
        for b in sorted(KNOWN_BRANDS, key=len, reverse=True):
            if re.search(r'\b' + re.escape(b) + r'\b', rem_lower):
                brand = b.title()
                rem_lower = re.sub(r'\b' + re.escape(b) + r'\b', '', rem_lower).strip()
                break

        # Remove filler words like 'ka', 'ki', 'ke', 'wala', 'wali', 'woh'
        cleaned_product = re.sub(r'\b(ka|ki|ke|wala|wali|woh|yeh)\b', ' ', rem_lower).strip()
        cleaned_product = re.sub(r'\s+', ' ', cleaned_product)

        # Detect confidence
        confidence = 0.92
        if "woh" in raw_snippet.lower() or "wala" in raw_snippet.lower() or not cleaned_product:
            confidence = 0.40

        product_name = cleaned_product if cleaned_product else (brand or "unknown product")

        return ParsedOrderItem(
            raw_text=raw_snippet,
            product=product_name,
            brand=brand,
            quantity=max(1, int(quantity)),
            unit=unit,
            confidence=confidence
        )


class AIService:
    """Modular AI facade supporting interchangeable backend adapters."""

    def __init__(self, adapter: Optional[BaseAIAdapter] = None):
        self.adapter = adapter or RuleBasedHinglishAIAdapter()

    def parse_order(self, text: str) -> AIParsedInput:
        return self.adapter.parse_hinglish_order(text)


ai_service = AIService()
