from datetime import datetime
from decimal import Decimal
from app import db


class Dispatch(db.Model):
    __tablename__ = 'dispatches'
    
    id = db.Column(db.Integer, primary_key=True)
    dispatch_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    sales_order_id = db.Column(db.Integer, db.ForeignKey('sales_orders.id'), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=True)
    dispatch_date = db.Column(db.Date, nullable=False)
    vehicle_no = db.Column(db.String(50))
    remarks = db.Column(db.Text)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    items = db.relationship('DispatchItem', backref='dispatch', lazy='dynamic', cascade='all, delete-orphan')
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    
    def __repr__(self):
        return f"<Dispatch {self.dispatch_number}>"


class DispatchItem(db.Model):
    __tablename__ = 'dispatch_items'
    
    id = db.Column(db.Integer, primary_key=True)
    dispatch_id = db.Column(db.Integer, db.ForeignKey('dispatches.id', ondelete='CASCADE'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Numeric(12, 2), nullable=False)
    unit = db.Column(db.String(20), default='packets', nullable=False)
    
    product = db.relationship('Product')
    
    def __repr__(self):
        return f"<DispatchItem DSP#{self.dispatch_id} Prod#{self.product_id}: {self.quantity}>"
