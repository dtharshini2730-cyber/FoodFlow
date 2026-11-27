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
  - Chart.js (Monthly Sales vs Production Costs and Top Debtors Outstanding Distribution)
- **Configuration & Testing:** `python-dotenv`, `pytest`, `docker-compose`

---

## 3. Role-Based Workspaces & Navigation

FoodFlow ERP provides 5 distinct, role-tailored workspaces. Each role is greeted with a dedicated dashboard, custom sidebar navigation, permitted actions, and strict backend permission enforcement (`HTTP 403 Forbidden` on unauthorized requests).

```
+-----------------------------------------------------------------------------------------+
|                                    FOODFLOW ERP                                         |
+-----------------------------------------------------------------------------------------+
| [Role: OWNER]      | Business Overview, Sales vs Production, Dues Doughnut, Alerts      |
| [Role: ADMIN]      | Daily Operations, Order Review, Invoicing, Dispatch, User Admin    |
| [Role: SALESMAN]   | Field Orders, Live FG Catalog, Customer Limits, Mobile Tab Bar     |
| [Role: PRODUCTION] | Batch Runs, BOM Execution, Material Readiness, Yield Variances     |
| [Role: AUDITOR]    | GSTR-1 Reconciliation, Customer Ageing, Statutory Registers Export|
+-----------------------------------------------------------------------------------------+
```

### A. Owner Workspace (`owner@foodflow.local`)
- **Focus:** High-level enterprise performance, capital allocation, and business health.
- **KPI Cards (8):** Total Sales (`₹`), Total Orders, Pending Orders, Finished Goods Stock, Raw Material Alerts, Total Outstanding Receivables, Avg Yield Variance (`%`), Total Production Cost.
- **Visualizations:**
  - Dual-bar Chart.js chart comparing Monthly Sales Revenue vs Monthly Production Cost.
  - Doughnut Chart.js chart displaying Top 5 Debtors Outstanding Distribution.
- **Navigation:** Dashboard, Business Overview, Sales Summary, Production Summary, Inventory Overview, Financial Reports, Audit Overview, Profile.

### B. Admin Operations Hub (`admin@foodflow.local`)
- **Focus:** Day-to-day factory fulfillment, procurement, order processing, and staff administration.
- **KPI Cards (6):** New Orders Today, Orders Awaiting Approval, Orders Ready for Dispatch, Today's Sales, Pending Payments, Low Stock Items.
- **Quick Shortcuts:** Post Purchase, Approve Orders, Generate Invoice, Dispatch Goods, Record Payment, User Management.
- **User Management (`/master/users`):** View staff list, register new users with specific roles, and toggle account activation status.
- **Navigation:** Dashboard, Sales Orders, Customers, Invoices, Dispatch, Payments, Purchases, Suppliers, Inventory, Products, User Management, Profile.

### C. Field Salesman Desk (`salesman.a@foodflow.local` / `salesman.b@foodflow.local`)
- **Focus:** Field order booking and customer relationship management.
- **KPI Cards (5):** My Total Orders, Pending Orders, Approved Orders, Dispatched Orders, My Total Sales Revenue.
- **Unique Capabilities:**
  - **Live Factory Finished Goods Catalog:** Real-time visibility into available factory finished goods stock to prevent booking out-of-stock items.
  - **Mobile Bottom Navigation Bar:** Quick one-touch buttons for *Dashboard*, *New Order*, *Orders*, *Customers*, and *Profile*.
- **Data Protection:** Restricted from viewing factory raw material stocks, production batch costs, profit margins, purchase bills, and company-wide financial registers.

### D. Production Supervisor Floor (`production@foodflow.local`)
- **Focus:** Factory manufacturing execution, recipe BOM management, and wastage control.
- **KPI Cards (7):** Today's Production, Planned Output, Actual Output, Production Efficiency, Finished Packets, Material Alerts, Yield Alerts.
- **Unique Capabilities:**
  - **Material Readiness Table:** Live indicators confirming whether flours, oils, and pouches are in stock before scheduling batches.
  - **Yield & Consumption Tracking:** Automatic tolerance badges flagged when batches exceed $\pm 3\%$ scrap or variance.
- **Navigation:** Dashboard, Production Runs, Create Production Run, Bill of Materials, Raw Materials, Material Consumption, Finished Goods, Stock Ledger, Profile.

### E. Accountant & Statutory Auditor Portal (`auditor@foodflow.local`)
- **Focus:** Read-only accounting oversight, GST return reconciliation, and receivables aging.
- **KPI Cards (6):** Total Invoiced, Payments Collected, Outstanding Receivables, Total Output GST, Current Month Turnover, Total Production Cost.
- **Unique Capabilities:**
  - **GSTR-1 Outward Supplies Summary:** Reconciles B2B, B2C, Taxable Value, CGST, SGST, and IGST totals for easy filing.
  - **Customer Ageing Breakdown:** Categorizes receivables into 0–30, 31–60, 61–90, and 90+ days brackets.
  - **Statutory Exports:** One-click downloads for Sales Register, Purchase Register, Stock Movement, and Invoices in Excel (`.xlsx`) and CSV formats.
- **Data Protection:** Read-only mode prevents accidental or unauthorized mutations to orders, purchases, or production runs.

---

## 4. UI/UX & Responsive Design Highlights

1. **Centered Flexbox Login Page:**
   - Independent, responsive viewport layout (`max-width: 440px`) centered on all devices.
   - Interactive password visibility toggle (Lucide eye/eye-off icons).
   - "Remember Me" session persistence.
   - Collapsible reviewer helper drawer for instant demo role switching.
2. **Mobile & Tablet Drawer Navigation:**
   - Off-canvas sidebar with hamburger menu toggle and dim backdrop on screens $< 992\text{px}$.
   - Dedicated mobile tab bar for field salesmen on smartphones.
3. **User Self-Service Profile (`/profile`):**
   - Displays user details, assigned roles, and phone number.
   - Password update form with current password verification.
4. **Professional Custom Error Pages:**
   - `403 Forbidden` ([errors/403.html](file:///c:/Users/KiTE/Desktop/FoodFlow/app/templates/errors/403.html)): Explains role boundaries with a button to return to the user's home workspace.
   - `404 Not Found` ([errors/404.html](file:///c:/Users/KiTE/Desktop/FoodFlow/app/templates/errors/404.html)): Professional missing-page handler.
   - `500 Server Error` ([errors/500.html](file:///c:/Users/KiTE/Desktop/FoodFlow/app/templates/errors/500.html)): Clean incident notification without leaking backend stack traces.

---

## 5. Indian Business Compliance & Localization

Designed from the ground up for Indian manufacturing operations:

- **Currency & Formatting:** Indian Rupee (`₹`) with standard Indian digit grouping (`₹1,25,000.00`) across all user interfaces, PDFs, and spreadsheets.
- **Date Format:** Standard Indian `DD-MM-YYYY` across all tables, forms, and audit timestamps.
- **GST Compliance:**
  - **Place of Supply Logic:** Compares Supplier Factory State (**Tamil Nadu**) with Customer State.
  - **Intra-State Transactions (e.g., Tamil Nadu to Tamil Nadu):** Splits GST evenly into **CGST** (2.5%) and **SGST** (2.5%).
  - **Inter-State Transactions (e.g., Tamil Nadu to Karnataka):** Applies full GST as **IGST** (5.0%).
  - **HSN / SAC Codes:** Recorded at item level for regulatory outward supply reporting.
  - **Invoice Numbering:** Sequential, reset per Indian Financial Year (`FF/24-25/0001`, `FF/24-25/0002`).
  - **Credit Notes:** Supported for damaged goods, price disputes, or returns with sequential numbering (`CN/24-25/0001`).
- **Standard Units of Measure:** `kg`, `grams`, `litres`, `ml`, `pieces`, `packets`, and `cartons` with fractional support up to 3 decimal places.

---

## 6. Inventory & Production Costing Methodology

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

## 7. Verification Against Benchmark Dataset (Sections 22 & 23)

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

## 8. Quick Start Guide (Windows)

### Prerequisites
- Python 3.10+ (Python 3.13 tested)
- PostgreSQL 14+ running locally on port `5432`
- Git

### Step 1: Start PostgreSQL Daemon
```powershell
# From the project root (using local PostgreSQL distribution):
pgsql\bin\postgres.exe -D pgsql\data
```

### Step 2: Virtual Environment & Dependencies
```powershell
cd C:\Users\KiTE\Desktop\FoodFlow
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Step 3: Run Database Migrations & Benchmark Seed
```powershell
flask db upgrade
python scripts/seed_benchmark.py
```

### Step 4: Start the Flask Application
```powershell
python run.py
```
Open your browser and navigate to: **`http://127.0.0.1:5000`**

---

## 9. Demo Accounts (Password for all: `Admin@123`)

| Role | Email | Key Capabilities |
| :--- | :--- | :--- |
| **Owner** | `owner@foodflow.local` | Executive performance, Sales vs Production charts, Top debtors doughnut chart, operational alerts. |
| **Admin** | `admin@foodflow.local` | Order approvals, GST invoice generation, dispatch, purchasing, and staff User Management (`/master/users`). |
| **Salesman A** | `salesman.a@foodflow.local` | Mobile field order booking (`/orders/new`), live finished goods availability catalog, personal order tracking. |
| **Salesman B** | `salesman.b@foodflow.local` | Second sales territory representative with isolated order book. |
| **Production** | `production@foodflow.local` | BOM recipe execution, batch runs (`/production/new`), yield variance tracking, raw material readiness. |
| **Auditor** | `auditor@foodflow.local` | Read-only GSTR-1 outward reconciliation, receivables ageing (0–90+ days), Excel (`.xlsx`) registers export. |

---

## 10. Automated Testing & Verification

### Pytest Unit & Integration Suite
Run the full 15-test automated test suite:
```powershell
.venv\Scripts\pytest.exe -v
```
**Results:** `15 passed in 8.34s` (100% pass rate covering inventory atomicity, duplicate prevention, negative stock protection, production batch costing, yield variances, GST calculations, FIFO payment allocations, dispatch deduction, and PDF/Excel generation).

### End-to-End Role Verification Script
Run the automated multi-role access control suite:
```powershell
.venv\Scripts\python.exe scripts/verify_roles_e2e.py
```
**Results:** `All 5 roles passed RBAC and endpoint tests with 100% success` (validates HTTP 200 on authorized routes and HTTP 403 on restricted endpoints for all 5 roles).

---

## 11. Regulatory & Operational Reports (17 Types)

FoodFlow ERP provides 17 standard regulatory, accounting, and operational reports with date range filtering, live web viewing, CSV export, and OpenPyXL Excel (`.xlsx`) downloads:

1. **Sales Register:** Chronological tax invoices with taxable, CGST, SGST, IGST, and grand totals.
2. **Customer-Wise Sales Summary:** Aggregate turnover and tax breakdown by client.
3. **Product-Wise Sales Summary:** Packets sold and revenue generated per SKU.
4. **GST Outward Supplies Summary:** Ready reconciliation for GSTR-1 & GSTR-3B filings.
5. **Purchase Register:** Supplier invoices, received quantities, and input tax credit (ITC).
6. **Raw Material Stock Summary:** Opening, inward, consumed, closing balances, and valuations.
7. **Packaging Material Stock Summary:** Pouch and carton closing balances and machine scrap.
8. **Finished Goods Stock Summary:** Good output, dispatched units, and closing packet inventory.
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

## 12. Security & Compliance Summary

* **OWASP Hardened:** All forms protected by Flask-WTF CSRF tokens; inputs sanitized; SQL injection prevented via SQLAlchemy parameterized queries.
* **Granular RBAC:** Decorators validate role membership on every HTTP request; unauthorized access triggers HTTP 403 with logged audit events.
* **Immutable Audit Trail:** Append-only `audit_logs` table records user ID, action (`CREATE`, `UPDATE`, `POST`), module, record ID, and change descriptions.
* **Precision Decimals:** Zero floating-point rounding errors on financial or inventory transactions.
