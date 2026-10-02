-- DukaanMitra Core SQL Seed Reference
-- Demonstrates synthetic shops, shopkeepers, and aliases

INSERT INTO shops (id, name, address, city, state, pincode, phone, active, data_source)
VALUES
(1, 'Patil General Store', 'Shop 4, Laxmi Road, Narayan Peth', 'Pune', 'Maharashtra', '411030', '+91 98220 11111', TRUE, 'SYNTHETIC_DEMO'),
(2, 'Sharma Kirana', '12 Station Road, Dadar West', 'Mumbai', 'Maharashtra', '400028', '+91 98200 22222', TRUE, 'SYNTHETIC_DEMO'),
(3, 'More Provision Store', '7 Ram Maruti Road, Naupada', 'Thane', 'Maharashtra', '400602', '+91 98190 33333', TRUE, 'SYNTHETIC_DEMO'),
(4, 'Sai Daily Needs', '25 College Road, Thatte Nagar', 'Nashik', 'Maharashtra', '422005', '+91 98230 44444', TRUE, 'SYNTHETIC_DEMO'),
(5, 'City Mart', '88 Dharampeth Main Road', 'Nagpur', 'Maharashtra', '440010', '+91 98210 55555', TRUE, 'SYNTHETIC_DEMO')
ON CONFLICT (id) DO NOTHING;

INSERT INTO shopkeepers (id, shop_id, name, phone, email, active, data_source)
VALUES
(1, 1, 'Ramesh Patil', '+91 98220 11111', 'ramesh.patil@demo.local', TRUE, 'SYNTHETIC_DEMO'),
(2, 2, 'Sunil Sharma', '+91 98200 22222', 'sunil.sharma@demo.local', TRUE, 'SYNTHETIC_DEMO'),
(3, 3, 'Ganesh More', '+91 98190 33333', 'ganesh.more@demo.local', TRUE, 'SYNTHETIC_DEMO'),
(4, 4, 'Vikas Sai', '+91 98230 44444', 'vikas.sai@demo.local', TRUE, 'SYNTHETIC_DEMO'),
(5, 5, 'Amit Verma', '+91 98210 55555', 'amit.verma@demo.local', TRUE, 'SYNTHETIC_DEMO')
ON CONFLICT (id) DO NOTHING;
