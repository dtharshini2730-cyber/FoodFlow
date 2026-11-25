import os
import sys
import pytest
from decimal import Decimal

# Add root directory to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.user import User, Role
from app.models.master import Customer, Supplier, Product, RawMaterial, PackagingMaterial, Unit
from app.models.bom import ProductBOM, BOMVersion, BOMItem


@pytest.fixture(scope='session')
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def session(app):
    with app.app_context():
        # Clear tables before each test
        meta = db.metadata
        for table in reversed(meta.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()
        
        # Seed basic roles and admin user
        role_admin = Role(name='admin', description='Administrator')
        role_owner = Role(name='owner', description='Owner')
        role_salesman = Role(name='salesman', description='Salesman')
        role_production = Role(name='production', description='Production')
        role_auditor = Role(name='auditor', description='Auditor')
        db.session.add_all([role_admin, role_owner, role_salesman, role_production, role_auditor])
        db.session.commit()
        
        admin = User(
            username='admin_test',
            email='admin@test.local',
            full_name='Test Admin',
            is_active=True
        )
        admin.set_password('Admin@123')
        admin.roles.append(role_admin)
        db.session.add(admin)
        db.session.commit()
        
        yield db.session
        db.session.rollback()


@pytest.fixture
def sample_master_data(session):
    admin = User.query.filter_by(username='admin_test').first()
    
    # Raw materials
    rm_flour = RawMaterial(name='Rice Flour', sku='RM-FLOUR-T', base_unit='kg', current_rate=Decimal('42.0000'), is_active=True)
    rm_oil = RawMaterial(name='Oil', sku='RM-OIL-T', base_unit='litres', current_rate=Decimal('140.0000'), is_active=True)
    pm_pouch = PackagingMaterial(name='Pouch 200g', sku='PM-POUCH-T', unit='pieces', current_rate=Decimal('2.5000'), is_active=True)
    
    # Product
    product = Product(name='Murukku 200g', sku='MRK-200G-T', pack_size='200 g', selling_price=Decimal('50.00'), gst_rate=Decimal('5.00'), unit='packets', is_active=True)
    
    # Customer TN & Karnataka
    cust_tn = Customer(name='TN Retailer', mobile_number='9876543210', address='Trichy', state='Tamil Nadu', credit_limit=Decimal('50000'), is_active=True)
    cust_ka = Customer(name='KA Distributor', mobile_number='9876543211', address='Bengaluru', state='Karnataka', credit_limit=Decimal('50000'), is_active=True)
    
    # Supplier
    supplier = Supplier(name='Trichy Mills', address='Trichy', state='Tamil Nadu', is_active=True)
    
    session.add_all([rm_flour, rm_oil, pm_pouch, product, cust_tn, cust_ka, supplier])
    session.commit()
    
    # BOM
    bom = ProductBOM(product_id=product.id, is_active=True)
    session.add(bom)
    session.flush()
    
    bom_v = BOMVersion(bom_id=bom.id, version_number=1, batch_size=Decimal('1.00'), expected_output=Decimal('200.00'), is_active=True)
    session.add(bom_v)
    session.flush()
    
    session.add_all([
        BOMItem(bom_version_id=bom_v.id, item_type='raw_material', item_id=rm_flour.id, standard_quantity=Decimal('40.000'), unit='kg'),
        BOMItem(bom_version_id=bom_v.id, item_type='raw_material', item_id=rm_oil.id, standard_quantity=Decimal('10.000'), unit='litres'),
        BOMItem(bom_version_id=bom_v.id, item_type='packaging_material', item_id=pm_pouch.id, standard_quantity=Decimal('200.000'), unit='pieces')
    ])
    session.commit()
    
    return {
        'admin': admin,
        'flour': rm_flour,
        'oil': rm_oil,
        'pouch': pm_pouch,
        'product': product,
        'cust_tn': cust_tn,
        'cust_ka': cust_ka,
        'supplier': supplier,
        'bom_v': bom_v
    }
