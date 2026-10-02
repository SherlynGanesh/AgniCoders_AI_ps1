import datetime
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Numeric, DateTime, ForeignKey,
    UniqueConstraint, Index, func, JSON
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

# Universal JSON type: Native JSONB in PostgreSQL, standard JSON in SQLite/testing
JSONType = JSONB().with_variant(JSON(), "sqlite")

# Try importing pgvector Vector type; if not available, fallback to JSONB/Text
try:
    from pgvector.sqlalchemy import Vector
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False
    Vector = None


class Shop(Base):
    __tablename__ = "shops"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    address = Column(String(500), nullable=True)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    pincode = Column(String(20), nullable=True)
    phone = Column(String(30), nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    data_source = Column(String(50), default="SYNTHETIC_DEMO", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    shopkeepers = relationship("Shopkeeper", back_populates="shop", cascade="all, delete-orphan")
    inventories = relationship("Inventory", back_populates="shop", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="shop")
    aliases = relationship("Alias", back_populates="shop", cascade="all, delete-orphan")


class Shopkeeper(Base):
    __tablename__ = "shopkeepers"

    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, ForeignKey("shops.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    phone = Column(String(30), nullable=False)
    email = Column(String(255), nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    data_source = Column(String(50), default="SYNTHETIC_DEMO", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    shop = relationship("Shop", back_populates="shopkeepers")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), unique=True, nullable=False)
    normalized_name = Column(String(150), index=True, nullable=False)
    description = Column(Text, nullable=True)
    data_source = Column(String(50), default="KAGGLE_CATALOG", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    products = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(255), nullable=False)
    brand = Column(String(150), nullable=True)
    sku = Column(String(100), nullable=True, index=True)
    description = Column(Text, nullable=True)
    normalized_name = Column(String(255), nullable=False, index=True)
    normalized_brand = Column(String(150), nullable=True, index=True)
    active = Column(Boolean, default=True, nullable=False)
    data_source = Column(String(50), default="KAGGLE_CATALOG", nullable=False)
    source_dataset = Column(String(100), nullable=True)
    source_record_id = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    category = relationship("Category", back_populates="products")
    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_product_cat_name_brand", "category_id", "normalized_name", "normalized_brand"),
    )


class ProductVariant(Base):
    __tablename__ = "product_variants"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    size = Column(Numeric(10, 2), nullable=True)
    unit = Column(String(50), nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    mrp = Column(Numeric(10, 2), nullable=True)
    barcode = Column(String(100), nullable=True, index=True)
    normalized_unit = Column(String(50), nullable=True)
    variant_label = Column(String(100), nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    data_source = Column(String(50), default="KAGGLE_CATALOG", nullable=False)
    source_dataset = Column(String(100), nullable=True)
    source_record_id = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    product = relationship("Product", back_populates="variants")
    inventories = relationship("Inventory", back_populates="variant", cascade="all, delete-orphan")
    order_items = relationship("OrderItem", back_populates="variant")
    aliases = relationship("Alias", back_populates="variant", cascade="all, delete-orphan")
    embeddings = relationship("ProductEmbedding", back_populates="variant", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_variant_prod_label", "product_id", "variant_label"),
    )


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, ForeignKey("shops.id", ondelete="CASCADE"), nullable=False)
    variant_id = Column(Integer, ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, default=0, nullable=False)
    reserved_quantity = Column(Integer, default=0, nullable=False)
    low_stock_threshold = Column(Integer, default=5, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    shop = relationship("Shop", back_populates="inventories")
    variant = relationship("ProductVariant", back_populates="inventories")

    __table_args__ = (
        UniqueConstraint("shop_id", "variant_id", name="uq_shop_variant_inventory"),
        Index("idx_inventory_shop_variant", "shop_id", "variant_id"),
    )


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, ForeignKey("shops.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(255), nullable=False)
    phone = Column(String(30), nullable=True)
    data_source = Column(String(50), default="SYNTHETIC_DEMO", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    orders = relationship("Order", back_populates="customer")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, ForeignKey("shops.id", ondelete="CASCADE"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(50), default="DRAFT", nullable=False)  # DRAFT, CLARIFICATION_REQUIRED, READY, CONFIRMED, CANCELLED, COMPLETED
    subtotal = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    discount = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    tax = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    total = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    confidence = Column(Numeric(4, 3), nullable=True)
    raw_input = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)

    shop = relationship("Shop", back_populates="orders")
    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    clarifications = relationship("Clarification", back_populates="order", cascade="all, delete-orphan")
    ai_decisions = relationship("AIDecision", back_populates="order", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_orders_shop_created_status", "shop_id", "created_at", "status"),
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    variant_id = Column(Integer, ForeignKey("product_variants.id", ondelete="RESTRICT"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)
    confidence = Column(Numeric(4, 3), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    order = relationship("Order", back_populates="items")
    variant = relationship("ProductVariant", back_populates="order_items")

    __table_args__ = (
        Index("idx_order_items_order_id", "order_id"),
    )


class Alias(Base):
    __tablename__ = "aliases"

    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, ForeignKey("shops.id", ondelete="CASCADE"), nullable=False)
    variant_id = Column(Integer, ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False)
    alias_text = Column(String(255), nullable=False)
    normalized_alias = Column(String(255), nullable=False)
    confidence = Column(Numeric(4, 3), default=Decimal("0.500"), nullable=False)
    source = Column(String(50), default="SHOPKEEPER", nullable=False)  # SHOPKEEPER, AI, CUSTOMER_HISTORY, SYSTEM
    usage_count = Column(Integer, default=1, nullable=False)
    last_used_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    shop = relationship("Shop", back_populates="aliases")
    variant = relationship("ProductVariant", back_populates="aliases")

    __table_args__ = (
        UniqueConstraint("shop_id", "normalized_alias", "variant_id", name="uq_shop_alias_variant"),
        Index("idx_aliases_shop_norm_alias", "shop_id", "normalized_alias"),
    )


class Clarification(Base):
    __tablename__ = "clarifications"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    ambiguous_text = Column(String(255), nullable=False)
    question = Column(String(500), nullable=False)
    options = Column(JSONType, nullable=False)  # List of candidate variants
    selected_variant_id = Column(Integer, ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True)
    resolved = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    order = relationship("Order", back_populates="clarifications")
    selected_variant = relationship("ProductVariant")

    __table_args__ = (
        Index("idx_clarifications_order_id", "order_id"),
    )


class AIDecision(Base):
    __tablename__ = "ai_decisions"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=True)
    raw_text = Column(Text, nullable=False)
    parsed_output = Column(JSONType, nullable=False)
    confidence = Column(Numeric(4, 3), nullable=True)
    decision = Column(String(50), nullable=False)  # MATCHED, AMBIGUOUS, OUT_OF_STOCK, INVALID_PRODUCT, etc.
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    order = relationship("Order", back_populates="ai_decisions")

    __table_args__ = (
        Index("idx_ai_decisions_order_id", "order_id"),
    )


class ProductEmbedding(Base):
    __tablename__ = "product_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    variant_id = Column(Integer, ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False)
    text_for_embedding = Column(Text, nullable=False)
    # If pgvector is present, use Vector(384); otherwise fallback to JSONType
    if HAS_PGVECTOR and Vector is not None:
        embedding = Column(Vector(384).with_variant(JSON, "sqlite"), nullable=True)
    else:
        embedding = Column(JSONType, nullable=True)
    model_name = Column(String(150), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    variant = relationship("ProductVariant", back_populates="embeddings")
