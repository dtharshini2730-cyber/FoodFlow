from datetime import datetime
from decimal import Decimal
from app import db


class ProductionRun(db.Model):
    __tablename__ = 'production_runs'
    
    id = db.Column(db.Integer, primary_key=True)
    run_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    production_date = db.Column(db.Date, nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    bom_version_id = db.Column(db.Integer, db.ForeignKey('bom_versions.id'), nullable=False)
    batch_count = db.Column(db.Numeric(10, 2), default=Decimal('1.00'), nullable=False)
    expected_output = db.Column(db.Numeric(12, 2), nullable=False)
    actual_output = db.Column(db.Numeric(12, 2), nullable=False)  # Good output
    yield_variance_pct = db.Column(db.Numeric(6, 2), default=Decimal('0.00'), nullable=False)
    yield_variance_alert = db.Column(db.Boolean, default=False, nullable=False)
    
    # Cost Breakdown
    total_material_cost = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    total_packaging_cost = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    labour_cost = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    gas_cost = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    power_cost = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    other_overhead_cost = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    total_production_cost = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    cost_per_packet = db.Column(db.Numeric(12, 4), default=Decimal('0.0000'), nullable=False)
    
    status = db.Column(db.String(30), default='completed', nullable=False)  # completed, reversed
    remarks = db.Column(db.Text)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    product = db.relationship('Product', foreign_keys=[product_id])
    bom_version = db.relationship('BOMVersion', foreign_keys=[bom_version_id])
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    
    consumptions = db.relationship('ProductionConsumption', backref='production_run', lazy='dynamic', cascade='all, delete-orphan')
    outputs = db.relationship('ProductionOutput', backref='production_run', lazy='dynamic', cascade='all, delete-orphan')
    overheads = db.relationship('ProductionOverhead', backref='production_run', lazy='dynamic', cascade='all, delete-orphan')
    
    @property
    def gross_contribution_per_packet(self):
        """Selling price before tax minus cost per packet."""
        if self.product and self.cost_per_packet:
            return self.product.selling_price - self.cost_per_packet
        return Decimal('0.00')
    
    @property
    def gross_margin_percentage(self):
        """Gross margin % = (Gross contribution / Selling price) * 100."""
        if self.product and self.product.selling_price > 0:
            return (self.gross_contribution_per_packet / self.product.selling_price) * Decimal('100.0')
        return Decimal('0.00')
    
    def __repr__(self):
        return f"<ProductionRun {self.run_number}: {self.actual_output} pkts>"


class ProductionConsumption(db.Model):
    __tablename__ = 'production_consumptions'
    
    id = db.Column(db.Integer, primary_key=True)
    production_run_id = db.Column(db.Integer, db.ForeignKey('production_runs.id', ondelete='CASCADE'), nullable=False)
    item_type = db.Column(db.String(30), nullable=False)  # raw_material, packaging_material
    item_id = db.Column(db.Integer, nullable=False)
    planned_quantity = db.Column(db.Numeric(12, 3), nullable=False)
    actual_quantity = db.Column(db.Numeric(12, 3), nullable=False)
    damaged_quantity = db.Column(db.Numeric(12, 3), default=Decimal('0.000'), nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    variance_pct = db.Column(db.Numeric(6, 2), default=Decimal('0.00'), nullable=False)
    variance_alert = db.Column(db.Boolean, default=False, nullable=False)
    unit_cost = db.Column(db.Numeric(12, 4), default=Decimal('0.0000'), nullable=False)
    total_cost = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    
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
        return f"<ProductionConsumption {self.item_type} #{self.item_id}: {self.actual_quantity}>"


class ProductionOutput(db.Model):
    __tablename__ = 'production_outputs'
    
    id = db.Column(db.Integer, primary_key=True)
    production_run_id = db.Column(db.Integer, db.ForeignKey('production_runs.id', ondelete='CASCADE'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    good_quantity = db.Column(db.Numeric(12, 2), nullable=False)
    damaged_quantity = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    unit = db.Column(db.String(20), default='packets', nullable=False)
    
    product = db.relationship('Product')


class ProductionOverhead(db.Model):
    __tablename__ = 'production_overheads'
    
    id = db.Column(db.Integer, primary_key=True)
    production_run_id = db.Column(db.Integer, db.ForeignKey('production_runs.id', ondelete='CASCADE'), nullable=False)
    overhead_type = db.Column(db.String(50), nullable=False)  # labour, gas, power, other
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    remarks = db.Column(db.String(255))
