-- DukaanMitra Database Schema Reference
-- Tagline: "Aap Bolo, DukaanMitra Sambhale."
-- Engine: PostgreSQL 18+

-- Enable pgvector if available
-- CREATE EXTENSION IF NOT EXISTS vector;

-- 1. Shops Table
CREATE TABLE IF NOT EXISTS shops (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    address VARCHAR(500),
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    pincode VARCHAR(20),
    phone VARCHAR(30),
    active BOOLEAN DEFAULT TRUE NOT NULL,
    data_source VARCHAR(50) DEFAULT 'SYNTHETIC_DEMO' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 2. Shopkeepers Table
CREATE TABLE IF NOT EXISTS shopkeepers (
    id SERIAL PRIMARY KEY,
    shop_id INTEGER NOT NULL REFERENCES shops(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(30) NOT NULL,
    email VARCHAR(255),
    active BOOLEAN DEFAULT TRUE NOT NULL,
    data_source VARCHAR(50) DEFAULT 'SYNTHETIC_DEMO' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 3. Categories Table
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) UNIQUE NOT NULL,
    normalized_name VARCHAR(150) NOT NULL,
    description TEXT,
    data_source VARCHAR(50) DEFAULT 'KAGGLE_CATALOG' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_categories_norm_name ON categories(normalized_name);

-- 4. Products Table
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    brand VARCHAR(150),
    sku VARCHAR(100),
    description TEXT,
    normalized_name VARCHAR(255) NOT NULL,
    normalized_brand VARCHAR(150),
    active BOOLEAN DEFAULT TRUE NOT NULL,
    data_source VARCHAR(50) DEFAULT 'KAGGLE_CATALOG' NOT NULL,
    source_dataset VARCHAR(100),
    source_record_id VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_products_cat_norm ON products(category_id, normalized_name, normalized_brand);
CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku);

-- 5. Product Variants Table
CREATE TABLE IF NOT EXISTS product_variants (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    size NUMERIC(10, 2),
    unit VARCHAR(50),
    price NUMERIC(10, 2) NOT NULL,
    mrp NUMERIC(10, 2),
    barcode VARCHAR(100),
    normalized_unit VARCHAR(50),
    variant_label VARCHAR(100) NOT NULL,
    active BOOLEAN DEFAULT TRUE NOT NULL,
    data_source VARCHAR(50) DEFAULT 'KAGGLE_CATALOG' NOT NULL,
    source_dataset VARCHAR(100),
    source_record_id VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_variants_product_id ON product_variants(product_id);
CREATE INDEX IF NOT EXISTS idx_variants_barcode ON product_variants(barcode);

-- 6. Inventory Table (Shop-specific)
CREATE TABLE IF NOT EXISTS inventory (
    id SERIAL PRIMARY KEY,
    shop_id INTEGER NOT NULL REFERENCES shops(id) ON DELETE CASCADE,
    variant_id INTEGER NOT NULL REFERENCES product_variants(id) ON DELETE CASCADE,
    quantity INTEGER DEFAULT 0 NOT NULL,
    reserved_quantity INTEGER DEFAULT 0 NOT NULL,
    low_stock_threshold INTEGER DEFAULT 5 NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT uq_shop_variant_inventory UNIQUE (shop_id, variant_id)
);
CREATE INDEX IF NOT EXISTS idx_inventory_shop_variant ON inventory(shop_id, variant_id);

-- 7. Customers Table
CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    shop_id INTEGER REFERENCES shops(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(30),
    data_source VARCHAR(50) DEFAULT 'SYNTHETIC_DEMO' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 8. Orders Table
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    shop_id INTEGER NOT NULL REFERENCES shops(id) ON DELETE CASCADE,
    customer_id INTEGER REFERENCES customers(id) ON DELETE SET NULL,
    status VARCHAR(50) DEFAULT 'DRAFT' NOT NULL,
    subtotal NUMERIC(10, 2) DEFAULT 0.00 NOT NULL,
    discount NUMERIC(10, 2) DEFAULT 0.00 NOT NULL,
    tax NUMERIC(10, 2) DEFAULT 0.00 NOT NULL,
    total NUMERIC(10, 2) DEFAULT 0.00 NOT NULL,
    confidence NUMERIC(4, 3),
    raw_input TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    confirmed_at TIMESTAMP WITH TIME ZONE
);
CREATE INDEX IF NOT EXISTS idx_orders_shop_status ON orders(shop_id, created_at, status);

-- 9. Order Items Table (Point-in-time pricing)
CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    variant_id INTEGER NOT NULL REFERENCES product_variants(id) ON DELETE RESTRICT,
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(10, 2) NOT NULL,
    total_price NUMERIC(10, 2) NOT NULL,
    confidence NUMERIC(4, 3),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);

-- 10. Aliases / Shop Memory Table
CREATE TABLE IF NOT EXISTS aliases (
    id SERIAL PRIMARY KEY,
    shop_id INTEGER NOT NULL REFERENCES shops(id) ON DELETE CASCADE,
    variant_id INTEGER NOT NULL REFERENCES product_variants(id) ON DELETE CASCADE,
    alias_text VARCHAR(255) NOT NULL,
    normalized_alias VARCHAR(255) NOT NULL,
    confidence NUMERIC(4, 3) DEFAULT 0.500 NOT NULL,
    source VARCHAR(50) DEFAULT 'SHOPKEEPER' NOT NULL,
    usage_count INTEGER DEFAULT 1 NOT NULL,
    last_used_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT uq_shop_alias_variant UNIQUE (shop_id, normalized_alias, variant_id)
);
CREATE INDEX IF NOT EXISTS idx_aliases_shop_alias ON aliases(shop_id, normalized_alias);

-- 11. Clarifications Table
CREATE TABLE IF NOT EXISTS clarifications (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    ambiguous_text VARCHAR(255) NOT NULL,
    question VARCHAR(500) NOT NULL,
    options JSONB NOT NULL,
    selected_variant_id INTEGER REFERENCES product_variants(id) ON DELETE SET NULL,
    resolved BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    resolved_at TIMESTAMP WITH TIME ZONE
);
CREATE INDEX IF NOT EXISTS idx_clarifications_order_id ON clarifications(order_id);

-- 12. AI Decisions Table (Audit & Explainability)
CREATE TABLE IF NOT EXISTS ai_decisions (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
    raw_text TEXT NOT NULL,
    parsed_output JSONB NOT NULL,
    confidence NUMERIC(4, 3),
    decision VARCHAR(50) NOT NULL,
    reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ai_decisions_order_id ON ai_decisions(order_id);

-- 13. Product Embeddings Table
CREATE TABLE IF NOT EXISTS product_embeddings (
    id SERIAL PRIMARY KEY,
    variant_id INTEGER NOT NULL REFERENCES product_variants(id) ON DELETE CASCADE,
    text_for_embedding TEXT NOT NULL,
    -- If pgvector is installed:
    -- embedding vector(384),
    embedding JSONB,
    model_name VARCHAR(150) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);
