import os
from decimal import Decimal
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from config import config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'
csrf = CSRFProtect()


def format_inr(value):
    """Format numbers into Indian numbering format (e.g. ₹1,25,000.00)."""
    if value is None:
        return '₹0.00'
    try:
        dec = Decimal(str(value))
    except Exception:
        return f"₹{value}"
    
    is_negative = dec < 0
    dec = abs(dec)
    
    parts = f"{dec:.2f}".split('.')
    integer_part = parts[0]
    decimal_part = parts[1]
    
    if len(integer_part) > 3:
        last_three = integer_part[-3:]
        remaining = integer_part[:-3]
        
        # Group remaining digits by 2
        groups = []
        while len(remaining) > 2:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            groups.insert(0, remaining)
        
        formatted_int = ','.join(groups) + ',' + last_three
    else:
        formatted_int = integer_part
    
    prefix = '-₹' if is_negative else '₹'
    return f"{prefix}{formatted_int}.{decimal_part}"


def format_date(value, fmt='%d-%m-%Y'):
    """Format date to DD-MM-YYYY."""
    if not value:
        return ''
    try:
        return value.strftime(fmt)
    except Exception:
        return str(value)


def format_qty(value, unit=''):
    """Format quantity cleanly with up to 3 decimals without trailing zeroes."""
    if value is None:
        return '0'
    try:
        dec = Decimal(str(value))
        # Format with 3 decimals and strip trailing zeroes
        formatted = f"{dec:.3f}".rstrip('0').rstrip('.')
        if not formatted:
            formatted = '0'
        return f"{formatted} {unit}".strip() if unit else formatted
    except Exception:
        return str(value)


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    
    # Register custom Jinja filters
    app.jinja_env.filters['inr'] = format_inr
    app.jinja_env.filters['date_in'] = format_date
    app.jinja_env.filters['qty'] = format_qty
    
    # Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.master import master_bp
    from app.routes.bom import bom_bp
    from app.routes.purchases import purchases_bp
    from app.routes.inventory import inventory_bp
    from app.routes.production import production_bp
    from app.routes.orders import orders_bp
    from app.routes.invoices import invoices_bp
    from app.routes.dispatch import dispatch_bp
    from app.routes.payments import payments_bp
    from app.routes.reports import reports_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(master_bp, url_prefix='/master')
    app.register_blueprint(bom_bp, url_prefix='/bom')
    app.register_blueprint(purchases_bp, url_prefix='/purchases')
    app.register_blueprint(inventory_bp, url_prefix='/inventory')
    app.register_blueprint(production_bp, url_prefix='/production')
    app.register_blueprint(orders_bp, url_prefix='/orders')
    app.register_blueprint(invoices_bp, url_prefix='/invoices')
    app.register_blueprint(dispatch_bp, url_prefix='/dispatch')
    app.register_blueprint(payments_bp, url_prefix='/payments')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    
    # Error Handlers
    from flask import render_template
    
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        app.logger.error(f"Internal Server Error: {e}")
        return render_template('errors/500.html'), 500
        
    return app
