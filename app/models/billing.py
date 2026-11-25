from datetime import datetime
from decimal import Decimal
from app import db


class Invoice(db.Model):
    __tablename__ = 'invoices'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    sales_order_id = db.Column(db.Integer, db.ForeignKey('sales_orders.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    invoice_date = db.Column(db.Date, nullable=False)
    financial_year = db.Column(db.String(20), nullable=False)  # e.g. 2024-25
    place_of_supply = db.Column(db.String(50), nullable=False)
    supplier_name = db.Column(db.String(150), nullable=False)
    supplier_address = db.Column(db.Text, nullable=False)
    supplier_gstin = db.Column(db.String(20), nullable=False)
    customer_name = db.Column(db.String(150), nullable=False)
    customer_address = db.Column(db.Text, nullable=False)
    customer_gstin = db.Column(db.String(20))
    is_interstate = db.Column(db.Boolean, default=False, nullable=False)
    
    total_taxable = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    cgst_total = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    sgst_total = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    igst_total = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    grand_total = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    status = db.Column(db.String(20), default='posted', nullable=False)  # posted, cancelled
    
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    items = db.relationship('InvoiceItem', backref='invoice', lazy='dynamic', cascade='all, delete-orphan')
    credit_notes = db.relationship('CreditNote', backref='invoice', lazy='dynamic')
    allocations = db.relationship('PaymentAllocation', backref='invoice', lazy='dynamic')
    dispatches = db.relationship('Dispatch', backref='invoice', lazy='dynamic')
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    
    @property
    def total_allocated(self):
        return sum(a.allocated_amount for a in self.allocations)
    
    @property
    def total_credits(self):
        return sum(cn.amount for cn in self.credit_notes)
    
    @property
    def outstanding_amount(self):
        return self.grand_total - self.total_allocated - self.total_credits
    
    @property
    def is_fully_paid(self):
        return self.outstanding_amount <= Decimal('0.00')
    
    def __repr__(self):
        return f"<Invoice {self.invoice_number} ({self.grand_total})>"


class InvoiceItem(db.Model):
    __tablename__ = 'invoice_items'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id', ondelete='CASCADE'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    hsn_code = db.Column(db.String(20), nullable=False)
    quantity = db.Column(db.Numeric(12, 2), nullable=False)
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)
    taxable_value = db.Column(db.Numeric(12, 2), nullable=False)
    gst_rate = db.Column(db.Numeric(5, 2), default=Decimal('5.00'), nullable=False)
    cgst_rate = db.Column(db.Numeric(5, 2), default=Decimal('0.00'), nullable=False)
    cgst_amount = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    sgst_rate = db.Column(db.Numeric(5, 2), default=Decimal('0.00'), nullable=False)
    sgst_amount = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    igst_rate = db.Column(db.Numeric(5, 2), default=Decimal('0.00'), nullable=False)
    igst_amount = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    total_amount = db.Column(db.Numeric(12, 2), nullable=False)
    
    def __repr__(self):
        return f"<InvoiceItem Inv#{self.invoice_id} Prod#{self.product_id}: {self.quantity}>"


class CreditNote(db.Model):
    __tablename__ = 'credit_notes'
    
    id = db.Column(db.Integer, primary_key=True)
    credit_note_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    credit_date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    reason = db.Column(db.String(255), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    
    def __repr__(self):
        return f"<CreditNote {self.credit_note_number} amount={self.amount}>"
