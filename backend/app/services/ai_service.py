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
            return AIParsedInput(items=[], flags=["Context Warning: No audible speech or text detected."], context_status="INAUDIBLE")

        raw_input = text.strip()
        text_lower = raw_input.lower()
        flags: List[str] = []
        delivery_note: Optional[str] = None
        context_status = "CLEAR"

        # -------------------------------------------------------------
        # Marathi / Hinglish Disambiguation: "Aata" (Now) vs "Atta" (Flour)
        # -------------------------------------------------------------
        # Check if 'aata' is used as a temporal adverb (Marathi for "Now / Immediately")
        # e.g., "aata bhej do", "aata de dya", "aata 2 packet milk bhej do", "urgent aata bhej do"
        has_temporal_aata = bool(
            re.search(r'\b(aata|atta)\s+(bhej|de\b|dya|pahije|lagel|nikal|lao|kar\b|delivery|jaldi|urgent)\b', text_lower) or
            re.search(r'\b(bhej|de\b|dya|pahije|lagel|jaldi|urgent)\s+(aata|atta)\b', text_lower) or
            re.search(r'^(aata|atta)\s+\d+.*(bhej|de|dya|chahiye)', text_lower)
        )

        # Check if 'atta' is explicitly a commodity (Wheat Flour)
        # e.g., "2 kilo atta", "1 kg aata", "atta 5kg", "aashirvaad atta", "wheat flour", "gehun atta"
        has_commodity_atta = bool(
            re.search(r'(\d+|ek|do|teen|char|chaar|paanch|panch|aadha|half|\bkg\b|\bkilo\b|\bpacket\b)\s*(kilo|kg|packet|g|gm)?\s+(atta|aata)\b', text_lower) or
            re.search(r'\b(atta|aata)\s+(\d+|kilo|kg)\b(?!\s*(kilo|kg|packet|pkt|bottle|dabba|can|g|gm)?\s*(milk|doodh|oil|tel|butter|bread|sugar|cheeni|biscuit|soap|chai|tea|rice|chawal|dal|daal))', text_lower) or
            re.search(r'\b(aashirvaad|pillsbury|fortune|gehun|sharbati|flour)\s+(atta|aata)\b', text_lower) or
            re.search(r'\b(atta|aata)\s+(packet|bori|bag|thaili)\b', text_lower)
        )

        cleaned = raw_input

        if has_temporal_aata and has_commodity_atta:
            flags.append("🟢 Multi-Context Resolved: Detected Wheat Flour ('Atta') AND Marathi Temporal Urgency ('Aata' -> Deliver Now).")
            delivery_note = "Deliver immediately (Customer requested 'Aata / Now')."
            # Only remove the temporal aata occurrences
            cleaned = re.sub(r'\b(aata|atta)\s+(bhej|de|dya|pahije|lagel|nikal|lao|kar|delivery)\b', r'\2', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'\b(bhej|de|dya|pahije|lagel)\s+(aata|atta)\b', r'\1', cleaned, flags=re.IGNORECASE)
        elif has_temporal_aata and not has_commodity_atta:
            flags.append("🟢 Marathi Linguistic Context: Resolved 'Aata' as Temporal Adverb (Deliver Immediately), not Wheat Flour.")
            delivery_note = "Deliver immediately (Customer requested 'Aata / Now')."
            # Strip temporal aata so it doesn't get extracted as a product
            cleaned = re.sub(r'\b(aata|atta)\b', '', cleaned, flags=re.IGNORECASE)
        elif has_commodity_atta:
            flags.append("🟢 Linguistic Disambiguation: Confirmed 'Atta' as Wheat Flour commodity based on numeric quantity/unit context.")
        elif re.search(r'\b(atta|aata)\b', text_lower) and not has_commodity_atta and not has_temporal_aata:
            flags.append("🟡 Context Ambiguity: 'Atta' can mean Marathi 'Aata' (Now) or Wheat Flour. Clarification recommended.")
            context_status = "AMBIGUOUS"

        # Check for delivery time modifiers
        if re.search(r'\b(kal subah|tomorrow morning)\b', text_lower):
            delivery_note = "Deliver tomorrow morning."
            flags.append("📅 Delivery Preference: Identified schedule for 'Kal Subah'.")
        elif re.search(r'\b(aaj shaam|today evening)\b', text_lower):
            delivery_note = "Deliver today evening."
            flags.append("📅 Delivery Preference: Identified schedule for 'Aaj Shaam'.")

        # Strip conversational filler prefixes & suffixes
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

        if not items:
            flags.append("⚠️ Audio / Context Alert: Could not extract recognizable store items from speech. Please speak louder or rephrase.")
            context_status = "INAUDIBLE"

        return AIParsedInput(
            items=items,
            delivery_note=delivery_note,
            flags=flags,
            context_status=context_status
        )

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
