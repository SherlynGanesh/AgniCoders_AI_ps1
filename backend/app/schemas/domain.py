from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal
from datetime import datetime


# ================= Base Schemas =================
class ShopBase(BaseModel):
    name: str
    address: Optional[str] = None
    city: str
    state: str
    pincode: Optional[str] = None
    phone: Optional[str] = None
    active: bool = True
    data_source: str = "SYNTHETIC_DEMO"


class ShopResponse(ShopBase):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ProductVariantResponse(BaseModel):
    id: int
    product_id: int
    size: Optional[float] = None
    unit: Optional[str] = None
    price: Decimal
    mrp: Optional[Decimal] = None
    barcode: Optional[str] = None
    normalized_unit: Optional[str] = None
    variant_label: str
    active: bool
    data_source: str
    model_config = ConfigDict(from_attributes=True)


class ProductResponse(BaseModel):
    id: int
    category_id: Optional[int] = None
    name: str
    brand: Optional[str] = None
    sku: Optional[str] = None
    description: Optional[str] = None
    normalized_name: str
    normalized_brand: Optional[str] = None
    active: bool
    data_source: str
    variants: List[ProductVariantResponse] = []
    model_config = ConfigDict(from_attributes=True)


class InventoryResponse(BaseModel):
    id: int
    shop_id: int
    variant_id: int
    quantity: int
    reserved_quantity: int
    low_stock_threshold: int
    updated_at: datetime
    variant: Optional[ProductVariantResponse] = None
    model_config = ConfigDict(from_attributes=True)


# ================= AI & Matching Contracts =================
class ParsedOrderItem(BaseModel):
    raw_text: str
    product: str
    brand: Optional[str] = None
    quantity: int = Field(default=1, ge=1)
    unit: Optional[str] = None
    confidence: float = Field(default=0.90, ge=0.0, le=1.0)


class AIParsedInput(BaseModel):
    items: List[ParsedOrderItem]
    delivery_note: Optional[str] = None
    flags: List[str] = []
    context_status: str = "CLEAR"  # CLEAR, AMBIGUOUS, INCOMPLETE, LINGUISTIC_DISAMBIGUATION


class ProductMatchCandidate(BaseModel):
    variant_id: int
    product_id: int
    product_name: str
    brand: Optional[str] = None
    variant_label: str
    size: Optional[float] = None
    unit: Optional[str] = None
    price: Decimal
    mrp: Optional[Decimal] = None
    stock: int
    match_score: float
    match_type: str  # EXACT_ALIAS, SEMANTIC, LEXICAL, BRAND_MATCH
    is_ambiguous: bool = False
    is_out_of_stock: bool = False


# ================= Clarification Schemas =================
class ClarificationOption(BaseModel):
    variant_id: int
    label: str
    price: Decimal
    stock: int


class ClarificationResponse(BaseModel):
    id: int
    order_id: int
    ambiguous_text: str
    question: str
    options: List[Dict[str, Any]]
    resolved: bool
    selected_variant_id: Optional[int] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ClarificationResolveRequest(BaseModel):
    clarification_id: int
    selected_variant_id: int


# ================= Order & Billing Schemas =================
class OrderItemResponse(BaseModel):
    id: int
    variant_id: int
    product_name: Optional[str] = None
    brand: Optional[str] = None
    variant_label: Optional[str] = None
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    confidence: Optional[float] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class OrderCreateRequest(BaseModel):
    shop_id: int
    raw_input: str
    customer_id: Optional[int] = None


class OrderResponse(BaseModel):
    id: int
    shop_id: int
    customer_id: Optional[int] = None
    status: str
    subtotal: Decimal
    discount: Decimal
    tax: Decimal
    total: Decimal
    confidence: Optional[float] = None
    raw_input: str
    items: List[OrderItemResponse] = []
    clarifications: List[ClarificationResponse] = []
    created_at: datetime
    confirmed_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


# ================= Explainability & What-If =================
class BillDiffItem(BaseModel):
    customer_said: str
    ai_understood: str
    catalog_match: str
    variant_id: int
    stock: int
    unit_price: Decimal
    quantity: int
    item_total: Decimal
    confidence: float
    status: str  # MATCHED, AMBIGUOUS, OUT_OF_STOCK


class OrderExplanationResponse(BaseModel):
    order_id: int
    raw_input: str
    overall_status: str
    diff_items: List[BillDiffItem]
    clarifications: List[ClarificationResponse]


class WhatIfOption(BaseModel):
    variant_id: int
    variant_label: str
    price: Decimal
    quantity: int
    total_price: Decimal
    stock: int


class WhatIfResponse(BaseModel):
    order_id: int
    ambiguous_item: str
    options: List[WhatIfOption]


# ================= Aliases / Shop Memory =================
class AliasCreateRequest(BaseModel):
    shop_id: int
    variant_id: int
    alias_text: str
    confidence: float = 0.95
    source: str = "SHOPKEEPER"


class AliasResponse(BaseModel):
    id: int
    shop_id: int
    variant_id: int
    alias_text: str
    normalized_alias: str
    confidence: float
    source: str
    usage_count: int
    last_used_at: datetime
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ================= Semantic Search =================
class SemanticSearchRequest(BaseModel):
    query: str
    shop_id: Optional[int] = None
    top_k: int = 5


class SemanticSearchItem(BaseModel):
    variant_id: int
    product_name: str
    brand: Optional[str] = None
    variant_label: str
    price: Decimal
    stock: Optional[int] = None
    score: float
    search_type: str
