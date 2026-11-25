import json
from datetime import datetime
from app import db


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    action = db.Column(db.String(50), nullable=False, index=True)  # CREATE, UPDATE, APPROVE, REJECT, POST, DISPATCH, REVERSE
    module = db.Column(db.String(50), nullable=False, index=True)  # Orders, Purchases, Production, Invoices, Dispatch, Payments, Stock
    record_id = db.Column(db.Integer, nullable=True)
    old_values = db.Column(db.Text, nullable=True)  # JSON formatted
    new_values = db.Column(db.Text, nullable=True)  # JSON formatted
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    
    user = db.relationship('User', foreign_keys=[user_id])
    
    @classmethod
    def log(cls, user_id, action, module, record_id=None, old_values=None, new_values=None, description='', ip_address=None):
        entry = cls(
            user_id=user_id,
            action=action,
            module=module,
            record_id=record_id,
            old_values=json.dumps(old_values, default=str) if old_values else None,
            new_values=json.dumps(new_values, default=str) if new_values else None,
            description=description,
            ip_address=ip_address
        )
        db.session.add(entry)
        return entry
    
    def __repr__(self):
        return f"<AuditLog {self.action} on {self.module} #{self.record_id} by User#{self.user_id}>"


class SystemSetting(db.Model):
    __tablename__ = 'system_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(255))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @classmethod
    def get_value(cls, key, default=None):
        setting = cls.query.filter_by(key=key).first()
        return setting.value if setting else default
    
    @classmethod
    def set_value(cls, key, value, description=None):
        setting = cls.query.filter_by(key=key).first()
        if not setting:
            setting = cls(key=key, value=str(value), description=description)
            db.session.add(setting)
        else:
            setting.value = str(value)
            if description:
                setting.description = description
        return setting
    
    def __repr__(self):
        return f"<SystemSetting {self.key}={self.value}>"
