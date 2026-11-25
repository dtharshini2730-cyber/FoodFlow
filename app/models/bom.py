from datetime import datetime
from decimal import Decimal
from app import db


class ProductBOM(db.Model):
    __tablename__ = 'product_boms'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='CASCADE'), nullable=False, unique=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    versions = db.relationship('BOMVersion', backref='bom', lazy='dynamic', cascade='all, delete-orphan')
    
    @property
    def active_version(self):
        return self.versions.filter_by(is_active=True).order_by(BOMVersion.version_number.desc()).first()
    
    def __repr__(self):
        return f"<ProductBOM product_id={self.product_id}>"


class BOMVersion(db.Model):
    __tablename__ = 'bom_versions'
    
    id = db.Column(db.Integer, primary_key=True)
    bom_id = db.Column(db.Integer, db.ForeignKey('product_boms.id', ondelete='CASCADE'), nullable=False)
    version_number = db.Column(db.Integer, default=1, nullable=False)
    batch_size = db.Column(db.Numeric(10, 2), default=Decimal('1.00'), nullable=False)  # e.g. 1 batch
    expected_output = db.Column(db.Numeric(12, 2), nullable=False)  # e.g. 200 packets
    expected_yield_pct = db.Column(db.Numeric(5, 2), default=Decimal('100.00'), nullable=False)
    notes = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    items = db.relationship('BOMItem', backref='bom_version', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<BOMVersion bom_id={self.bom_id} v={self.version_number}>"


class BOMItem(db.Model):
    __tablename__ = 'bom_items'
    
    id = db.Column(db.Integer, primary_key=True)
    bom_version_id = db.Column(db.Integer, db.ForeignKey('bom_versions.id', ondelete='CASCADE'), nullable=False)
    item_type = db.Column(db.String(30), nullable=False)  # 'raw_material' or 'packaging_material'
    item_id = db.Column(db.Integer, nullable=False)
    standard_quantity = db.Column(db.Numeric(12, 3), nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    notes = db.Column(db.String(255))
    
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
        return f"<BOMItem {self.item_type} #{self.item_id}: {self.standard_quantity} {self.unit}>"
