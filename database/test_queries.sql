-- DukaanMitra Verification & Debug Queries

-- 1. Check database version and extensions
SELECT version();
SELECT * FROM pg_available_extensions WHERE name = 'vector';
SELECT * FROM pg_extension WHERE extname = 'vector';

-- 2. Verify all 13 core tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public'
ORDER BY table_name;

-- 3. Check shops and shopkeepers
SELECT s.id, s.name, s.city, sk.name AS shopkeeper, sk.phone 
FROM shops s
JOIN shopkeepers sk ON s.id = sk.shop_id;

-- 4. Check product count by category
SELECT c.name AS category, COUNT(p.id) AS total_products
FROM categories c
LEFT JOIN products p ON c.id = p.category_id
GROUP BY c.name
ORDER BY total_products DESC;

-- 5. Test shop memory / aliases for Patil General Store (shop_id = 1)
SELECT a.alias_text, a.confidence, a.usage_count, p.name AS product, pv.variant_label, pv.price
FROM aliases a
JOIN product_variants pv ON a.variant_id = pv.id
JOIN products p ON pv.product_id = p.id
WHERE a.shop_id = 1
ORDER BY a.usage_count DESC;

-- 6. Check inventory stock levels for shop 1 (including low stock and zero stock)
SELECT p.name, pv.variant_label, i.quantity AS in_stock, pv.price
FROM inventory i
JOIN product_variants pv ON i.variant_id = pv.id
JOIN products p ON pv.product_id = p.id
WHERE i.shop_id = 1
ORDER BY i.quantity ASC
LIMIT 15;

-- 7. Audit recent orders and their status
SELECT o.id, o.status, o.total, o.raw_input, COUNT(oi.id) AS item_count, o.created_at
FROM orders o
LEFT JOIN order_items oi ON o.id = oi.order_id
GROUP BY o.id
ORDER BY o.created_at DESC
LIMIT 10;
