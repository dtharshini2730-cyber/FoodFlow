import os
import sys
from datetime import date, datetime
from decimal import Decimal

# Add root directory to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from app import create_app, db
from app.models.user import User, Role
from app.models.master import Customer, Supplier, Product, RawMaterial, PackagingMaterial, Unit
from app.models.bom import ProductBOM, BOMVersion, BOMItem
from app.models.billing import Invoice
from app.services.stock_service import StockService
from app.services.production_service import ProductionService
from app.services.order_service import OrderService
from app.services.invoice_service import InvoiceService
from app.services.dispatch_service import DispatchService
from app.services.payment_service import PaymentService


def seed_all():
    app = create_app('development')
    with app.app_context():
        print("--- Clearing existing database tables ---")
        db.drop_all()
        db.create_all()
        print("Database schema created cleanly.")
        
        # 1. Create Roles
        roles_data = [
            ('owner', 'Business Owner / Managing Director'),
            ('admin', 'Operations & Sales Administrator'),
            ('salesman', 'Field Sales Representative'),
            ('production', 'Factory Production Supervisor'),
            ('auditor', 'Chartered Accountant / Internal Auditor')
        ]
        roles = {}
        for name, desc in roles_data:
            role = Role(name=name, description=desc)
            db.session.add(role)
            roles[name] = role
        db.session.commit()
        print("[1/9] Roles created.")

        # 2. Create User Accounts (Section 26)
        dev_password = 'Admin@123'
        users_data = [
            ('owner@foodflow.local', 'owner', 'S. Ramanathan (Owner)', 'owner', '+91 94431 10001'),
            ('admin@foodflow.local', 'admin', 'M. Sundaram (Admin)', 'admin', '+91 94431 10002'),
            ('salesman.a@foodflow.local', 'salesman_a', 'K. Murugan (Salesman A)', 'salesman', '+91 94431 10003'),
            ('salesman.b@foodflow.local', 'salesman_b', 'V. Karthik (Salesman B)', 'salesman', '+91 94431 10004'),
            ('production@foodflow.local', 'production', 'P. Selvam (Production Head)', 'production', '+91 94431 10005'),
            ('auditor@foodflow.local', 'auditor', 'CA R. Venkatraman (Auditor)', 'auditor', '+91 94431 10006'),
        ]
        users = {}
        for email, username, full_name, role_name, phone in users_data:
            user = User(
                email=email,
                username=username,
                full_name=full_name,
                phone=phone,
                is_active=True
            )
            user.set_password(dev_password)
            user.roles.append(roles[role_name])
            db.session.add(user)
            users[email] = user
        db.session.commit()
        print("[2/9] User accounts created with password 'Admin@123'.")

        admin_user = users['admin@foodflow.local']
        salesman_a = users['salesman.a@foodflow.local']
        salesman_b = users['salesman.b@foodflow.local']
        prod_user = users['production@foodflow.local']

        # 3. Create Standard Units
        units_data = [
            ('kg', 'Kilogram', 'weight', Decimal('1.0000')),
            ('g', 'Gram', 'weight', Decimal('0.0010')),
            ('litres', 'Litres', 'volume', Decimal('1.0000')),
            ('ml', 'Millilitre', 'volume', Decimal('0.0010')),
            ('pieces', 'Pieces', 'count', Decimal('1.0000')),
            ('packets', 'Packets', 'count', Decimal('1.0000')),
            ('cartons', 'Cartons (20 pkts)', 'count', Decimal('20.0000'))
        ]
        for code, name, b_type, conv in units_data:
            db.session.add(Unit(code=code, name=name, base_type=b_type, conversion_factor_to_base=conv))
        db.session.commit()
        print("[3/9] Standard units created.")

        # 4. Create Customers & Suppliers
        customer_a = Customer(
            name='Retailer A Provisions',
            customer_type='Retailer',
            contact_person='A. Kumar',
            mobile_number='+91 98421 22222',
            address='45 Main Bazaar, Thillai Nagar, Tiruchirappalli',
            state='Tamil Nadu',
            gstin='33AAACR1234A1Z5',
            assigned_salesman_id=salesman_a.id,
            credit_limit=Decimal('50000.00'),
            is_active=True
        )
        customer_b = Customer(
            name='Distributor B Enterprises',
            customer_type='Distributor',
            contact_person='B. Suresh',
            mobile_number='+91 98421 33333',
            address='12 BVK Iyengar Road, Chickpet, Bengaluru',
            state='Karnataka',
            gstin='29AAACB5678B1Z8',
            assigned_salesman_id=salesman_b.id,
            credit_limit=Decimal('100000.00'),
            is_active=True
        )
        supplier_1 = Supplier(
            name='Trichy Agro Millers',
            contact_details='+91 94432 55555',
            gstin='33AAACT9999C1Z1',
            address='7 Industrial Estate, Thuvakudi, Tiruchirappalli',
            state='Tamil Nadu',
            is_active=True
        )
        db.session.add_all([customer_a, customer_b, supplier_1])
        db.session.commit()
        print("[4/9] Customers and Suppliers created.")

        # 5. Create Product & BOM (Section 22)
        product_murukku = Product(
            name='Murukku 200 g',
            sku='MRK-200G',
            description='Crisp, aromatic traditional South Indian savoury snack',
            category='Snacks',
            pack_size='200 g',
            selling_price=Decimal('50.00'),  # Before tax: ₹50
            gst_rate=Decimal('5.00'),         # GST: 5%
            hsn_code='19059040',              # Configurable dummy HSN
            unit='packets',
            is_active=True
        )
        db.session.add(product_murukku)
        db.session.commit()

        # Raw Materials
        rm_flour = RawMaterial(
            name='Rice & Urad Flour Mix',
            sku='RM-FLOUR',
            base_unit='kg',
            opening_stock=Decimal('100.000'),
            reorder_level=Decimal('30.000'),
            current_rate=Decimal('42.0000'),  # Opening Flour Valuation: ₹42/kg
            is_active=True
        )
        rm_oil = RawMaterial(
            name='Refined Cooking Oil',
            sku='RM-OIL',
            base_unit='litres',
            opening_stock=Decimal('30.000'),
            reorder_level=Decimal('10.000'),
            current_rate=Decimal('140.0000'), # Opening Oil Valuation: ₹140/L
            is_active=True
        )
        rm_spice = RawMaterial(
            name='Salt and Spice Mix',
            sku='RM-SPICE',
            base_unit='kg',
            opening_stock=Decimal('5.000'),
            reorder_level=Decimal('2.000'),
            current_rate=Decimal('200.0000'), # Opening Spice Mix Valuation: ₹200/kg
            is_active=True
        )
        db.session.add_all([rm_flour, rm_oil, rm_spice])

        # Packaging Materials
        pm_pouch = PackagingMaterial(
            name='200 g Printed Pouches',
            sku='PKG-POUCH-200',
            unit='pieces',
            opening_quantity=Decimal('500.000'),
            reorder_level=Decimal('100.000'),
            current_rate=Decimal('2.5000'),   # Pouch cost: ₹2.50/pc (194 pouches = ₹485)
            is_active=True
        )
        pm_carton = PackagingMaterial(
            name='Master Shipping Cartons',
            sku='PKG-CARTON',
            unit='pieces',
            opening_quantity=Decimal('30.000'),
            reorder_level=Decimal('10.000'),
            current_rate=Decimal('15.0000'),  # Carton cost: ₹15.00/pc (9 cartons = ₹135)
            is_active=True
        )
        db.session.add_all([pm_pouch, pm_carton])
        db.session.commit()

        # Recipe BOM Configuration (1 batch = 200 expected packets)
        bom = ProductBOM(product_id=product_murukku.id, is_active=True)
        db.session.add(bom)
        db.session.flush()

        bom_v1 = BOMVersion(
            bom_id=bom.id,
            version_number=1,
            batch_size=Decimal('1.00'),
            expected_output=Decimal('200.00'),
            expected_yield_pct=Decimal('100.00'),
            notes='Standard benchmark recipe: Flour 40kg, Oil 10L, Spice 1.2kg, Pouches 200pcs, Cartons 10pcs',
            is_active=True
        )
        db.session.add(bom_v1)
        db.session.flush()

        bom_items = [
            BOMItem(bom_version_id=bom_v1.id, item_type='raw_material', item_id=rm_flour.id, standard_quantity=Decimal('40.000'), unit='kg'),
            BOMItem(bom_version_id=bom_v1.id, item_type='raw_material', item_id=rm_oil.id, standard_quantity=Decimal('10.000'), unit='litres'),
            BOMItem(bom_version_id=bom_v1.id, item_type='raw_material', item_id=rm_spice.id, standard_quantity=Decimal('1.200'), unit='kg'),
            BOMItem(bom_version_id=bom_v1.id, item_type='packaging_material', item_id=pm_pouch.id, standard_quantity=Decimal('200.000'), unit='pieces'),
            BOMItem(bom_version_id=bom_v1.id, item_type='packaging_material', item_id=pm_carton.id, standard_quantity=Decimal('10.000'), unit='pieces'),
        ]
        db.session.add_all(bom_items)
        db.session.commit()
        print("[5/9] Product, Materials, and Recipe BOM created.")

        # 6. Post Opening Stock to Stock Ledger (Section 22)
        # Flour: 100 kg, Oil: 30 L, Spice: 5 kg, Pouches: 500 pcs, Cartons: 30 pcs, Finished Murukku: 50 packets
        opening_movements = [
            ('raw_material', rm_flour.id, Decimal('100.000'), 'kg', rm_flour.current_rate),
            ('raw_material', rm_oil.id, Decimal('30.000'), 'litres', rm_oil.current_rate),
            ('raw_material', rm_spice.id, Decimal('5.000'), 'kg', rm_spice.current_rate),
            ('packaging_material', pm_pouch.id, Decimal('500.000'), 'pieces', pm_pouch.current_rate),
            ('packaging_material', pm_carton.id, Decimal('30.000'), 'pieces', pm_carton.current_rate),
            ('finished_good', product_murukku.id, Decimal('50.000'), 'packets', Decimal('31.14')),
        ]
        opening_date = date(2024, 4, 1)
        for i_type, i_id, qty, unit, rate in opening_movements:
            StockService.record_movement(
                item_type=i_type,
                item_id=i_id,
                movement_date=opening_date,
                movement_type='opening_stock',
                quantity=qty,
                unit=unit,
                direction='IN',
                source_document_type='OpeningStock',
                source_document_id=None,
                unit_rate=rate,
                user_id=admin_user.id
            )
        db.session.commit()
        print("[6/9] Opening stock posted to StockLedger.")

        # 7. Post New Purchase of Flour (Section 22)
        # Flour: 60 kg @ ₹45/kg
        purchase_data = {
            'supplier_id': supplier_1.id,
            'purchase_date': '2024-04-05',
            'supplier_invoice_no': 'TAM-2024-042',
            'items': [
                {
                    'item_type': 'raw_material',
                    'item_id': rm_flour.id,
                    'quantity': Decimal('60.000'),
                    'unit': 'kg',
                    'unit_rate': Decimal('45.0000'),
                    'tax_rate': Decimal('5.00')
                }
            ]
        }
        purchase = StockService.post_purchase(purchase_data, admin_user.id)
        db.session.commit()
        
        # Verify Flour Weighted Average: ((100 * 42) + (60 * 45)) / 160 = ₹43.125/kg
        flour_refreshed = RawMaterial.query.get(rm_flour.id)
        flour_stock = StockService.get_stock_balance('raw_material', rm_flour.id)
        print(f"[7/9] Purchase posted. Flour closing: {flour_stock} kg (Expected: 160.000). Rate: ₹{flour_refreshed.current_rate}/kg (Expected: 43.125).")

        # 8. Post Production Run (Section 22 & 23)
        # Flour issued: 40 kg, Oil issued: 10.5 L (+5% variance -> alert!), Spice: 1.2 kg
        # Good packets produced: 188 (-6% yield variance -> alert!)
        # Damaged pouches: 6 pcs, Cartons used: 9 pcs
        # Labour: ₹1,200, Gas/power: ₹600
        run_data = {
            'product_id': product_murukku.id,
            'bom_version_id': bom_v1.id,
            'batch_count': Decimal('1.00'),
            'actual_output': Decimal('188.00'),
            'damaged_output': Decimal('0.00'),
            'production_date': '2024-04-10',
            'labour_cost': Decimal('1200.00'),
            'gas_cost': Decimal('400.00'),
            'power_cost': Decimal('200.00'),
            'other_overhead_cost': Decimal('0.00'),
            'remarks': 'Mandatory benchmark production run',
            'consumptions': [
                {'item_type': 'raw_material', 'item_id': rm_flour.id, 'actual_quantity': Decimal('40.000'), 'damaged_quantity': Decimal('0.000'), 'unit': 'kg'},
                {'item_type': 'raw_material', 'item_id': rm_oil.id, 'actual_quantity': Decimal('10.500'), 'damaged_quantity': Decimal('0.000'), 'unit': 'litres'},
                {'item_type': 'raw_material', 'item_id': rm_spice.id, 'actual_quantity': Decimal('1.200'), 'damaged_quantity': Decimal('0.000'), 'unit': 'kg'},
                {'item_type': 'packaging_material', 'item_id': pm_pouch.id, 'actual_quantity': Decimal('188.000'), 'damaged_quantity': Decimal('6.000'), 'unit': 'pieces'},
                {'item_type': 'packaging_material', 'item_id': pm_carton.id, 'actual_quantity': Decimal('9.000'), 'damaged_quantity': Decimal('0.000'), 'unit': 'pieces'},
            ]
        }
        prod_run = ProductionService.create_production_run(run_data, prod_user.id)
        db.session.commit()
        print(f"[8/9] Production run #{prod_run.run_number} posted. Output: {prod_run.actual_output} pkts, Yield Var: {prod_run.yield_variance_pct}%, Total Cost: ₹{prod_run.total_production_cost}, Cost/Pkt: ₹{prod_run.cost_per_packet:.4f}.")

        # 9. Sales Operations & Payments (Section 22 & 23)
        # Salesman A: Retailer A (Tamil Nadu), Quantity: 150 packets
        order_a_data = {
            'customer_id': customer_a.id,
            'order_date': '2024-04-12',
            'remarks': 'Benchmark order Retailer A (Tamil Nadu)',
            'items': [{'product_id': product_murukku.id, 'quantity': Decimal('150.00')}]
        }
        order_a = OrderService.create_sales_order(order_a_data, salesman_a.id)
        db.session.commit()

        # Admin approves Order A
        OrderService.approve_order(order_a.id, admin_user.id)
        db.session.commit()

        # Generate GST Tax Invoice for Order A (Taxable: ₹7,500, CGST: ₹187.50, SGST: ₹187.50, Total: ₹7,875)
        invoice_a = InvoiceService.create_invoice_from_order(order_a.id, admin_user.id)
        db.session.commit()

        # Dispatch 150 packets for Retailer A
        dispatch_a_data = {
            'sales_order_id': order_a.id,
            'invoice_id': invoice_a.id,
            'dispatch_date': '2024-04-13',
            'vehicle_no': 'TN 45 AB 1234',
            'remarks': 'Full order delivery to Retailer A',
            'items': [{'product_id': product_murukku.id, 'quantity': Decimal('150.00')}]
        }
        DispatchService.create_dispatch(dispatch_a_data, admin_user.id)
        db.session.commit()

        # Retailer A pays ₹4,000 via UPI (Outstanding = ₹7,875 - ₹4,000 = ₹3,875)
        payment_a_data = {
            'customer_id': customer_a.id,
            'amount': Decimal('4000.00'),
            'payment_mode': 'UPI',
            'payment_date': '2024-04-15',
            'reference_number': 'UPI/98421/0001',
            'remarks': 'Partial payment for invoice ' + invoice_a.invoice_number,
            'allocations': [{'invoice_id': invoice_a.id, 'amount': Decimal('4000.00')}]
        }
        PaymentService.record_payment(payment_a_data, admin_user.id)
        db.session.commit()

        # Salesman B: Distributor B (Karnataka), Quantity: 120 packets
        # Note: FG remaining = 238 - 150 = 88 packets. Requested: 120 packets. Shortage = 32 packets.
        # Order is booked but NOT dispatched in full!
        order_b_data = {
            'customer_id': customer_b.id,
            'order_date': '2024-04-14',
            'remarks': 'Interstate order Distributor B (Karnataka) - 120 packets',
            'items': [{'product_id': product_murukku.id, 'quantity': Decimal('120.00')}]
        }
        order_b = OrderService.create_sales_order(order_b_data, salesman_b.id)
        db.session.commit()
        print("[9/9] Sales orders, GST invoice, dispatch and payments posted.")

        print("\n==================================================")
        print("MANDATORY BENCHMARK VERIFICATION RESULTS")
        print("==================================================")
        
        # Flour stock: 100 + 60 - 40 = 120 kg
        c_flour = StockService.get_stock_balance('raw_material', rm_flour.id)
        print(f"1. Flour Closing Stock:       {c_flour} kg (Expected: 120.000 kg)")
        assert c_flour == Decimal('120.000'), f"Flour stock mismatch: {c_flour}"

        # Oil stock: 30 - 10.5 = 19.5 L
        c_oil = StockService.get_stock_balance('raw_material', rm_oil.id)
        print(f"2. Oil Closing Stock:         {c_oil} litres (Expected: 19.500 litres)")
        assert c_oil == Decimal('19.500'), f"Oil stock mismatch: {c_oil}"

        # Spice mix stock: 5 - 1.2 = 3.8 kg
        c_spice = StockService.get_stock_balance('raw_material', rm_spice.id)
        print(f"3. Spice Mix Closing Stock:   {c_spice} kg (Expected: 3.800 kg)")
        assert c_spice == Decimal('3.800'), f"Spice mix stock mismatch: {c_spice}"

        # Pouches: 500 - 188 - 6 = 306 pieces
        c_pouch = StockService.get_stock_balance('packaging_material', pm_pouch.id)
        print(f"4. Pouches Closing Stock:     {c_pouch} pieces (Expected: 306.000 pieces)")
        assert c_pouch == Decimal('306.000'), f"Pouch stock mismatch: {c_pouch}"

        # Cartons: 30 - 9 = 21 pieces
        c_carton = StockService.get_stock_balance('packaging_material', pm_carton.id)
        print(f"5. Cartons Closing Stock:     {c_carton} pieces (Expected: 21.000 pieces)")
        assert c_carton == Decimal('21.000'), f"Carton stock mismatch: {c_carton}"

        # Finished Goods stock after Retailer A dispatch: 50 + 188 - 150 = 88 packets
        c_fg = StockService.get_stock_balance('finished_good', product_murukku.id)
        print(f"6. Finished Goods Remaining:  {c_fg} packets (Expected: 88.000 packets)")
        assert c_fg == Decimal('88.000'), f"Finished goods stock mismatch: {c_fg}"

        # Yield variance: (188 - 200)/200 * 100 = -6%
        print(f"7. Yield Variance:            {prod_run.yield_variance_pct}% (Expected: -6.00%)")
        assert prod_run.yield_variance_pct == Decimal('-6.00'), f"Yield variance mismatch: {prod_run.yield_variance_pct}"
        assert prod_run.yield_variance_alert == True, "Yield variance alert was not triggered!"

        # Oil variance: (10.5 - 10)/10 * 100 = +5%
        oil_c = prod_run.consumptions.filter_by(item_type='raw_material', item_id=rm_oil.id).first()
        print(f"8. Oil Variance:              +{oil_c.variance_pct}% (Expected: +5.00%)")
        assert oil_c.variance_pct == Decimal('5.00'), f"Oil variance mismatch: {oil_c.variance_pct}"
        assert oil_c.variance_alert == True, "Oil variance alert was not triggered!"

        # GST Invoice A: Taxable = ₹7,500, CGST = ₹187.50, SGST = ₹187.50, Total = ₹7,875
        print(f"9. GST Invoice Taxable:       ₹{invoice_a.total_taxable} (Expected: 7500.00)")
        print(f"   CGST:                      ₹{invoice_a.cgst_total} (Expected: 187.50)")
        print(f"   SGST:                      ₹{invoice_a.sgst_total} (Expected: 187.50)")
        print(f"   Grand Total:               ₹{invoice_a.grand_total} (Expected: 7875.00)")
        assert invoice_a.total_taxable == Decimal('7500.00'), f"Taxable mismatch: {invoice_a.total_taxable}"
        assert invoice_a.cgst_total == Decimal('187.50'), f"CGST mismatch: {invoice_a.cgst_total}"
        assert invoice_a.sgst_total == Decimal('187.50'), f"SGST mismatch: {invoice_a.sgst_total}"
        assert invoice_a.grand_total == Decimal('7875.00'), f"Total mismatch: {invoice_a.grand_total}"

        # Outstanding after Retailer A payment: ₹7,875 - ₹4,000 = ₹3,875
        inv_a_refreshed = Invoice.query.get(invoice_a.id)
        print(f"10. Retailer A Outstanding:   ₹{inv_a_refreshed.outstanding_amount} (Expected: 3875.00)")
        assert inv_a_refreshed.outstanding_amount == Decimal('3875.00'), f"Outstanding mismatch: {inv_a_refreshed.outstanding_amount}"

        # Distributor B Shortage: Requested = 120, Available = 88, Shortage = 32
        stock_check_b = OrderService.check_order_stock_availability(order_b.id)
        b_item_stock = stock_check_b['items'][0]
        print(f"11. Distributor B Requested:  {b_item_stock['requested_qty']} pkts")
        print(f"    Distributor B Available:  {b_item_stock['available_qty']} pkts")
        print(f"    Distributor B Shortage:   {b_item_stock['shortage_qty']} pkts (Expected: 32 pkts)")
        assert b_item_stock['shortage_qty'] == Decimal('32.00'), f"Shortage mismatch: {b_item_stock['shortage_qty']}"

        # Production Cost: Total = ₹5,855, Cost per good packet: ~₹31.14
        print(f"12. Total Production Cost:    ₹{prod_run.total_production_cost} (Expected: 5855.00)")
        print(f"    Cost Per Good Packet:     ₹{prod_run.cost_per_packet:.4f} (Expected: ~31.14)")
        assert prod_run.total_production_cost == Decimal('5855.00'), f"Total production cost mismatch: {prod_run.total_production_cost}"
        assert round(prod_run.cost_per_packet, 2) == Decimal('31.14'), f"Cost per packet mismatch: {prod_run.cost_per_packet}"

        print("==================================================")
        print("ALL MANDATORY BENCHMARK CHECKS PASSED PERFECTLY!")
        print("==================================================")


if __name__ == '__main__':
    seed_all()
