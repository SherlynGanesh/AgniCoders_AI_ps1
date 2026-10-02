from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from decimal import Decimal

from backend.app.database.session import get_db
from backend.app.models.entities import (
    Shop, Product, ProductVariant, Inventory, Order, OrderItem,
    Alias, Clarification, AIDecision
)
from backend.app.schemas.domain import (
    ShopResponse, ProductResponse, ProductVariantResponse, InventoryResponse,
    OrderCreateRequest, OrderResponse, ClarificationResolveRequest,
    OrderExplanationResponse, WhatIfResponse, AliasCreateRequest, AliasResponse,
    SemanticSearchRequest, SemanticSearchItem
)
from backend.app.services.order_engine import order_engine
from backend.app.services.semantic_search import semantic_engine
from backend.data_ingestion.normalization import normalize_text

router = APIRouter()


# ================= Health Check =================
@router.get("/health", tags=["System"])
def health_check(db: Session = Depends(get_db)):
    try:
        # Verify DB connection
        db.execute(func.now()).scalar()
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "online",
        "app": "DukaanMitra",
        "tagline": "Aap Bolo, DukaanMitra Sambhale.",
        "database": db_status,
        "semantic_engine_ready": semantic_engine.is_vector_available
    }


# ================= Shops =================
@router.get("/shops", response_model=List[ShopResponse], tags=["Shops"])
def list_shops(db: Session = Depends(get_db)):
    return db.query(Shop).filter(Shop.active == True).all()


@router.get("/shops/{shop_id}", response_model=ShopResponse, tags=["Shops"])
def get_shop(shop_id: int, db: Session = Depends(get_db)):
    shop = db.query(Shop).filter(Shop.id == shop_id).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
    return shop


# ================= Products =================
@router.get("/products", response_model=List[ProductResponse], tags=["Products"])
def list_products(
    limit: int = 50,
    offset: int = 0,
    category_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Product).filter(Product.active == True)
    if category_id:
        query = query.filter(Product.category_id == category_id)
    return query.offset(offset).limit(limit).all()


@router.get("/products/search", response_model=List[ProductResponse], tags=["Products"])
def search_products(q: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    norm_q = f"%{normalize_text(q)}%"
    return db.query(Product).filter(
        (Product.normalized_name.ilike(norm_q)) |
        (Product.normalized_brand.ilike(norm_q))
    ).limit(20).all()


@router.get("/products/{product_id}", response_model=ProductResponse, tags=["Products"])
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


# ================= Inventory =================
@router.get("/inventory", response_model=List[InventoryResponse], tags=["Inventory"])
def list_inventory(
    shop_id: Optional[int] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    query = db.query(Inventory)
    if shop_id:
        query = query.filter(Inventory.shop_id == shop_id)
    return query.limit(limit).all()


@router.get("/inventory/{variant_id}", response_model=List[InventoryResponse], tags=["Inventory"])
def get_variant_inventory(variant_id: int, db: Session = Depends(get_db)):
    return db.query(Inventory).filter(Inventory.variant_id == variant_id).all()


# ================= Orders =================
@router.post("/orders", response_model=OrderResponse, tags=["Orders"])
def create_order(req: OrderCreateRequest, db: Session = Depends(get_db)):
    """
    Submits a conversational raw order (Hinglish/English).
    Triggers AI parsing, hybrid catalog matching, ambiguity detection.
    """
    return order_engine.create_and_analyze_order(
        db, shop_id=req.shop_id, raw_input=req.raw_input, customer_id=req.customer_id
    )


@router.get("/orders", response_model=List[OrderResponse], tags=["Orders"])
def list_orders(
    shop_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    query = db.query(Order)
    if shop_id:
        query = query.filter(Order.shop_id == shop_id)
    if status_filter:
        query = query.filter(Order.status == status_filter)
    return query.order_by(Order.created_at.desc()).limit(limit).all()


@router.get("/orders/{order_id}", response_model=OrderResponse, tags=["Orders"])
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.post("/orders/{order_id}/clarify", response_model=OrderResponse, tags=["Orders"])
def clarify_order(
    order_id: int,
    req: ClarificationResolveRequest,
    db: Session = Depends(get_db)
):
    """
    Resolves an ambiguity question with the user/shopkeeper's chosen variant.
    Updates order and records shop memory.
    """
    return order_engine.resolve_order_clarification(
        db, order_id=order_id, clarification_id=req.clarification_id,
        selected_variant_id=req.selected_variant_id
    )


@router.post("/orders/{order_id}/confirm", response_model=OrderResponse, tags=["Orders"])
def confirm_order(order_id: int, db: Session = Depends(get_db)):
    """
    Finalizes the order within a transactional lock. Deducts inventory.
    """
    return order_engine.confirm_order_with_transaction(db, order_id)


@router.post("/orders/{order_id}/cancel", response_model=OrderResponse, tags=["Orders"])
def cancel_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status == "CONFIRMED":
        raise HTTPException(status_code=400, detail="Cannot cancel confirmed order directly")
    order.status = "CANCELLED"
    db.commit()
    db.refresh(order)
    return order


@router.get("/orders/{order_id}/explanation", response_model=OrderExplanationResponse, tags=["Orders"])
def explain_order(order_id: int, db: Session = Depends(get_db)):
    """
    Returns explainable Bill Diff:
    Customer Said vs AI Understood vs Catalog Match vs Stock vs Price.
    """
    return order_engine.explain_order(db, order_id)


@router.get("/orders/{order_id}/what-if", response_model=WhatIfResponse, tags=["Orders"])
def what_if_analysis(order_id: int, db: Session = Depends(get_db)):
    """
    Compares ambiguous variants and total price differentials.
    """
    return order_engine.what_if_comparison(db, order_id)


# ================= Aliases / Shop Memory =================
@router.get("/aliases", response_model=List[AliasResponse], tags=["Shop Memory"])
def list_aliases(shop_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Alias)
    if shop_id:
        query = query.filter(Alias.shop_id == shop_id)
    return query.order_by(Alias.usage_count.desc()).all()


@router.post("/aliases", response_model=AliasResponse, tags=["Shop Memory"])
def create_alias(req: AliasCreateRequest, db: Session = Depends(get_db)):
    norm_alias = normalize_text(req.alias_text)
    existing = db.query(Alias).filter_by(
        shop_id=req.shop_id, normalized_alias=norm_alias, variant_id=req.variant_id
    ).first()

    if existing:
        existing.confidence = Decimal(str(req.confidence))
        existing.usage_count += 1
        db.commit()
        db.refresh(existing)
        return existing

    alias = Alias(
        shop_id=req.shop_id,
        variant_id=req.variant_id,
        alias_text=req.alias_text,
        normalized_alias=norm_alias,
        confidence=Decimal(str(req.confidence)),
        source=req.source,
        usage_count=1
    )
    db.add(alias)
    db.commit()
    db.refresh(alias)
    return alias


# ================= Semantic Search =================
@router.post("/semantic-search", response_model=List[SemanticSearchItem], tags=["Search"])
def semantic_search(req: SemanticSearchRequest, db: Session = Depends(get_db)):
    candidates = semantic_engine.search_candidates(
        db, query=req.query, shop_id=req.shop_id, limit=req.top_k
    )
    results = []
    for c in candidates:
        results.append(SemanticSearchItem(
            variant_id=c["variant_id"],
            product_name=c["product_name"],
            brand=c["brand"],
            variant_label=c["variant_label"],
            price=c["price"],
            stock=c["stock"],
            score=c["match_score"],
            search_type=c["match_type"]
        ))
    return results


# ================= Analytics =================
@router.get("/analytics/summary", tags=["Analytics"])
def analytics_summary(db: Session = Depends(get_db)):
    total_orders = db.query(func.count(Order.id)).scalar() or 0
    confirmed_orders = db.query(func.count(Order.id)).filter(Order.status == "CONFIRMED").scalar() or 0
    total_sales = db.query(func.sum(Order.total)).filter(Order.status == "CONFIRMED").scalar() or Decimal("0.00")
    total_products = db.query(func.count(Product.id)).scalar() or 0
    total_variants = db.query(func.count(ProductVariant.id)).scalar() or 0
    total_aliases = db.query(func.count(Alias.id)).scalar() or 0

    return {
        "total_orders": total_orders,
        "confirmed_orders": confirmed_orders,
        "total_sales": float(total_sales),
        "total_products": total_products,
        "total_variants": total_variants,
        "shop_memory_aliases": total_aliases
    }
