import os
import sys
import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy.orm import Session

# Add project root to sys.path
sys.path.insert(0, os.path.abspath("."))
from backend.app.database.session import SessionLocal
from backend.app.models.entities import (
    Shop, Shopkeeper, Customer, Product, ProductVariant,
    Inventory, Order, OrderItem, Alias, AIDecision
)
from backend.app.services.billing_service import billing_service
from backend.data_ingestion.normalization import normalize_text


DEMO_SHOPS = [
    {
        "name": "Patil General Store",
        "address": "Shop 4, Laxmi Road, Narayan Peth",
        "city": "Pune",
        "state": "Maharashtra",
        "pincode": "411030",
        "phone": "+91 98220 11111",
        "shopkeeper": "Ramesh Patil",
        "shopkeeper_phone": "+91 98220 11111",
        "shopkeeper_email": "ramesh.patil@demo.local"
    },
    {
        "name": "Sharma Kirana",
        "address": "12 Station Road, Dadar West",
        "city": "Mumbai",
        "state": "Maharashtra",
        "pincode": "400028",
        "phone": "+91 98200 22222",
        "shopkeeper": "Sunil Sharma",
        "shopkeeper_phone": "+91 98200 22222",
        "shopkeeper_email": "sunil.sharma@demo.local"
    },
    {
        "name": "More Provision Store",
        "address": "7 Ram Maruti Road, Naupada",
        "city": "Thane",
        "state": "Maharashtra",
        "pincode": "400602",
        "phone": "+91 98190 33333",
        "shopkeeper": "Ganesh More",
        "shopkeeper_phone": "+91 98190 33333",
        "shopkeeper_email": "ganesh.more@demo.local"
    },
    {
        "name": "Sai Daily Needs",
        "address": "25 College Road, Thatte Nagar",
        "city": "Nashik",
        "state": "Maharashtra",
        "pincode": "422005",
        "phone": "+91 98230 44444",
        "shopkeeper": "Vikas Sai",
        "shopkeeper_phone": "+91 98230 44444",
        "shopkeeper_email": "vikas.sai@demo.local"
    },
    {
        "name": "City Mart",
        "address": "88 Dharampeth Main Road",
        "city": "Nagpur",
        "state": "Maharashtra",
        "pincode": "440010",
        "phone": "+91 98210 55555",
        "shopkeeper": "Amit Verma",
        "shopkeeper_phone": "+91 98210 55555",
        "shopkeeper_email": "amit.verma@demo.local"
    }
]

FIRST_NAMES = ["Aarav", "Rohan", "Sneha", "Pooja", "Rahul", "Priya", "Aniket", "Kavita", "Suresh", "Meena", "Vipin", "Neha", "Deepak", "Sunita", "Rajesh", "Sangeeta", "Ajay", "Shweta"]
LAST_NAMES = ["Kulkarni", "Deshmukh", "Joshi", "Patel", "Shah", "Shinde", "Gupta", "Mehta", "Singh", "Yadav", "Chavan", "Pawar"]


def generate_demo_data():
    print("==================================================")
    print("DUKAANMITRA — Generating Synthetic Demo Data")
    print("==================================================")

    db: Session = SessionLocal()
    try:
        # Verify catalog exists or insert core demo essentials if empty
        variants = db.query(ProductVariant).all()
        if not variants:
            print("Notice: Catalog is currently empty. Seeding essential demo grocery products first...")
            seed_core_catalog(db)
            variants = db.query(ProductVariant).all()

        print(f"Active catalog variants available: {len(variants)}")

        # 1. Create Shops & Shopkeepers
        created_shops = []
        for shop_info in DEMO_SHOPS:
            shop = db.query(Shop).filter_by(name=shop_info["name"]).first()
            if not shop:
                shop = Shop(
                    name=shop_info["name"],
                    address=shop_info["address"],
                    city=shop_info["city"],
                    state=shop_info["state"],
                    pincode=shop_info["pincode"],
                    phone=shop_info["phone"],
                    active=True,
                    data_source="SYNTHETIC_DEMO"
                )
                db.add(shop)
                db.flush()

                sk = Shopkeeper(
                    shop_id=shop.id,
                    name=shop_info["shopkeeper"],
                    phone=shop_info["shopkeeper_phone"],
                    email=shop_info["shopkeeper_email"],
                    active=True,
                    data_source="SYNTHETIC_DEMO"
                )
                db.add(sk)
            created_shops.append(shop)
        db.commit()
        print(f"Shops & Shopkeepers created: {len(created_shops)} stores active.")

        # 2. Generate 60 Synthetic Customers
        existing_custs = db.query(Customer).count()
        customers = []
        if existing_custs < 60:
            for i in range(60):
                c_name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
                phone_num = f"+91 {random.randint(90000, 99999)} {random.randint(10000, 99999)}"
                cust = Customer(
                    shop_id=random.choice(created_shops).id,
                    name=c_name,
                    phone=phone_num,
                    data_source="SYNTHETIC_DEMO"
                )
                db.add(cust)
                customers.append(cust)
            db.commit()
            print("Generated 60 synthetic customers.")
        else:
            customers = db.query(Customer).limit(60).all()

        # 3. Create Shop-Specific Realistic Inventory
        for shop in created_shops:
            for idx, var in enumerate(variants[:80]):
                existing_inv = db.query(Inventory).filter_by(shop_id=shop.id, variant_id=var.id).first()
                if not existing_inv:
                    # Realistic distribution
                    if idx % 15 == 0:
                        stock_qty = 0  # Out-of-stock scenario
                    elif idx % 7 == 0:
                        stock_qty = random.randint(1, 3)  # Low stock
                    elif idx % 2 == 0:
                        stock_qty = random.randint(20, 60)  # Fast moving
                    else:
                        stock_qty = random.randint(5, 20)  # Standard stock

                    inv = Inventory(
                        shop_id=shop.id,
                        variant_id=var.id,
                        quantity=stock_qty,
                        reserved_quantity=0,
                        low_stock_threshold=5
                    )
                    db.add(inv)
        db.commit()
        print("Shop-specific inventory initialized with realistic stock levels.")

        # 4. Create 20+ Shop Memory Aliases
        seed_shop_aliases(db, created_shops[0].id, variants)

        # 5. Create 500+ Demo Historical Orders
        existing_orders = db.query(Order).count()
        if existing_orders < 500:
            print(f"Creating historical demo orders (target: 500)...")
            now = datetime.now(timezone.utc)
            statuses = ["CONFIRMED", "COMPLETED", "READY", "CONFIRMED", "CONFIRMED"]

            for i in range(500 - existing_orders):
                target_shop = random.choice(created_shops)
                target_cust = random.choice(customers)
                order_time = now - timedelta(days=random.randint(0, 90), hours=random.randint(0, 23))

                order = Order(
                    shop_id=target_shop.id,
                    customer_id=target_cust.id,
                    status=random.choice(statuses),
                    subtotal=Decimal("0.00"),
                    discount=Decimal("0.00"),
                    tax=Decimal("0.00"),
                    total=Decimal("0.00"),
                    confidence=Decimal(str(round(random.uniform(0.88, 0.98), 2))),
                    raw_input=f"Demo historical grocery order #{i+1}",
                    created_at=order_time,
                    updated_at=order_time,
                    confirmed_at=order_time
                )
                db.add(order)
                db.flush()

                # Add 1 to 4 items
                num_items = random.randint(1, 4)
                order_subtotal = Decimal("0.00")
                sample_vars = random.sample(variants[:80], num_items)

                for svar in sample_vars:
                    qty = random.randint(1, 3)
                    unit_p = svar.price
                    item_tot = billing_service.quantize_money(unit_p * Decimal(qty))
                    order_subtotal += item_tot

                    oi = OrderItem(
                        order_id=order.id,
                        variant_id=svar.id,
                        quantity=qty,
                        unit_price=unit_p,
                        total_price=item_tot,
                        confidence=Decimal("0.95"),
                        created_at=order_time
                    )
                    db.add(oi)

                order.subtotal = order_subtotal
                order.total = order_subtotal

            db.commit()
            print("500+ historical demo orders generated with point-in-time pricing.")

        print("\nDemo data generation completed successfully!")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Demo data generation failed: {e}")
        raise e
    finally:
        db.close()


def seed_core_catalog(db: Session):
    """Seeds baseline catalog products for immediate hackathon readiness."""
    from backend.app.models.entities import Category, Product, ProductVariant

    categories = [
        ("Grocery", "Staples and daily items"),
        ("Dairy", "Milk, butter, curd"),
        ("Edible Oil", "Cooking oils"),
        ("Atta & Flour", "Wheat flour and grains"),
        ("Snacks & Biscuits", "Packaged snacks and biscuits")
    ]
    cat_objs = {}
    for c_name, c_desc in categories:
        cat = Category(
            name=c_name,
            normalized_name=normalize_text(c_name),
            description=c_desc,
            data_source="SYNTHETIC_DEMO"
        )
        db.add(cat)
        db.flush()
        cat_objs[c_name] = cat.id

    # Core Products
    catalog_items = [
        # Atta
        ("Aashirvaad Shudh Chakki Atta", "Aashirvaad", "Atta & Flour", [
            (5.0, "kg", Decimal("245.00"), Decimal("270.00"), "5 kg"),
            (10.0, "kg", Decimal("480.00"), Decimal("520.00"), "10 kg")
        ]),
        ("Fortune Chakki Fresh Atta", "Fortune", "Atta & Flour", [
            (5.0, "kg", Decimal("230.00"), Decimal("255.00"), "5 kg"),
            (10.0, "kg", Decimal("450.00"), Decimal("490.00"), "10 kg")
        ]),
        # Butter
        ("Amul Butter", "Amul", "Dairy", [
            (100.0, "g", Decimal("58.00"), Decimal("60.00"), "100 g"),
            (500.0, "g", Decimal("285.00"), Decimal("295.00"), "500 g")
        ]),
        # Edible Oil
        ("Fortune Sunlite Refined Sunflower Oil", "Fortune", "Edible Oil", [
            (1.0, "l", Decimal("145.00"), Decimal("160.00"), "1 L"),
            (5.0, "l", Decimal("720.00"), Decimal("780.00"), "5 L")
        ]),
        ("Saffola Gold Pro Healthy Lifestyle Oil", "Saffola", "Edible Oil", [
            (1.0, "l", Decimal("175.00"), Decimal("195.00"), "1 L"),
            (5.0, "l", Decimal("840.00"), Decimal("920.00"), "5 L")
        ]),
        # Salt
        ("Tata Salt Vacuum Evaporated Iodised", "Tata", "Grocery", [
            (1.0, "kg", Decimal("28.00"), Decimal("30.00"), "1 kg")
        ]),
        # Biscuits
        ("Parle-G Gold Glucose Biscuit", "Parle", "Snacks & Biscuits", [
            (100.0, "g", Decimal("10.00"), Decimal("10.00"), "100 g"),
            (1.0, "kg", Decimal("90.00"), Decimal("100.00"), "1 kg")
        ]),
        ("Britannia Good Day Butter Cookies", "Britannia", "Snacks & Biscuits", [
            (200.0, "g", Decimal("40.00"), Decimal("45.00"), "200 g")
        ]),
        # Maggi
        ("Maggi 2-Minute Masala Noodles", "Nestle", "Snacks & Biscuits", [
            (70.0, "g", Decimal("14.00"), Decimal("14.00"), "70 g"),
            (280.0, "g", Decimal("56.00"), Decimal("56.00"), "4 x 70 g")
        ])
    ]

    for p_name, brand, cat_name, vars_list in catalog_items:
        prod = Product(
            category_id=cat_objs.get(cat_name),
            name=p_name,
            brand=brand,
            normalized_name=normalize_text(p_name),
            normalized_brand=normalize_text(brand),
            data_source="SYNTHETIC_DEMO",
            sku=f"CORE-{normalize_text(brand)}-{random.randint(100, 999)}"
        )
        db.add(prod)
        db.flush()

        for sz, un, pr, mr, lbl in vars_list:
            var = ProductVariant(
                product_id=prod.id,
                size=Decimal(str(sz)),
                unit=un,
                price=pr,
                mrp=mr,
                variant_label=lbl,
                normalized_unit=un,
                data_source="SYNTHETIC_DEMO"
            )
            db.add(var)
    db.commit()


def seed_shop_aliases(db: Session, shop_id: int, variants: list):
    """Seeds 20+ shop memory aliases for testing shopkeeper Hinglish idioms."""
    # Find key variants
    amul_butter_500g = None
    amul_butter_100g = None
    fortune_oil_1l = None
    fortune_oil_5l = None
    aashirvaad_atta_5kg = None
    tata_salt = None
    parle_g = None
    maggi = None

    for v in variants:
        p_name = v.product.name.lower()
        lbl = v.variant_label.lower()
        if "amul" in p_name and "butter" in p_name:
            if "500" in lbl:
                amul_butter_500g = v
            elif "100" in lbl:
                amul_butter_100g = v
        elif "fortune" in p_name and ("sunflower" in p_name or "oil" in p_name):
            if "1 l" in lbl:
                fortune_oil_1l = v
            elif "5 l" in lbl:
                fortune_oil_5l = v
        elif "aashirvaad" in p_name and "atta" in p_name and "5" in lbl:
            aashirvaad_atta_5kg = v
        elif "salt" in p_name and "tata" in p_name:
            tata_salt = v
        elif "parle" in p_name:
            parle_g = v
        elif "maggi" in p_name:
            maggi = v

    aliases_to_seed = []
    if amul_butter_500g:
        aliases_to_seed.extend([
            ("makkhan", amul_butter_500g.id, Decimal("0.96"), "SHOPKEEPER", 18),
            ("amul wala", amul_butter_500g.id, Decimal("0.95"), "SHOPKEEPER", 12),
            ("butter", amul_butter_500g.id, Decimal("0.92"), "SYSTEM", 10),
            ("peela makkhan", amul_butter_500g.id, Decimal("0.90"), "CUSTOMER_HISTORY", 5)
        ])
    if fortune_oil_1l:
        aliases_to_seed.extend([
            ("woh wala tel", fortune_oil_1l.id, Decimal("0.88"), "SHOPKEEPER", 14),
            ("fortune tel", fortune_oil_1l.id, Decimal("0.95"), "CUSTOMER_HISTORY", 20),
            ("sunflower oil", fortune_oil_1l.id, Decimal("0.94"), "SYSTEM", 9),
            ("mitha tel", fortune_oil_1l.id, Decimal("0.85"), "SHOPKEEPER", 6)
        ])
    if aashirvaad_atta_5kg:
        aliases_to_seed.extend([
            ("laal packet wala atta", aashirvaad_atta_5kg.id, Decimal("0.95"), "SHOPKEEPER", 22),
            ("aashirvaad atta", aashirvaad_atta_5kg.id, Decimal("0.96"), "SYSTEM", 30),
            ("chakki atta", aashirvaad_atta_5kg.id, Decimal("0.88"), "CUSTOMER_HISTORY", 11),
            ("gehu atta", aashirvaad_atta_5kg.id, Decimal("0.85"), "SHOPKEEPER", 7)
        ])
    if tata_salt:
        aliases_to_seed.extend([
            ("namak", tata_salt.id, Decimal("0.98"), "SHOPKEEPER", 45),
            ("tata namak", tata_salt.id, Decimal("0.99"), "SYSTEM", 50),
            ("desh ka namak", tata_salt.id, Decimal("0.90"), "CUSTOMER_HISTORY", 8)
        ])
    if parle_g:
        aliases_to_seed.extend([
            ("biskut parle", parle_g.id, Decimal("0.95"), "SHOPKEEPER", 35),
            ("chai biscuit", parle_g.id, Decimal("0.86"), "CUSTOMER_HISTORY", 9),
            ("parle biscuit", parle_g.id, Decimal("0.98"), "SYSTEM", 40)
        ])
    if maggi:
        aliases_to_seed.extend([
            ("maggi", maggi.id, Decimal("0.98"), "SHOPKEEPER", 55),
            ("noodles", maggi.id, Decimal("0.92"), "SYSTEM", 25),
            ("2 minute wali", maggi.id, Decimal("0.89"), "CUSTOMER_HISTORY", 12)
        ])

    for alias_txt, var_id, conf, src, cnt in aliases_to_seed:
        norm_a = normalize_text(alias_txt)
        existing = db.query(Alias).filter_by(
            shop_id=shop_id, normalized_alias=norm_a, variant_id=var_id
        ).first()
        if not existing:
            db.add(Alias(
                shop_id=shop_id,
                variant_id=var_id,
                alias_text=alias_txt,
                normalized_alias=norm_a,
                confidence=conf,
                source=src,
                usage_count=cnt
            ))
    db.commit()
    print("20+ shop memory aliases seeded.")


if __name__ == "__main__":
    generate_demo_data()
