import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.user import User

app = create_app()

def test_role(client, role_name, email, allowed_checks, forbidden_checks):
    print(f"\n=======================================================")
    print(f"Testing Role: {role_name} ({email})")
    print(f"=======================================================")
    
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if not user:
            print(f"  [FAIL] User {email} not found in database!")
            return False

    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)
        sess['_fresh'] = True
        
    all_ok = True
    for path, expected_text in allowed_checks:
        res = client.get(path, follow_redirects=True)
        html = res.get_data(as_text=True)
        if res.status_code == 200 and (expected_text is None or expected_text in html):
            print(f"  [PASS] Allowed {path} -> 200 OK (Contains: '{expected_text}')")
        else:
            print(f"  [FAIL] Allowed {path} -> Status: {res.status_code}, Found text: {expected_text in html if expected_text else 'N/A'}")
            all_ok = False
            
    for item in forbidden_checks:
        path = item[0]
        res = client.get(path, follow_redirects=False)
        if res.status_code in [403, 302]:
            print(f"  [PASS] Forbidden {path} -> Blocked with {res.status_code}")
        else:
            print(f"  [FAIL] Forbidden {path} -> UNEXPECTED STATUS {res.status_code}")
            all_ok = False
            
    return all_ok

def main():
    client = app.test_client()
    results = {}
    
    # 1. OWNER
    owner_allowed = [
        ("/", "Executive Business Performance"),
        ("/reports/?type=sales_register", "Sales Register"),
        ("/inventory/", "Inventory Valuation"),
        ("/production/", "Production Runs"),
        ("/reports/?type=stock_movement", "Stock Movement"),
        ("/profile", "My Profile")
    ]
    owner_forbidden = [
        ("/master/users",),
    ]
    results['Owner'] = test_role(client, "Owner", "owner@foodflow.local", owner_allowed, owner_forbidden)
    
    # 2. ADMIN
    admin_allowed = [
        ("/", "Factory Operations Dashboard"),
        ("/orders/", "Sales Orders"),
        ("/invoices/", "Tax Invoices"),
        ("/dispatch/", "Dispatch"),
        ("/payments/", "Payments"),
        ("/purchases/", "Raw Material Purchases"),
        ("/master/users", "User Management"),
        ("/master/customers", "Customers Master"),
        ("/master/suppliers", "Suppliers Master"),
        ("/master/products", "Finished Products Master"),
        ("/master/raw-materials", "Raw Materials Master"),
        ("/bom/", "Bill of Materials"),
        ("/profile", "My Profile")
    ]
    admin_forbidden = []
    results['Admin'] = test_role(client, "Admin", "admin@foodflow.local", admin_allowed, admin_forbidden)
    
    # 3. SALESMAN
    salesman_allowed = [
        ("/", "Field Sales Workspace"),
        ("/orders/new", "Create Sales Order"),
        ("/orders/", "Sales Orders"),
        ("/master/customers", "Customers Master"),
        ("/profile", "My Profile")
    ]
    salesman_forbidden = [
        ("/invoices/",),
        ("/purchases/",),
        ("/production/",),
        ("/master/users",),
        ("/reports/",),
        ("/inventory/",)
    ]
    results['Salesman'] = test_role(client, "Salesman", "salesman.a@foodflow.local", salesman_allowed, salesman_forbidden)
    
    # 4. PRODUCTION SUPERVISOR
    prod_allowed = [
        ("/", "Production & Factory Floor Workspace"),
        ("/production/", "Production Runs"),
        ("/production/new", "Production Batch Entry"),
        ("/inventory/", "Inventory Valuation"),
        ("/bom/", "Bill of Materials"),
        ("/reports/?type=yield_report", "Yield Report"),
        ("/reports/?type=consumption_analysis", "Planned vs Actual Consumption"),
        ("/profile", "My Profile")
    ]
    prod_forbidden = [
        ("/invoices/",),
        ("/payments/",),
        ("/purchases/",),
        ("/orders/new",),
        ("/reports/?type=sales_register",),
        ("/reports/?type=gst_outward",),
        ("/master/users",),
    ]
    results['Production'] = test_role(client, "Production Supervisor", "production@foodflow.local", prod_allowed, prod_forbidden)
    
    # 5. AUDITOR / ACCOUNTANT
    auditor_allowed = [
        ("/", "Financial & Statutory Audit Workspace"),
        ("/reports/?type=sales_register", "Sales Register"),
        ("/reports/?type=gst_outward", "GST Outward Supplies"),
        ("/reports/?type=stock_movement", "Stock Movement"),
        ("/invoices/", "Tax Invoices"),
        ("/payments/", "Payments"),
        ("/inventory/", "Inventory Valuation"),
        ("/profile", "My Profile")
    ]
    auditor_forbidden = [
        ("/production/new",),
        ("/orders/new",),
        ("/purchases/new",),
        ("/master/users",)
    ]
    results['Auditor'] = test_role(client, "Accountant / Auditor", "auditor@foodflow.local", auditor_allowed, auditor_forbidden)
    
    print("\n=======================================================")
    print("SUMMARY OF ROLE-BASED ACCESS CONTROL (RBAC) TESTS:")
    print("=======================================================")
    all_passed = True
    for role, passed in results.items():
        status = "PASSED [OK]" if passed else "FAILED [X]"
        print(f"  {role:25}: {status}")
        if not passed:
            all_passed = False
            
    if all_passed:
        print("\nALL 5 ROLES PASSED RBAC AND ENDPOINT TESTS WITH 100% SUCCESS!")
        sys.exit(0)
    else:
        print("\nSOME TESTS FAILED!")
        sys.exit(1)

if __name__ == '__main__':
    main()
