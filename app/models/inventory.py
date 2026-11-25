from datetime import datetime
from decimal import Decimal
from app import db


class StockLedger(db.Model):
    __tablename__ = 'stock_ledger'
    
    id = db.Column(db.Integer, primary_key=True)
    item_type = db.Column(db.String(30), nullable=False, index=True)  # raw_material, packaging_material, finished_good
    item_id = db.Column(db.Integer, nullable=False, index=True)
    movement_date = db.Column(db.Date, nullable=False, index=True)
    movement_type = db.Column(db.String(50), nullable=False)  # opening_stock, purchase_receipt, production_issue, production_output, production_damage, sales_dispatch, sales_return, stock_adjustment
    quantity = db.Column(db.Numeric(12, 3), nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    direction = db.Column(db.String(10), nullable=False)  # IN or OUT
    source_document_type = db.Column(db.String(50), nullable=False)  # Purchase, ProductionRun, Dispatch, Adjustment, Opening
    source_document_id = db.Column(db.Integer, nullable=True)
    unit_rate = db.Column(db.Numeric(12, 4), default=Decimal('0.0000'), nullable=False)
    total_value = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), nullable=False)
    running_balance = db.Column(db.Numeric(12, 3), default=Decimal('0.000'), nullable=False)
    batch_reference = db.Column(db.String(100), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    
    def get_item_name(self):
        if self.item_type == 'raw_material':
            from app.models.master import RawMaterial
            item = RawMaterial.query.get(self.item_id)
            return item.name if item else f"RM #{self.item_id}"
        elif self.item_type == 'packaging_material':
            from app.models.master import PackagingMaterial
            item = PackagingMaterial.query.get(self.item_id)
            return item.name if item else f"PM #{self.item_id}"
        elif self.item_type == 'finished_good':
            from app.models.master import Product
            item = Product.query.get(self.item_id)
            return item.name if item else f"FG #{self.item_id}"
        return f"Item #{self.item_id}"
    
    def __repr__(self):
        return f"<StockLedger {self.item_type} #{self.item_id} {self.direction} {self.quantity} {self.unit}>"


class StockAdjustment(db.Model):
    __tablename__ = 'stock_adjustments'
    
    id = db.Column(db.Integer, primary_key=True)
    item_type = db.Column(db.String(30), nullable=False)
    item_id = db.Column(db.Integer, nullable=False)
    adjustment_date = db.Column(db.Date, nullable=False)
    quantity = db.Column(db.Numeric(12, 3), nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    direction = db.Column(db.String(10), nullable=False)  # IN or OUT
    reason = db.Column(db.String(255), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    
    def __repr__(self):
        return f"<StockAdjustment {self.item_type} #{self.item_id}: {self.direction} {self.quantity}>"


class StockBatch(db.Model):
    __tablename__ = 'stock_batches'
    
    id = db.Column(db.Integer, primary_key=True)
    batch_number = db.Column(db.String(100), unique=True, nullable=False)
    item_type = db.Column(db.String(30), nullable=False)
    item_id = db.Column(db.Integer, nullable=False)
    production_run_id = db.Column(db.Integer, nullable=True)
    initial_quantity = db.Column(db.Numeric(12, 3), nullable=False)
    current_quantity = db.Column(db.Numeric(12, 3), nullable=False)
    manufacturing_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<StockBatch {self.batch_number}>"
