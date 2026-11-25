# FOODFLOW ERP
### Order-to-Audit Management System for Small Food Manufacturers
**Organization:** Centre for Digital Infrastructure, National Institute of Technology Tiruchirappalli  
**Project Type:** Individual Internship Technical Assessment  

---

## 1. Executive Summary

**FoodFlow ERP** is an end-to-end, commercial-grade web ERP application specifically engineered for small-scale Indian food manufacturing businesses (such as manufacturers producing traditional packaged South Indian snacks like Murukku, Mixture, Banana Chips, and Sweets).

The system seamlessly integrates the complete business cycle into a single automated, persistent workflow:

```
PURCHASE (Raw Materials & Packaging)
   ↓
RAW MATERIAL & PACKAGING INVENTORY (Moving Weighted-Average Valuation)
   ↓
RECIPE / BILL OF MATERIALS (BOM) & BATCH SCALING
   ↓
PRODUCTION EXECUTION (Actual Consumption, Scrap & Yield Variance Alerts)
   ↓
FINISHED GOODS INVENTORY (Auto-populated from Production Output)
   ↓
SALESMAN ORDER BOOKING (Mobile-Optimized, Live GST Calculation, Shortage Checks)
   ↓
ADMIN REVIEW & APPROVAL (Stock Shortage Warning, Item-Level Amendments)
   ↓
GST TAX INVOICE (Intra-State CGST/SGST vs Inter-State IGST, FY Sequence FF/24-25/xxxx)
   ↓
DISPATCH MANAGEMENT (Partial/Full Shipments, Finished Goods Deduction)
   ↓
PAYMENT COLLECTION & RECONCILIATION (FIFO Invoice Allocation, Customer Ageing)
   ↓
MONTHLY AUDIT & COMPLIANCE REPORTS (17 Standard Reports, PDF & Excel Exports)
```

By enforcing strict database transactions, append-only immutable stock ledgers, moving weighted-average valuation, and granular role-based permissions, FoodFlow ERP completely eliminates duplicate data entry, manual stock calculations, batch wastage disputes, and month-end accounting reconciliation bottlenecks.

---

## 2. Technology Stack

- **Backend Framework:** Python 3.13, Flask 3.0+
- **Database & ORM:** PostgreSQL 16, Flask-SQLAlchemy, SQLAlchemy 2.0 (with `psycopg2-binary`)
- **Database Migrations:** Alembic via Flask-Migrate
- **Authentication & Security:** Flask-Login, Werkzeug Secure Password Hashing (PBKDF2-SHA256), Flask-WTF CSRF protection
- **Precision Arithmetic:** Python standard library `decimal.Decimal` throughout all monetary, tax, costing, and inventory quantities (zero floating-point inaccuracies)
- **Document & Export Generation:**
  - **PDF:** ReportLab (Clean, GST-compliant A4 Tax Invoices)
  - **Excel:** OpenPyXL (Multi-column formatted `.xlsx` workbooks with styled headers)
  - **CSV:** Python built-in `csv` streaming
- **Frontend & UI/UX:**
  - Responsive HTML5 & CSS3 with custom corporate palette (`#2563EB` Primary, `#1E293B` Text, `#F8FAFC` Background)
  - Bootstrap 5.3 (modern layout, responsive data tables, accessible modal dialogs)
  - Jinja2 Template Engine (custom Indian Rupee `inr`, Date `date_in`, and Quantity `qty` formatters)
  - Lucide Icons (clean, modern iconography)
  - Chart.js (used purposefully for 6-month sales trends and top-product distributions)
- **Configuration & Testing:** `python-dotenv`, `pytest`, `docker-compose`

---

## 3. Indian Business Compliance & Localization

Designed from the ground up for Indian manufacturing operations:

- **Currency & Formatting:** Indian Rupee (`₹`) with standard Indian digit grouping (`₹1,25,000.00`) across all user interfaces, PDFs, and spreadsheets.
- **Date Format:** Standard Indian `DD-MM-YYYY` across all tables, forms, and audit timestamps.
- **GST Compliance:**
  - **Place of Supply Logic:** Automatically compares the Supplier Factory State (**Tamil Nadu**) with the Customer's State.
  - **Intra-State Transactions (e.g., Tamil Nadu to Tamil Nadu):** Splits GST evenly into **CGST** and **SGST** (e.g., 5% total tax = 2.50% CGST + 2.50% SGST).
  - **Inter-State Transactions (e.g., Tamil Nadu to Karnataka):** Applies full GST as **IGST** (e.g., 5% total tax = 5.00% IGST).
  - **HSN / SAC Codes:** Recorded at item level for regulatory outward supply reporting.
  - **Invoice Numbering:** Sequential, reset per Indian Financial Year (`FF/24-25/0001`, `FF/24-25/0002`).
  - **Credit Notes:** Supported for damaged goods, price disputes, or returns with sequential numbering (`CN/24-25/0001`).
- **Standard Units of Measure:** `kg`, `grams`, `litres`, `ml`, `pieces`, `packets`, and `cartons` with fractional support up to 3 decimal places.

---

## 4. Role-Based Access Control (RBAC)

FoodFlow ERP enforces strict backend authorization decorators (`@roles_required`) on all administrative, operational, and financial endpoints.

| Role | Target Persona | Accessible Capabilities |
|---|---|---|
| **Owner** | Factory Proprietor / Managing Director | Full system access: executive dashboard, all master data, approvals, financial audit reports, settings. |
| **Admin** | Factory General Manager / Operations Lead | Purchase posting, recipe BOM configuration, order review/approval, invoicing, dispatch, payments, stock adjustments. |
| **Production** | Factory Floor Supervisor | Production execution, recipe loading, actual vs planned consumption entry, scrap recording, run reversals. |
| **Salesman** | Field Sales Representatives | Mobile-first sales order entry, customer catalog lookup, customer order history, shortage visibility. Restricted from back-office settings and invoices. |
| **Auditor** | Internal/External Chartered Accountant | Read-only access to GST registers, stock ledgers, financial summaries, production costings, audit logs, and export downloads. |

### Demo Accounts (Password for all: `Admin@123`)

- **Owner:** `owner@foodflow.local`
- **Admin:** `admin@foodflow.local`
- **Production Manager:** `production@foodflow.local`
- **Salesman A:** `salesman.a@foodflow.local`
- **Salesman B:** `salesman.b@foodflow.local`
- **Auditor:** `auditor@foodflow.local`

*(Quick-fill demo buttons are provided on the login screen for rapid role switching).*

---

## 5. Inventory & Production Costing Methodology

### 1. Append-Only Stock Ledger
Stock balances are never overwritten in place. Every transaction creates an immutable row in the `stock_ledger` table with `direction` (`IN` or `OUT`), `quantity`, `unit_rate`, and source document linkages (`Purchase`, `ProductionRun`, `SalesOrder`, `StockAdjustment`). Current stock is computed dynamically:
$$\text{Closing Stock} = \text{Opening Stock} + \sum \text{Stock IN} - \sum \text{Stock OUT}$$

### 2. Moving Weighted-Average Costing (WAC)
When new raw materials are purchased, the material's inventory valuation rate is atomically updated using the moving weighted-average formula:
$$\text{New Average Rate} = \frac{(\text{Current Stock} \times \text{Current Rate}) + (\text{Incoming Qty} \times \text{Purchase Rate})}{\text{Current Stock} + \text{Incoming Qty}}$$

### 3. Production Batch Costing & Scrap Accounting
For every production run:
- **Raw Material Cost:** Actual raw materials consumed multiplied by their weighted-average inventory valuation rate.
- **Packaging Scrap Allocation:** Both good pouches used and damaged pouches wasted on the machine are deducted from packaging inventory and charged to batch material cost.
- **Factory Overheads:** Allocated labor, fuel/gas, electricity, and indirect overheads are included in total batch cost.
- **Unit Cost per Packet:**
$$\text{Cost Per Packet} = \frac{\text{Total Material Cost} + \text{Total Packaging Cost} + \text{Overhead Costs}}{\text{Actual Good Output (Packets)}}$$

### 4. Production Variance & Tolerance Alerts
The system automatically tracks consumption and yield variance:
$$\text{Yield Variance \%} = \frac{\text{Actual Output} - \text{Expected Output}}{\text{Expected Output}} \times 100$$
$$\text{Consumption Variance \%} = \frac{\text{Actual Consumed} - \text{Planned Consumed}}{\text{Planned Consumed}} \times 100$$
If any variance exceeds the configured tolerance threshold (default $\pm 3.00\%$), an alert badge is highlighted and flagged on the Executive Dashboard.

---

## 6. Verification Against Benchmark Dataset (Sections 22 & 23)

The application has been verified against the exact benchmark production scenario:

| Metric | Expected Value | FoodFlow Result | Status |
|---|---|---|---|
| **Flour Closing Stock** | $100 + 60 - 40 = 120.000\text{ kg}$ | $120.000\text{ kg}$ | Verified |
| **Oil Closing Stock** | $30 - 10.5 = 19.500\text{ L}$ | $19.500\text{ L}$ | Verified |
| **Spice Mix Closing Stock** | $5 - 1.2 = 3.800\text{ kg}$ | $3.800\text{ kg}$ | Verified |
| **Pouches Closing Stock** | $500 - 188 - 6 = 306.000\text{ pcs}$ | $306.000\text{ pcs}$ | Verified |
| **Cartons Closing Stock** | $30 - 9 = 21.000\text{ pcs}$ | $21.000\text{ pcs}$ | Verified |
| **Finished Goods Stock** | $50 + 188 - 150 = 88.000\text{ pkts}$ | $88.000\text{ pkts}$ | Verified |
| **Yield Variance %** | $(188 - 200)/200 \times 100 = -6.00\%$ | $-6.00\%$ (Alert Triggered) | Verified |
| **Oil Consumption Variance %** | $(10.5 - 10.0)/10.0 \times 100 = +5.00\%$ | $+5.00\%$ (Alert Triggered) | Verified |
| **Invoice A Taxable Amount** | $150 \times ₹50.00 = ₹7,500.00$ | $₹7,500.00$ | Verified |
| **Invoice A CGST + SGST** | $₹187.50 + ₹187.50$ (5% total) | $₹187.50 + ₹187.50$ | Verified |
| **Invoice A Grand Total** | $₹7,875.00$ | $₹7,875.00$ | Verified |
| **Retailer A Outstanding** | $₹7,875.00 - ₹4,000.00 = ₹3,875.00$ | $₹3,875.00$ | Verified |
| **Distributor B Shortage** | Requested 120, Available 88, Shortage 32 | Shortage: 32 pkts flagged | Verified |
| **Total Production Cost** | $₹3,195.00 + ₹660.00 + ₹2,000.00 = ₹5,855.00$ | $₹5,855.00$ | Verified |
| **Cost Per Packet** | $₹5,855.00 / 188 = ₹31.1436$ | $₹31.1436$ (~₹31.14) | Verified |

---

## 7. Local Setup & Execution Guide (Windows)

### Prerequisites
- Python 3.10+ (Python 3.13 tested)
- PostgreSQL 14+ running locally on port `5432`
- Git

### Step 1: Clone and Set Up Virtual Environment
```powershell
cd C:\Users\KiTE\Desktop\FoodFlow
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Step 2: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables
Create a `.env` file in the root directory (or use `.env.example`):
```ini
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=foodflow-secret-production-key-2024
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/foodflow_db
TEST_DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/foodflow_test_db
```

### Step 4: Initialize Database & Seed Benchmark Data
```powershell
# Run database migrations
flask db upgrade

# Populate master data, demo users, and verified benchmark scenario
python scripts/seed_benchmark.py
```

### Step 5: Start the Web Application
```powershell
python run.py
```
Open your browser and navigate to: `http://127.0.0.1:5000`

---

## 8. Automated Test Suite

The test suite covers inventory atomicity, duplicate prevention, negative stock protection, production batch costing, yield variances, GST calculations, FIFO payment allocations, dispatch deduction, and PDF/Excel generation.

Run all tests via `pytest`:
```powershell
pytest -v
```

All 15 automated test cases execute against the isolated PostgreSQL test database (`foodflow_test_db`).

---

## 9. Comprehensive Reports (Section 17)

FoodFlow ERP provides 17 standard regulatory, accounting, and operational reports with date filters, live browser view, CSV export, and OpenPyXL Excel (`.xlsx`) downloads:

1. **Sales Register:** Chronological tax invoices with taxable, CGST, SGST, IGST, and total.
2. **Customer-Wise Sales Summary:** Aggregate turnover and tax by customer.
3. **Product-Wise Sales Summary:** Packets sold and revenue generated per SKU.
4. **GST Outward Supplies Summary:** Ready reconciliation for GSTR-1 & GSTR-3B.
5. **Purchase Register:** Supplier invoices, received quantities, and input GST.
6. **Raw Material Stock Summary:** Opening, inward, consumed, closing, and valuation.
7. **Packaging Material Stock Summary:** Pouch and carton closing balances and scrap.
8. **Finished Goods Stock Summary:** Good output, dispatched units, closing packets.
9. **Daily Stock Movement Ledger:** Complete debit/credit audit trail of every stock item.
10. **Reorder Level Alert Report:** Items at or below minimum threshold.
11. **Production Register:** Batch runs, planned vs actual outputs, total cost.
12. **Material Consumption Summary:** Standard BOM vs actual consumption.
13. **Production Variance Report:** Yield and consumption variances with alert flags.
14. **Customer Outstanding Balances:** Total receivables per customer.
15. **Payment Collection Register:** Cash/NEFT/UPI/Cheque collections log.
16. **Salesman-Wise Booking Report:** Order volume and value by field representative.
17. **Credit Note Register:** Issued credit notes with original invoice links.

---

## 10. Known Limitations & Roadmap

- **E-Way Bill Direct API:** E-Way Bill numbers can currently be recorded on dispatches; direct NIC API integration via GSP can be added in Phase 2.
- **Barcode / QR Scanning:** Batch QR code scanning on mobile devices for dispatch verification is architected and ready for mobile camera wrapper integration.
- **Multi-Branch Warehouses:** Currently architected for single-factory multi-godown setup; multi-state manufacturing locations can be enabled via tenant branch IDs.
