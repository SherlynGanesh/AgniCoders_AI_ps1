# DukaanMitra Dataset Catalog & Provenance

## Data Provenance & Real vs Synthetic Separation

### Real / Public Datasets (Product & Catalog Foundation)
1. **BigBasket Product Dataset (`data/raw/bigbasket/bigbasket_products.csv`)**
   - **Source**: Kaggle Public Dataset (BigBasket Products)
   - **Usage**: Product catalog, standardized brand names, multi-level category taxonomy, descriptions, pack sizes, market price, barcodes (EAN).
   - **Provenance Attribution**: Publicly listed e-commerce catalog data in India. Not private inventory of any shopkeeper.
   - **License**: Public retail catalog data used for educational/hackathon demonstration.

2. **DMart Product Dataset (`data/raw/dmart/DMart.csv`)**
   - **Source**: Kaggle Public Dataset (DMart Products)
   - **Usage**: Indian supermarket pack sizes, MRP, discounted pricing, variants (100g, 500g, 1kg, 1L, 5L), and breadcrumbs.
   - **Provenance Attribution**: Public grocery retail listings. Not private individual store inventory.

3. **Supermart Grocery Sales Dataset (`data/raw/supermart/`)**
   - **Source**: Public Kaggle Retail Order/Sales Patterns
   - **Usage**: Reference for realistic order item combinations, seasonal demand, and realistic order sizes.

---

### Synthetic / Demo Data (Store Operations Layer)
- **Shops**: 5 realistic synthetic grocery shops across Indian cities (Pune, Mumbai, Thane, Nashik, Nagpur).
- **Shopkeepers**: Fictional shopkeeper identities (e.g., Patil General Store, Sharma Kirana).
- **Inventory**: Shop-specific stock allocations (fast-moving vs slow-moving stock, low stock, out-of-stock items).
- **Shop Memory / Aliases**: Shopkeeper-specific Hinglish nicknames (e.g., "makkhan" -> Amul Butter 500g, "laal packet atta" -> Aashirvaad Shudh Chakki Atta 5kg).
- **Customers**: Synthetic fictional customers.
- **Orders & Audit Logs**: Demo historical and active orders.

---

### System Generated Layer
- AI Hinglish parsing output & confidence scores
- Ambiguity decisions & clarification prompts
- Hybrid match scores (Lexical + Semantic + Shop Memory)
- Order explainability diffs
