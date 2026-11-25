from datetime import datetime
from decimal import Decimal
from app import db


class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    payment_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    payment_date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    payment_mode = db.Column(db.String(50), default='UPI', nullable=False)  # Cash, UPI, Bank Transfer, Cheque
    reference_number = db.Column(db.String(100))
    remarks = db.Column(db.Text)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    allocations = db.relationship('PaymentAllocation', backref='payment', lazy='dynamic', cascade='all, delete-orphan')
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    
    @property
    def total_allocated(self):
        return sum(a.allocated_amount for a in self.allocations)
    
    @property
    def unallocated_amount(self):
        return self.amount - self.total_allocated
    
    def __repr__(self):
        return f"<Payment {self.payment_number} amount={self.amount}>"


class PaymentAllocation(db.Model):
    __tablename__ = 'payment_allocations'
    
    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.id', ondelete='CASCADE'), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id', ondelete='CASCADE'), nullable=False)
    allocated_amount = db.Column(db.Numeric(12, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<PaymentAllocation Pay#{self.payment_id} Inv#{self.invoice_id}: {self.allocated_amount}>"
