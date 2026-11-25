from datetime import datetime
from decimal import Decimal
from app import db


class SalesOrder(db.Model):
    __tablename__ = 'sales_orders'
    
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    salesman_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    order_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(30), default='Submitted', nullable=False, index=True)
    # Submitted, Under Review, Approved, Rejected, Invoiced, Partially Dispatched, Dispatched
    rejection_reason = db.Column(db.String(255))
    total_taxable_amount = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    total_tax_amount = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    total_amount = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    remarks = db.Column(db.Text)
    idempotency_key = db.Column(db.String(100), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    items = db.relationship('SalesOrderItem', backref='sales_order', lazy='dynamic', cascade='all, delete-orphan')
    invoices = db.relationship('Invoice', backref='sales_order', lazy='dynamic')
    dispatches = db.relationship('Dispatch', backref='sales_order', lazy='dynamic')
    
    @property
    def total_dispatched_quantity(self):
        return sum(item.dispatched_quantity for item in self.items)
    
    @property
    def total_ordered_quantity(self):
        return sum(item.quantity for item in self.items)
    
    @property
    def is_fully_dispatched(self):
        return self.total_dispatched_quantity >= self.total_ordered_quantity and self.total_ordered_quantity > 0
    
    def __repr__(self):
        return f"<SalesOrder {self.order_number} ({self.status})>"


class SalesOrderItem(db.Model):
    __tablename__ = 'sales_order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    sales_order_id = db.Column(db.Integer, db.ForeignKey('sales_orders.id', ondelete='CASCADE'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Numeric(12, 2), nullable=False)
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)  # Selling price before tax
    gst_rate = db.Column(db.Numeric(5, 2), default=Decimal('5.00'), nullable=False)
    taxable_amount = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    cgst_amount = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    sgst_amount = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    igst_amount = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    total_amount = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    dispatched_quantity = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    
    def __repr__(self):
        return f"<SalesOrderItem SO#{self.sales_order_id} Prod#{self.product_id}: {self.quantity} pkts>"
