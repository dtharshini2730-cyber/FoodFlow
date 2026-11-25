from datetime import datetime
from decimal import Decimal
from app import db


class Purchase(db.Model):
    __tablename__ = 'purchases'
    
    id = db.Column(db.Integer, primary_key=True)
    purchase_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    purchase_date = db.Column(db.Date, nullable=False)
    supplier_invoice_no = db.Column(db.String(100), nullable=False)
    total_taxable_amount = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    total_tax_amount = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    grand_total = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    status = db.Column(db.String(20), default='posted', nullable=False)  # posted
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    items = db.relationship('PurchaseItem', backref='purchase', lazy='dynamic', cascade='all, delete-orphan')
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    
    def __repr__(self):
        return f"<Purchase {self.purchase_number}>"


class PurchaseItem(db.Model):
    __tablename__ = 'purchase_items'
    
    id = db.Column(db.Integer, primary_key=True)
    purchase_id = db.Column(db.Integer, db.ForeignKey('purchases.id', ondelete='CASCADE'), nullable=False)
    item_type = db.Column(db.String(30), nullable=False)  # 'raw_material' or 'packaging_material'
    item_id = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Numeric(12, 3), nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    unit_rate = db.Column(db.Numeric(12, 4), nullable=False)
    tax_rate = db.Column(db.Numeric(5, 2), default=Decimal('5.00'), nullable=False)
    tax_amount = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    total_amount = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    
    def get_item_name(self):
        if self.item_type == 'raw_material':
            from app.models.master import RawMaterial
            rm = RawMaterial.query.get(self.item_id)
            return rm.name if rm else f"RawMaterial #{self.item_id}"
        else:
            from app.models.master import PackagingMaterial
            pm = PackagingMaterial.query.get(self.item_id)
            return pm.name if pm else f"PackagingMaterial #{self.item_id}"
    
    def __repr__(self):
        return f"<PurchaseItem {self.item_type} #{self.item_id}: {self.quantity} @ {self.unit_rate}>"
