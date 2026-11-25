from datetime import datetime
from decimal import Decimal
from app import db


class Unit(db.Model):
    __tablename__ = 'units'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)  # kg, g, l, ml, pcs, pkt, ctn
    name = db.Column(db.String(50), nullable=False)
    base_type = db.Column(db.String(20), nullable=False)  # weight, volume, count
    conversion_factor_to_base = db.Column(db.Numeric(12, 4), default=Decimal('1.0000'), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    def __repr__(self):
        return f"<Unit {self.code}>"


class Customer(db.Model):
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    customer_type = db.Column(db.String(50), default='Retailer', nullable=False)  # Retailer / Distributor
    contact_person = db.Column(db.String(100))
    mobile_number = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text, nullable=False)
    state = db.Column(db.String(50), default='Tamil Nadu', nullable=False)
    gstin = db.Column(db.String(15))
    assigned_salesman_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    credit_limit = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    orders = db.relationship('SalesOrder', backref='customer', lazy='dynamic')
    invoices = db.relationship('Invoice', backref='customer', lazy='dynamic')
    payments = db.relationship('Payment', backref='customer', lazy='dynamic')
    
    @property
    def is_interstate(self):
        """Returns True if customer state is outside Tamil Nadu."""
        return self.state.strip().lower() != 'tamil nadu'
    
    def __repr__(self):
        return f"<Customer {self.name}>"


class Supplier(db.Model):
    __tablename__ = 'suppliers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    contact_details = db.Column(db.String(150))
    gstin = db.Column(db.String(15))
    address = db.Column(db.Text, nullable=False)
    state = db.Column(db.String(50), default='Tamil Nadu', nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    purchases = db.relationship('Purchase', backref='supplier', lazy='dynamic')
    
    def __repr__(self):
        return f"<Supplier {self.name}>"


class RawMaterial(db.Model):
    __tablename__ = 'raw_materials'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    base_unit = db.Column(db.String(20), default='kg', nullable=False)
    opening_stock = db.Column(db.Numeric(12, 3), default=Decimal('0.000'), nullable=False)
    reorder_level = db.Column(db.Numeric(12, 3), default=Decimal('10.000'), nullable=False)
    current_rate = db.Column(db.Numeric(12, 4), default=Decimal('0.0000'), nullable=False)  # Weighted average rate
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def get_current_stock(self):
        """Calculate derived stock balance from StockLedger."""
        from app.models.inventory import StockLedger
        from sqlalchemy import func
        total_in = db.session.query(func.coalesce(func.sum(StockLedger.quantity), 0)).filter(
            StockLedger.item_type == 'raw_material',
            StockLedger.item_id == self.id,
            StockLedger.direction == 'IN'
        ).scalar()
        total_out = db.session.query(func.coalesce(func.sum(StockLedger.quantity), 0)).filter(
            StockLedger.item_type == 'raw_material',
            StockLedger.item_id == self.id,
            StockLedger.direction == 'OUT'
        ).scalar()
        return Decimal(str(total_in)) - Decimal(str(total_out))
    
    def __repr__(self):
        return f"<RawMaterial {self.name}>"


class PackagingMaterial(db.Model):
    __tablename__ = 'packaging_materials'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    unit = db.Column(db.String(20), default='pcs', nullable=False)
    opening_quantity = db.Column(db.Numeric(12, 3), default=Decimal('0.000'), nullable=False)
    reorder_level = db.Column(db.Numeric(12, 3), default=Decimal('50.000'), nullable=False)
    current_rate = db.Column(db.Numeric(12, 4), default=Decimal('0.0000'), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def get_current_stock(self):
        """Calculate derived stock balance from StockLedger."""
        from app.models.inventory import StockLedger
        from sqlalchemy import func
        total_in = db.session.query(func.coalesce(func.sum(StockLedger.quantity), 0)).filter(
            StockLedger.item_type == 'packaging_material',
            StockLedger.item_id == self.id,
            StockLedger.direction == 'IN'
        ).scalar()
        total_out = db.session.query(func.coalesce(func.sum(StockLedger.quantity), 0)).filter(
            StockLedger.item_type == 'packaging_material',
            StockLedger.item_id == self.id,
            StockLedger.direction == 'OUT'
        ).scalar()
        return Decimal(str(total_in)) - Decimal(str(total_out))
    
    def __repr__(self):
        return f"<PackagingMaterial {self.name}>"


class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), default='Snacks', nullable=False)
    pack_size = db.Column(db.String(50), default='200 g', nullable=False)
    selling_price = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)  # Before tax
    gst_rate = db.Column(db.Numeric(5, 2), default=Decimal('5.00'), nullable=False)  # 5%
    hsn_code = db.Column(db.String(20), default='19059040', nullable=False)  # Configurable dummy HSN
    unit = db.Column(db.String(20), default='packets', nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    boms = db.relationship('ProductBOM', backref='product', lazy='dynamic')
    order_items = db.relationship('SalesOrderItem', backref='product', lazy='dynamic')
    invoice_items = db.relationship('InvoiceItem', backref='product', lazy='dynamic')
    
    def get_current_stock(self):
        """Calculate finished goods derived stock balance from StockLedger."""
        from app.models.inventory import StockLedger
        from sqlalchemy import func
        total_in = db.session.query(func.coalesce(func.sum(StockLedger.quantity), 0)).filter(
            StockLedger.item_type == 'finished_good',
            StockLedger.item_id == self.id,
            StockLedger.direction == 'IN'
        ).scalar()
        total_out = db.session.query(func.coalesce(func.sum(StockLedger.quantity), 0)).filter(
            StockLedger.item_type == 'finished_good',
            StockLedger.item_id == self.id,
            StockLedger.direction == 'OUT'
        ).scalar()
        return Decimal(str(total_in)) - Decimal(str(total_out))
    
    def __repr__(self):
        return f"<Product {self.name}>"
