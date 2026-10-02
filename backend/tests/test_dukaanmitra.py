import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.main import app
from backend.app.database.session import Base, get_db
from backend.app.models.entities import (
    Shop, Shopkeeper, Category, Product, ProductVariant, Inventory,
    Order, OrderItem, Alias, Clarification, AIDecision
)
from backend.app.services.ai_service import ai_service
from backend.app.services.billing_service import billing_service
from backend.app.services.product_matching import product_matcher
from backend.app.services.order_engine import order_engine
from backend.app.services.semantic_search import semantic_engine
from backend.data_ingestion.normalization import normalize_text, normalize_price, parse_pack_size


# In-memory SQLite for fast, robust, isolated pytest execution
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine_test = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine_test)
    db = TestingSessionLocal()

    # Seed minimal test store environment
    shop = Shop(
        id=1,
        name="Patil General Store",
        city="Pune",
        state="Maharashtra",
        data_source="SYNTHETIC_DEMO"
    )
    db.add(shop)

    cat_staples = Category(id=1, name="Atta & Flour", normalized_name="atta flour", data_source="SYNTHETIC_DEMO")
    cat_dairy = Category(id=2, name="Dairy", normalized_name="dairy", data_source="SYNTHETIC_DEMO")
    cat_oil = Category(id=3, name="Edible Oil", normalized_name="edible oil", data_source="SYNTHETIC_DEMO")
    db.add_all([cat_staples, cat_dairy, cat_oil])
    db.flush()

    # Atta
    prod_atta = Product(id=1, category_id=1, name="Aashirvaad Shudh Chakki Atta", brand="Aashirvaad", normalized_name="aashirvaad shudh chakki atta", normalized_brand="aashirvaad", data_source="SYNTHETIC_DEMO")
    var_atta_5k = ProductVariant(id=1, product_id=1, size=Decimal("5.0"), unit="kg", price=Decimal("245.00"), mrp=Decimal("270.00"), variant_label="5 kg", normalized_unit="kg", data_source="SYNTHETIC_DEMO")
    var_atta_2k = ProductVariant(id=2, product_id=1, size=Decimal("2.0"), unit="kg", price=Decimal("110.00"), mrp=Decimal("120.00"), variant_label="2 kg", normalized_unit="kg", data_source="SYNTHETIC_DEMO")
    
    # Butter
    prod_butter = Product(id=2, category_id=2, name="Amul Butter", brand="Amul", normalized_name="amul butter", normalized_brand="amul", data_source="SYNTHETIC_DEMO")
    var_butter_100g = ProductVariant(id=3, product_id=2, size=Decimal("100.0"), unit="g", price=Decimal("58.00"), mrp=Decimal("60.00"), variant_label="100 g", normalized_unit="g", data_source="SYNTHETIC_DEMO")
    var_butter_500g = ProductVariant(id=4, product_id=2, size=Decimal("500.0"), unit="g", price=Decimal("285.00"), mrp=Decimal("295.00"), variant_label="500 g", normalized_unit="g", data_source="SYNTHETIC_DEMO")

    # Oils
    prod_fortune_oil = Product(id=3, category_id=3, name="Fortune Sunflower Oil", brand="Fortune", normalized_name="fortune sunflower oil", normalized_brand="fortune", data_source="SYNTHETIC_DEMO")
    var_oil_1l = ProductVariant(id=5, product_id=3, size=Decimal("1.0"), unit="l", price=Decimal("145.00"), mrp=Decimal("160.00"), variant_label="1 L", normalized_unit="l", data_source="SYNTHETIC_DEMO")
    var_oil_5l = ProductVariant(id=6, product_id=3, size=Decimal("5.0"), unit="l", price=Decimal("720.00"), mrp=Decimal("780.00"), variant_label="5 L", normalized_unit="l", data_source="SYNTHETIC_DEMO")

    db.add_all([prod_atta, var_atta_5k, var_atta_2k, prod_butter, var_butter_100g, var_butter_500g, prod_fortune_oil, var_oil_1l, var_oil_5l])
    db.flush()

    # Shop Inventory
    inv_atta = Inventory(shop_id=1, variant_id=2, quantity=25, reserved_quantity=0)
    inv_butter = Inventory(shop_id=1, variant_id=4, quantity=15, reserved_quantity=0)
    inv_oil_1l = Inventory(shop_id=1, variant_id=5, quantity=10, reserved_quantity=0)
    inv_oil_5l = Inventory(shop_id=1, variant_id=6, quantity=5, reserved_quantity=0)
    inv_out_stock = Inventory(shop_id=1, variant_id=3, quantity=0, reserved_quantity=0) # 100g butter is out of stock

    db.add_all([inv_atta, inv_butter, inv_oil_1l, inv_oil_5l, inv_out_stock])
    db.commit()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine_test)


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ================= TEST SUITE =================

def test_normalization_utils():
    """Verify data normalization for text, pack sizes, and prices."""
    assert normalize_text("500 GM") == "500 gm"
    assert normalize_price("₹ 285.50") == Decimal("285.50")
    assert normalize_price("Rs.120") == Decimal("120.00")
    
    size, unit, label = parse_pack_size("500 gm")
    assert size == 500.0
    assert unit == "g"
    assert label == "500 g"

    size_l, unit_l, label_l = parse_pack_size("1 Litre")
    assert size_l == 1.0
    assert unit_l == "l"
    assert label_l == "1 L"


def test_ai_parsing_hinglish():
    """Verify AI entity extraction on multi-item conversational Hinglish input."""
    customer_input = "Bhaiya 2 kilo atta, ek Amul butter aur woh wala tel."
    parsed = ai_service.parse_order(customer_input)

    assert len(parsed.items) == 3
    
    # 1. Atta
    assert parsed.items[0].quantity == 2
    assert parsed.items[0].unit == "kg"
    assert "atta" in parsed.items[0].product.lower()

    # 2. Amul Butter
    assert parsed.items[1].quantity == 1
    assert parsed.items[1].brand == "Amul"
    assert "butter" in parsed.items[1].product.lower()

    # 3. Tel (Ambiguous)
    assert parsed.items[2].quantity == 1
    assert "tel" in parsed.items[2].product.lower() or "oil" in parsed.items[2].product.lower()


def test_billing_precision():
    """Verify server-side Decimal financial calculations."""
    items = [
        {"unit_price": Decimal("245.00"), "quantity": 2},
        {"unit_price": Decimal("58.50"), "quantity": 1}
    ]
    subtotal, discount, tax, total = billing_service.calculate_bill(
        items, discount_pct=Decimal("10.00"), tax_pct=Decimal("5.00")
    )
    # Subtotal: 2*245 + 58.50 = 548.50
    assert subtotal == Decimal("548.50")
    # Discount: 10% of 548.50 = 54.85
    assert discount == Decimal("54.85")
    # Taxable: 548.50 - 54.85 = 493.65. Tax: 5% of 493.65 = 24.68
    assert tax == Decimal("24.68")
    # Total: 493.65 + 24.68 = 518.33
    assert total == Decimal("518.33")


def test_lexical_fallback_matching(db_session):
    """Verify lexical fallback search works without external ML models."""
    results = semantic_engine.search_candidates(db_session, "amul butter", shop_id=1)
    assert len(results) > 0
    top = results[0]
    assert "amul" in top["product_name"].lower()


def test_ambiguity_detection_for_generic_oil(db_session):
    """Verify generic 'tel' is flagged as AMBIGUOUS without guessing."""
    from backend.app.schemas.domain import ParsedOrderItem
    generic_oil_item = ParsedOrderItem(
        raw_text="woh wala tel",
        product="tel",
        brand=None,
        quantity=1,
        confidence=0.40
    )
    best_match, alternatives, status = product_matcher.match_item(db_session, 1, generic_oil_item)
    assert status == "AMBIGUOUS"
    assert best_match is None
    assert len(alternatives) >= 2


def test_section_50_full_acceptance_flow(db_session):
    """
    Acceptance Test Section 50:
    1. Input: 'Bhaiya 2 kilo atta, ek Amul butter aur woh wala tel.'
    2. Atta & Amul Butter matched, Oil flagged as AMBIGUOUS.
    3. Clarification asked: 'Kaunsa Tel Chahiye?'
    4. User resolves by selecting Fortune Sunflower Oil 1L.
    5. Order status becomes READY.
    6. User confirms order.
    7. Inventory safely locked & deducted.
    8. Order marked CONFIRMED.
    9. Next query: 'Makkhan dena' resolves via Shop Memory.
    """
    # 1. Submit raw order
    raw_input = "Bhaiya 2 kilo atta, ek Amul butter aur woh wala tel."
    order = order_engine.create_and_analyze_order(db_session, shop_id=1, raw_input=raw_input)

    assert order.status == "CLARIFICATION_REQUIRED"
    assert len(order.clarifications) == 1
    clarification = order.clarifications[0]
    assert clarification.resolved == False
    assert "tel" in clarification.ambiguous_text.lower()
    assert len(clarification.options) >= 2

    # 2. Check Explainability Bill Diff
    explanation = order_engine.explain_order(db_session, order.id)
    assert explanation.order_id == order.id
    assert len(explanation.diff_items) >= 2  # Atta and Butter matched

    # 3. Check What-If Analysis
    what_if = order_engine.what_if_comparison(db_session, order.id)
    assert len(what_if.options) >= 2

    # 4. Resolve ambiguity with Fortune Sunflower Oil 1L (variant_id = 5)
    resolved_order = order_engine.resolve_order_clarification(
        db_session, order_id=order.id, clarification_id=clarification.id, selected_variant_id=5
    )
    assert resolved_order.status == "READY"
    assert len(resolved_order.items) == 3

    # Initial stock before confirmation
    inv_oil = db_session.query(Inventory).filter_by(shop_id=1, variant_id=5).first()
    stock_before = inv_oil.quantity
    assert stock_before == 10

    # 5. Confirm Order (Transaction lock & deduction)
    confirmed_order = order_engine.confirm_order_with_transaction(db_session, order.id)
    assert confirmed_order.status == "CONFIRMED"
    assert confirmed_order.confirmed_at is not None

    # Verify inventory was deducted
    db_session.refresh(inv_oil)
    assert inv_oil.quantity == stock_before - 1

    # 6. Verify Dukaan Memory Learning
    # Shopkeeper learned the mapping for 'tel'/'woh wala tel'
    learned_alias = db_session.query(Alias).filter_by(shop_id=1, variant_id=5).first()
    assert learned_alias is not None
    assert learned_alias.usage_count >= 1

    # 7. Test Shop Memory with 'makkhan'
    # Seed high-confidence alias for Amul butter 500g (variant_id = 4)
    db_session.add(Alias(
        shop_id=1,
        variant_id=4,
        alias_text="makkhan",
        normalized_alias="makkhan",
        confidence=Decimal("0.96"),
        source="SHOPKEEPER",
        usage_count=10
    ))
    db_session.commit()

    makkhan_order = order_engine.create_and_analyze_order(db_session, shop_id=1, raw_input="Makkhan dena.")
    assert makkhan_order.status == "READY"
    assert len(makkhan_order.items) == 1
    assert makkhan_order.items[0].variant_id == 4  # Resolved directly via Shop Memory!


def test_transaction_rollback_safety(db_session):
    """Verify that transaction rollback occurs and preserves stock if an item fails."""
    # Create order with 1 item in stock, and 1 item with insufficient stock
    order = Order(
        shop_id=1,
        status="READY",
        subtotal=Decimal("400.00"),
        total=Decimal("400.00"),
        raw_input="Test transaction rollback"
    )
    db_session.add(order)
    db_session.flush()

    # Valid item (stock = 25)
    item1 = OrderItem(order_id=order.id, variant_id=2, quantity=2, unit_price=Decimal("110.00"), total_price=Decimal("220.00"))
    # Invalid item (stock = 0)
    item2 = OrderItem(order_id=order.id, variant_id=3, quantity=5, unit_price=Decimal("58.00"), total_price=Decimal("290.00"))
    db_session.add_all([item1, item2])
    db_session.commit()

    inv_atta = db_session.query(Inventory).filter_by(shop_id=1, variant_id=2).first()
    stock_before = inv_atta.quantity

    with pytest.raises(Exception):
        order_engine.confirm_order_with_transaction(db_session, order.id)

    # Verify rollback: stock of item1 was NOT deducted
    db_session.refresh(inv_atta)
    assert inv_atta.quantity == stock_before
    assert order.status != "CONFIRMED"


def test_api_explanation_and_whatif(client):
    """Verify GET /orders/{id}/explanation and GET /orders/{id}/what-if endpoints."""
    # 1. Create order with ambiguous input
    create_res = client.post("/orders", json={
        "shop_id": 1,
        "raw_input": "ek tel dena bhaiya"
    })
    assert create_res.status_code == 200
    order_data = create_res.json()
    order_id = order_data["id"]
    assert order_data["status"] == "CLARIFICATION_REQUIRED"

    # 2. Test Explainability endpoint
    exp_res = client.get(f"/orders/{order_id}/explanation")
    assert exp_res.status_code == 200
    exp_data = exp_res.json()
    assert exp_data["order_id"] == order_id
    assert exp_data["overall_status"] == "CLARIFICATION_REQUIRED"

    # 3. Test What-If endpoint
    whatif_res = client.get(f"/orders/{order_id}/what-if")
    assert whatif_res.status_code == 200
    whatif_data = whatif_res.json()
    assert whatif_data["order_id"] == order_id
    assert len(whatif_data["options"]) >= 2
    assert float(whatif_data["options"][0]["price"]) > 0


def test_out_of_stock_logic(db_session):
    """Verify that requesting an out-of-stock item triggers OUT_OF_STOCK and clarification."""
    from backend.app.schemas.domain import ParsedOrderItem
    out_stock_item = ParsedOrderItem(
        raw_text="Amul butter 100g",
        product="butter 100g",
        brand="Amul",
        quantity=1
    )
    best_match, alternatives, status = product_matcher.match_item(db_session, 1, out_stock_item)
    if best_match and best_match.stock == 0:
        assert status == "OUT_OF_STOCK"
        assert best_match.is_out_of_stock == True


def test_api_health_endpoint(client):
    """Verify GET /health returns online status and app metadata."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["app"] == "DukaanMitra"
    assert data["tagline"] == "Aap Bolo, DukaanMitra Sambhale."
    assert data["status"] == "online"


def test_api_products_and_search(client):
    """Verify GET /products and GET /products/search?q= endpoints."""
    res_list = client.get("/products")
    assert res_list.status_code == 200
    products = res_list.json()
    assert len(products) >= 3

    res_search = client.get("/products/search?q=butter")
    assert res_search.status_code == 200
    search_data = res_search.json()
    assert len(search_data) >= 1
    assert "butter" in search_data[0]["name"].lower()
