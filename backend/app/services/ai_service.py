import re
from typing import List, Dict, Any, Optional
from backend.app.schemas.domain import AIParsedInput, ParsedOrderItem

# Devanagari numerals to ASCII digits
DEVANAGARI_DIGITS = str.maketrans('०१२३४५६७८९', '0123456789')

# Hinglish & Hindi Devanagari number mappings
HINDI_NUMBERS = {
    # Hinglish
    'ek': 1, 'do': 2, 'teen': 3, 'char': 4, 'chaar': 4, 'paanch': 5, 'panch': 5,
    'chhe': 6, 'che': 6, 'saat': 7, 'aath': 8, 'nau': 9, 'das': 10,
    'gyarah': 11, 'barah': 12, 'aadha': 0.5, 'adhaa': 0.5, 'half': 0.5,
    'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
    # Devanagari Hindi
    'एक': 1, 'दो': 2, 'तीन': 3, 'चार': 4, 'पांच': 5, 'पाँच': 5,
    'छह': 6, 'छः': 6, 'सात': 7, 'आठ': 8, 'नौ': 9, 'दस': 10,
    'ग्यारह': 11, 'बारह': 12, 'तेरह': 13, 'चौदह': 14, 'पंद्रह': 15,
    'सोलह': 16, 'सत्रह': 17, 'अठारह': 18, 'उन्नीस': 19, 'बीस': 20,
    'पच्चीस': 25, 'तीस': 30, 'चालीस': 40, 'पचास': 50, 'सौ': 100,
    'आधा': 0.5, 'पाव': 0.25, 'डेढ़': 1.5, 'ढाई': 2.5
}

# Unit mapping covering English, Hinglish, and Hindi Devanagari
UNIT_MAPPING = {
    # Weight (kg)
    'kilo': 'kg', 'kg': 'kg', 'kgs': 'kg', 'kilogram': 'kg', 'kilograms': 'kg',
    'किलो': 'kg', 'किलोग्राम': 'kg', 'केजी': 'kg', 'किग्रा': 'kg', 'कि.ग्रा.': 'kg',
    # Weight (g)
    'gram': 'g', 'gm': 'g', 'gms': 'g', 'g': 'g', 'grams': 'g',
    'ग्राम': 'g', 'ग्राम्स': 'g', 'ग्रा': 'g', 'ग्रा.': 'g', 'मिलीग्राम': 'mg',
    # Volume (l)
    'litre': 'l', 'liter': 'l', 'litres': 'l', 'liters': 'l', 'l': 'l', 'ltr': 'l',
    'लीटर': 'l', 'ली': 'l', 'ली.': 'l', 'लीटरों': 'l',
    # Volume (ml)
    'ml': 'ml', 'millilitre': 'ml', 'मिलीलीटर': 'ml', 'एमएल': 'ml',
    # Packets / Pouches
    'packet': 'packet', 'packets': 'packet', 'pkt': 'packet', 'pkts': 'packet', 'pack': 'packet',
    'पैकेट': 'packet', 'पैक': 'packet', 'पाउच': 'packet', 'थैली': 'packet', 'बोरी': 'packet',
    # Bottles / Jars
    'bottle': 'bottle', 'bottles': 'bottle', 'बोतल': 'bottle', 'बॉटल': 'bottle',
    # Boxes / Cans
    'box': 'box', 'dabbi': 'box', 'dabba': 'box', 'डिब्बा': 'box', 'डब्बा': 'box',
    'can': 'can', 'tins': 'can', 'tin': 'can', 'कैन': 'can', 'टिन': 'can',
    # Pieces
    'piece': 'pc', 'pieces': 'pc', 'pcs': 'pc', 'pc': 'pc', 'पीस': 'pc', 'नग': 'pc'
}

# Hindi Devanagari & Hinglish grocery commodity translation to catalog terms
HINDI_COMMODITIES = {
    'आटा': 'atta', 'गेहूं आटा': 'wheat atta', 'गेहूं': 'atta', 'मैदा': 'maida', 'सूजी': 'suji', 'रवा': 'rava',
    'बेसन': 'besan', 'पोहा': 'poha', 'चावल': 'rice', 'बासमती': 'basmati rice',
    'दाल': 'dal', 'तूर दाल': 'toor dal', 'तुवर दाल': 'toor dal', 'अरहर दाल': 'toor dal',
    'मूंग दाल': 'moong dal', 'मूंग': 'moong', 'चना दाल': 'chana dal', 'चना': 'chana',
    'उड़द दाल': 'urad dal', 'उड़द': 'urad', 'मसूर दाल': 'masoor dal', 'मसूर': 'masoor',
    'राजमा': 'rajma', 'छोले': 'chole', 'काबुली चना': 'kabuli chana',
    'तेल': 'oil', 'रिफाइंड तेल': 'oil', 'सरसों का तेल': 'mustard oil', 'सरसों तेल': 'mustard oil',
    'सूरजमुखी तेल': 'sunflower oil', 'सोयाबीन तेल': 'soybean oil',
    'मक्खन': 'butter', 'बटर': 'butter', 'दूध': 'milk', 'दही': 'curd', 'पनीर': 'paneer',
    'चीज': 'cheese', 'चीज़': 'cheese', 'घी': 'ghee', 'ब्रेड': 'bread', 'पाव': 'pav',
    'अंडे': 'eggs', 'अंडा': 'egg', 'चीनी': 'sugar', 'शक्कर': 'sugar', 'गुड़': 'jaggery',
    'नमक': 'salt', 'सेंधा नमक': 'rock salt', 'चाय': 'tea', 'चायपत्ती': 'tea',
    'कॉफ़ी': 'coffee', 'कॉफी': 'coffee', 'बिस्कुट': 'biscuit', 'बिस्किट': 'biscuit',
    'नमकीन': 'namkeen', 'भुजिया': 'bhujia', 'चिप्स': 'chips', 'मैगी': 'maggi',
    'नूडल्स': 'noodles', 'पास्ता': 'pasta', 'सॉस': 'sauce', 'केचप': 'ketchup',
    'काजू': 'kaju cashew', 'बादाम': 'badam almond', 'किशमिश': 'kishmish', 'पिस्ता': 'pista',
    'मखाना': 'makhana', 'मूंगफली': 'peanut',
    'हल्दी': 'turmeric', 'मिर्च': 'chilli', 'मिर्ची': 'chilli', 'लाल मिर्च': 'red chilli',
    'धनिया': 'coriander', 'जीरा': 'jeera', 'राई': 'mustard seeds', 'गरम मसाला': 'garam masala', 'मसाला': 'masala',
    'साबुन': 'soap', 'शैम्पू': 'shampoo', 'शैंपू': 'shampoo', 'सर्फ': 'surf detergent',
    'डिटर्जेंट': 'detergent', 'टूथपेस्ट': 'toothpaste', 'ब्रश': 'toothbrush'
}

# Known Indian grocery brands (both English and Devanagari)
HINDI_BRANDS = {
    'अमूल': 'Amul', 'फॉर्च्यून': 'Fortune', 'आशीर्वाद': 'Aashirvaad', 'टाटा': 'Tata', 'पारले': 'Parle',
    'ब्रिटानिया': 'Britannia', 'सफोला': 'Saffola', 'एमडीएच': 'MDH', 'एवरेस्ट': 'Everest',
    'सर्फ एक्सेल': 'Surf Excel', 'एरियल': 'Ariel', 'रिन': 'Rin', 'डेटॉल': 'Dettol',
    'लाइफबॉय': 'Lifebuoy', 'कोलगेट': 'Colgate', 'नेस्ले': 'Nestle', 'मैगी': 'Maggi',
    'हल्दीराम': 'Haldiram', 'किसान': 'Kissan', 'सनफीस्ट': 'Sunfeast', 'कैडबरी': 'Cadbury',
    'हॉर्लिक्स': 'Horlicks', 'बॉर्नविटा': 'Bournvita', 'प्रीमिया': 'Premia', 'जेमिनी': 'Gemini',
    'धारा': 'Dhara', 'मदर डेयरी': 'Mother Dairy', 'पिल्सबरी': 'Pillsbury', 'गोदरेज': 'Godrej'
}

KNOWN_BRANDS = [
    "amul", "fortune", "aashirvaad", "tata", "parle", "britannia", "saffola",
    "dharampal", "mdh", "everest", "surf excel", "ariel", "rin", "dettol",
    "lifebuoy", "colgate", "pepsodent", "nestle", "maggi", "haldiram",
    "kissan", "sunfeast", "cadbury", "horlicks", "bournvita", "bru", "nescafe",
    "premia", "gemini", "dhara", "mother dairy", "pillsbury", "godrej"
]


class BaseAIAdapter:
    """Abstract interface for AI parsing adapter."""
    def parse_hinglish_order(self, text: str) -> AIParsedInput:
        raise NotImplementedError


class RuleBasedHinglishAIAdapter(BaseAIAdapter):
    """
    Robust local rule-based Hinglish & Hindi entity extractor.
    Parses conversational Indian shop inputs in English, Hinglish, and Hindi (Devanagari):
    - 'Bhaiya 2 kilo atta, ek Amul butter aur 3 litre tel.'
    - '4 किलो आटा एक बटर 3 लीटर तेल'
    - 'आता 2 पाकीट दूध पाठवून द्या' (Marathi urgent delivery)
    """

    def parse_hinglish_order(self, text: str) -> AIParsedInput:
        if not text or not text.strip():
            return AIParsedInput(items=[], flags=["Context Warning: No audible speech or text detected."], context_status="INAUDIBLE")

        raw_input = text.strip()
        # Normalize Devanagari digits to 0-9 for uniform processing
        normalized_input = raw_input.translate(DEVANAGARI_DIGITS)
        text_lower = normalized_input.lower()
        flags: List[str] = []
        delivery_note: Optional[str] = None
        context_status = "CLEAR"

        # -------------------------------------------------------------
        # Marathi / Hinglish Disambiguation: "Aata" (Now) vs "Atta" (Flour)
        # -------------------------------------------------------------
        has_temporal_aata = bool(
            re.search(r'\b(aata|atta|आता)\s+(bhej|de\b|dya|pahije|lagel|nikal|lao|kar\b|delivery|jaldi|urgent|पाठवा|पाठवून|द्या|द्यावे|लागेल|लवकर|तात्काळ)\b', text_lower) or
            re.search(r'\b(bhej|de\b|dya|pahije|lagel|jaldi|urgent|पाठवा|द्या)\s+(aata|atta|आता)\b', text_lower) or
            re.search(r'^(aata|atta|आता)\s+\d+.*(bhej|de|dya|chahiye|पाठवा|द्या)', text_lower)
        )

        has_commodity_atta = bool(
            re.search(r'(\d+|ek|do|teen|char|chaar|paanch|panch|aadha|half|एक|दो|तीन|चार|पांच|पाँच|आधा|पाव|\bkg\b|\bkilo\b|\bpacket\b|किलो|केजी|पैकेट)\s*(kilo|kg|packet|g|gm|किलो|केजी|पैकेट)?\s*(atta|aata|आटा|गेहूं)\b', text_lower) or
            re.search(r'\b(atta|aata|आटा)\s+(\d+|kilo|kg|किलो|केजी)\b', text_lower) or
            re.search(r'\b(aashirvaad|pillsbury|fortune|gehun|sharbati|flour|आशीर्वाद|फॉर्च्यून)\s+(atta|aata|आटा)\b', text_lower) or
            re.search(r'\b(atta|aata|आटा)\s+(packet|bori|bag|thaili|पैकेट|बोरी|थैली)\b', text_lower) or
            'आटा' in text_lower
        )

        cleaned = normalized_input

        if has_temporal_aata and has_commodity_atta:
            flags.append("🟢 Multi-Context Resolved: Detected Wheat Flour ('Atta') AND Marathi Temporal Urgency ('Aata' -> Deliver Now).")
            delivery_note = "Deliver immediately (Customer requested 'Aata / Now')."
            cleaned = re.sub(r'\b(aata|atta|आता)\s+(bhej|de|dya|pahije|lagel|nikal|lao|kar|delivery|पाठवा|द्या)\b', r'\2', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'\b(bhej|de|dya|pahije|lagel|पाठवा|द्या)\s+(aata|atta|आता)\b', r'\1', cleaned, flags=re.IGNORECASE)
        elif has_temporal_aata and not has_commodity_atta:
            flags.append("🟢 Marathi Linguistic Context: Resolved 'Aata' as Temporal Adverb (Deliver Immediately), not Wheat Flour.")
            delivery_note = "Deliver immediately (Customer requested 'Aata / Now')."
            cleaned = re.sub(r'\b(aata|atta|आता)\b', '', cleaned, flags=re.IGNORECASE)
        elif has_commodity_atta:
            flags.append("🟢 Linguistic Disambiguation: Confirmed 'Atta' as Wheat Flour commodity based on numeric quantity/unit context.")
        elif re.search(r'\b(atta|aata)\b', text_lower) and not has_commodity_atta and not has_temporal_aata:
            flags.append("🟡 Context Ambiguity: 'Atta' can mean Marathi 'Aata' (Now) or Wheat Flour. Clarification recommended.")
            context_status = "AMBIGUOUS"

        # Check for delivery time modifiers
        if re.search(r'\b(kal subah|tomorrow morning|उद्या सकाळी)\b', text_lower):
            delivery_note = "Deliver tomorrow morning."
            flags.append("📅 Delivery Preference: Identified schedule for 'Kal Subah'.")
        elif re.search(r'\b(aaj shaam|today evening|आज संध्याकाळी)\b', text_lower):
            delivery_note = "Deliver today evening."
            flags.append("📅 Delivery Preference: Identified schedule for 'Aaj Shaam'.")

        # Strip conversational filler prefixes & suffixes (both Hinglish and Hindi)
        cleaned = re.sub(r'^(bhaiya|bhai|sunona|suno|kaka|uncle|chachu|भैया|भाई|सुनो|सुनिए|काका|चाचा|अंकल)\b[,:\s]*', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\b(dena|dedo|de do|chahiye|pack karna|bhejo|nikal do|देना|दे दो|दीजिए|चाहिए|भेज दो|भेजो|पैक कर दो|डाल दो|निकाल दो|लाओ)\b.*$', '', cleaned, flags=re.IGNORECASE)

        # -------------------------------------------------------------
        # Multi-Item Splitting: Conjunctions + Quantifier Boundaries
        # -------------------------------------------------------------
        item_clauses = self._segment_into_item_clauses(cleaned)
        items: List[ParsedOrderItem] = []

        for clause in item_clauses:
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

    def _segment_into_item_clauses(self, text: str) -> List[str]:
        """
        Splits text by conjunctions (aur, and, tatha, evam, और, तथा, एवं, व, commas, semicolons)
        AND detects quantifier/number transitions when multiple items are listed without conjunctions
        (e.g., '4 किलो आटा एक बटर 3 लीटर तेल' -> ['4 किलो आटा', 'एक बटर', '3 लीटर तेल']).
        """
        initial_clauses = re.split(r'\s*(?:,|\n|;|\baur\b|\band\b|\btatha\b|\bevam\b|और|तथा|एवं|\bव\b)\s*', text, flags=re.IGNORECASE)
        segmented: List[str] = []

        for clause in initial_clauses:
            clause = clause.strip()
            if not clause:
                continue
            words = clause.split()
            current_words: List[str] = []
            has_product = False

            for w in words:
                w_lower = w.lower()
                is_num = (
                    bool(re.match(r'^\d+(\.\d+)?(kg|kilo|g|gm|l|ltr|litre|liter|ml|pkt|packet)?$', w_lower)) or
                    w_lower in HINDI_NUMBERS
                )

                if is_num and has_product:
                    # New item starts here!
                    segmented.append(' '.join(current_words))
                    current_words = [w]
                    has_product = False
                else:
                    current_words.append(w)
                    if not is_num and w_lower not in UNIT_MAPPING:
                        has_product = True

            if current_words:
                segmented.append(' '.join(current_words))

        return segmented

    def _extract_item_from_clause(self, clause: str) -> Optional[ParsedOrderItem]:
        raw_snippet = clause.strip()
        words = raw_snippet.split()
        if not words:
            return None

        quantity: float = 1.0
        unit: Optional[str] = None
        brand: Optional[str] = None

        # 1. Check first 1-2 words for quantity and attached unit (e.g. 500g, 4, ek, एक)
        matched_idx = 0
        w0 = words[0].lower()

        # Check attached quantity and unit like '500g', '2kg', '1L', '4किलो'
        m_attached = re.match(r'^(\d+(?:\.\d+)?)([a-zA-Z]+|किलो|ग्राम|लीटर|पैकेट)?$', w0)
        if m_attached:
            quantity = float(m_attached.group(1))
            raw_u = m_attached.group(2)
            if raw_u and raw_u.lower() in UNIT_MAPPING:
                unit = UNIT_MAPPING[raw_u.lower()]
            matched_idx = 1
        elif w0 in HINDI_NUMBERS:
            quantity = float(HINDI_NUMBERS[w0])
            matched_idx = 1

        # 2. Check next word for standalone unit if not already captured
        remaining_words = words[matched_idx:]
        if remaining_words and not unit:
            w_unit = remaining_words[0].lower()
            if w_unit in UNIT_MAPPING:
                unit = UNIT_MAPPING[w_unit]
                remaining_words = remaining_words[1:]

        remaining_str = " ".join(remaining_words).strip()

        # 3. Extract Brand (Devanagari and English)
        rem_lower = remaining_str.lower()
        for hb, eb in sorted(HINDI_BRANDS.items(), key=lambda x: len(x[0]), reverse=True):
            if hb in remaining_str:
                brand = eb
                remaining_str = remaining_str.replace(hb, ' ').strip()
                rem_lower = remaining_str.lower()
                break

        if not brand:
            for b in sorted(KNOWN_BRANDS, key=len, reverse=True):
                if re.search(r'\b' + re.escape(b) + r'\b', rem_lower):
                    brand = b.title()
                    rem_lower = re.sub(r'\b' + re.escape(b) + r'\b', '', rem_lower).strip()
                    break

        # 4. Remove filler words (English, Hinglish, and Hindi)
        cleaned_product = re.sub(
            r'\b(ka|ki|ke|wala|wali|woh|yeh|का|की|के|वाला|वाली|वाले|वो|वह|यह|ये)\b',
            ' ',
            rem_lower
        ).strip()
        cleaned_product = re.sub(r'\s+', ' ', cleaned_product)

        # 5. Translate Hindi Devanagari Commodity to English catalog term
        translated_commodity = None
        for hc, ec in sorted(HINDI_COMMODITIES.items(), key=lambda x: len(x[0]), reverse=True):
            if hc in cleaned_product:
                translated_commodity = ec
                cleaned_product = cleaned_product.replace(hc, ec).strip()
                break

        product_name = cleaned_product if cleaned_product else (translated_commodity or brand or "unknown product")

        # 6. Confidence Scoring
        confidence = 0.95
        if "woh" in raw_snippet.lower() or "wala" in raw_snippet.lower() or product_name == "unknown product":
            confidence = 0.40

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
