# 🛒 DUKAANMITRA (दुकानमित्र)
> **Tagline:** *"Aap Bolo, DukaanMitra Sambhale."*  
> **Production-Grade Hackathon Prototype: AI-Powered Hinglish Order Desk & Transaction-Safe Order Engine for Indian Kirana Shopkeepers.**

---

## 🌟 1. Project Concept & Core Principle

DukaanMitra is an intelligent, voice-and-text order processing desk built for local Indian shopkeepers. Customers frequently order in conversational, colloquial Hinglish:
> *"Bhaiya 2 kilo atta, ek Amul butter aur woh wala tel."*

### Core Architectural Principle: **"AI Knows When NOT to Guess."**
A common failure of typical LLM apps is blindly guessing products or prices (e.g., picking any random brand or size of oil). DukaanMitra strictly separates AI understanding from database business logic:
- **AI / NLP**: Extracts structured entities (product, brand, quantity, unit, confidence).
- **Order Engine & Database**: Performs hybrid product matching, inventory verification, and ambiguity detection.
- **Clarification Minimizer**: When ambiguous items are detected (e.g. *"woh wala tel"* with multiple variants), the system generates concise, structured clarification options without guessing.
- **Explainability (Bill Diff)**: Shopkeepers can audit *"Customer Said"* vs *"AI Understood"* vs *"Catalog Match"* with price and stock levels.
- **Transaction Safety**: Financial totals are computed server-side with precise `Decimal` arithmetic. Confirmations use PostgreSQL row locks (`SELECT ... FOR UPDATE`) to guarantee atomicity and prevent overselling.

```
Customer Speech / Hinglish Text
               ↓
    Entity Extraction (AI Service)
               ↓
   Structured Order Items (JSON)
               ↓
 Hybrid Matching & Shop Memory (Aliases)
               ↓
    Ambiguity Detection & Minimizer
               ↓
   Clarification (If Ambiguous) / Ready
               ↓
  PostgreSQL ACID Transaction & Stock Deduction
               ↓
        Final Verified Bill
```

---

## ⚙️ 2. Tech Stack

- **Backend Framework:** FastAPI (High performance, async-ready)
- **Validation & Schemas:** Pydantic V2 & Pydantic-Settings
- **ORM & Database:** SQLAlchemy 2.x & PostgreSQL (direct on localhost)
- **Database Migrations:** Alembic
- **Driver:** psycopg2-binary
- **Semantic Search:** PostgreSQL pgvector extension + HuggingFace `sentence-transformers` (Multilingual MiniLM)
- **Lexical Matching:** RapidFuzz (Token set & partial ratio matching for Hinglish nicknames)
- **Testing:** Pytest & FastAPI TestClient

---

## 🔍 3. Environment Inspection & Status

DukaanMitra was inspected and configured directly on this Windows system:

| Component | Status | Details |
| :--- | :--- | :--- |
| **Python** | ✅ Installed | Python 3.14.7, pip 26.2.1 |
| **PostgreSQL** | ✅ Running | PostgreSQL 18.6 on `localhost:5432` (Service `postgresql-x64-18`) |
| **Git** | ✅ Available | Git 2.55.0.windows.5 |
| **Public Datasets** | ✅ Ready | `bigbasket_products.csv` (22.4 MB) & `DMart.csv` (4.08 MB) |
| **Dependencies** | ✅ Installed | FastAPI, SQLAlchemy 2.x, Alembic, RapidFuzz, SentenceTransformers, Pytest |
| **pgvector** | ⚠️ Fallback Ready | Checked extension directory in PG 18. Hybrid fallback active. |
| **Automated Tests** | ✅ Passing | 11/11 tests pass in `backend/tests/test_dukaanmitra.py` |

---

## 📊 4. Data Provenance: Real vs. Synthetic Separation

To maintain strict data integrity, DukaanMitra separates catalog data from store operations:

### A. Real / Public Data (Catalog Foundation)
- **BigBasket Products Dataset (`data/raw/bigbasket/bigbasket_products.csv`)**: Real-world FMCG product names, standardized brands, multi-tier categories, descriptions, pack sizes, market price, barcodes (EAN).
- **DMart Products Dataset (`data/raw/dmart/DMart.csv`)**: Indian supermarket pack sizes (100g, 500g, 1kg, 1L, 5L), MRP, discounted selling prices, and breadcrumbs.
- **Supermart Grocery Sales (`data/raw/supermart/`)**: Public retail basket and order trends.

### B. Synthetic / Demo Data (Store Operations Layer)
- **Shops**: 5 synthetic demo stores across Maharashtra (Patil General Store, Sharma Kirana, More Provision Store, Sai Daily Needs, City Mart).
- **Shopkeepers**: Fictional demo shopkeepers (Ramesh Patil, Sunil Sharma, etc.).
- **Inventory**: Shop-specific stock allocations (fast-moving, slow-moving, low-stock, and out-of-stock items).
- **Shop Memory (Aliases)**: Shopkeeper-specific Hinglish idioms (`"makkhan" -> Amul Butter 500g`, `"laal packet atta" -> Aashirvaad 5kg`).
- **Demo Orders**: 500+ historical orders preserving unit prices at time of purchase.

---

## 🚀 5. Quick Start Guide (Windows PowerShell)

### Step 1: Environment & Virtualenv
```powershell
# Open Windows PowerShell in C:\DukanMitra
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables
Copy `.env.example` to `.env` and insert your PostgreSQL password:
```ini
DATABASE_URL=postgresql://postgres:<YOUR_PASSWORD>@localhost:5432/dukaanmitra
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=dukaanmitra
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<YOUR_PASSWORD>
APP_ENV=development
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=True
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

### Step 3: Initialize Database & Run Migrations
```powershell
# 1. Create database 'dukaanmitra' and check extensions
python scripts/setup_database.py

# 2. Run Alembic migration to create all 13 normalized tables
alembic upgrade head

# 3. Ingest public catalogs (DMart & BigBasket)
python scripts/ingest_dmart.py
python scripts/ingest_bigbasket.py

# 4. Generate synthetic shops, inventory, aliases, and 500+ orders
python scripts/generate_demo_data.py

# 5. Generate vector embeddings for semantic search
python scripts/generate_embeddings.py
```

### Step 4: Run Automated Tests
```powershell
python -m pytest backend/tests/test_dukaanmitra.py -v
```

### Step 5: Start FastAPI Server
```powershell
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```
Or double-click `run_server.bat` in the project root!
Interactive Swagger API documentation: **http://localhost:8000/docs**

---

## 📡 6. Core API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | System health, database connection, semantic engine state |
| `GET` | `/shops` | List active shops |
| `GET` | `/products/search?q=` | Search products by name, brand, or category |
| `POST` | `/orders` | Submit raw conversational order (Hinglish/English) |
| `POST` | `/orders/{id}/clarify` | Resolve ambiguous item with selected variant |
| `POST` | `/orders/{id}/confirm` | Atomically lock inventory & finalize order (PostgreSQL transaction) |
| `GET` | `/orders/{id}/explanation` | **Bill Diff**: Customer said vs AI understood vs Catalog match |
| `GET` | `/orders/{id}/what-if` | **What-If Analysis**: Compare prices of ambiguous variants |
| `GET` | `/aliases` | Inspect Dukaan Memory (shopkeeper custom mappings) |
| `POST` | `/semantic-search` | Multilingual semantic search endpoint |

---

## 🎯 7. The Acceptance Scenario (Section 50)

### 1. Customer Order
```http
POST /orders
Content-Type: application/json

{
  "shop_id": 1,
  "raw_input": "Bhaiya 2 kilo atta, ek Amul butter aur woh wala tel."
}
```
**Response:**
- Atta → Matched: Aashirvaad Shudh Chakki Atta (2 kg), Price: ₹110.00
- Amul Butter → Matched: Amul Butter (500 g), Price: ₹285.00
- Tel → Flagged as `AMBIGUOUS`. Clarification generated:
  - *"Kaunsa Tel Chahiye? 1. Fortune Sunflower Oil 1L, 2. Fortune Sunflower Oil 5L"*
- Order Status: `CLARIFICATION_REQUIRED`

### 2. Shopkeeper Resolves Ambiguity
```http
POST /orders/1/clarify
Content-Type: application/json

{
  "clarification_id": 1,
  "selected_variant_id": 5
}
```
**System Actions:**
- Resolves clarification with Fortune Sunflower Oil 1L.
- Stores mapping in **Dukaan Memory** (`aliases` table) with increased confidence.
- Order Status updates to `READY`. Total recomputed to: ₹540.00.

### 3. Order Confirmation & Stock Locking
```http
POST /orders/1/confirm
```
**Transaction Execution:**
- Row-level lock (`SELECT ... FOR UPDATE`) on Atta, Butter, and Oil inventory.
- Stock validation: Available stock checked.
- Atomic stock deduction: Atta (25 → 24), Butter (15 → 14), Oil (10 → 9).
- Order status marked `CONFIRMED`. AI audit decision committed.

### 4. Shop Memory Recall
```http
POST /orders
{
  "shop_id": 1,
  "raw_input": "Makkhan dena."
}
```
**System Actions:**
- Direct resolution to **Amul Butter 500g** via Shop Memory alias (`confidence: 0.96`), bypassing ambiguity!

---

## 🔒 8. Security & Financial Integrity

1. **No Direct LLM SQL Generation**: The AI engine only outputs structured JSON entities. SQL queries are parameterized via SQLAlchemy.
2. **Backend Financial Calculation**: Currency arithmetic uses `Decimal` with `ROUND_HALF_UP` precision. Frontend totals are never trusted.
3. **Point-in-Time Historical Billing**: Order items store `unit_price` at the instant of purchase. Future price changes never alter historical records.
4. **Row-Level Concurrency Control**: Prevents overselling during concurrent customer orders via PostgreSQL row locking.
