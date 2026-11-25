from datetime import datetime, date, timedelta
from decimal import Decimal
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from sqlalchemy import func
from app import db
from app.models.sales import SalesOrder
from app.models.billing import Invoice, InvoiceItem
from app.models.production import ProductionRun
from app.models.master import Product, RawMaterial, PackagingMaterial, Customer
from app.models.payment import Payment
from app.services.stock_service import StockService
from app.services.payment_service import PaymentService

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    today = date.today()
    
    # 1. Summary Metrics
    todays_orders_count = SalesOrder.query.filter(SalesOrder.order_date == today).count()
    awaiting_approval_count = SalesOrder.query.filter(SalesOrder.status.in_(['Submitted', 'Under Review'])).count()
    
    todays_sales = db.session.query(func.coalesce(func.sum(Invoice.grand_total), 0)).filter(
        Invoice.invoice_date == today,
        Invoice.status == 'posted'
    ).scalar()
    
    # Count total available packets across all active products
    total_finished_pkts = Decimal('0')
    active_products = Product.query.filter_by(is_active=True).all()
    for p in active_products:
        total_finished_pkts += p.get_current_stock()
        
    # Low stock alerts for raw materials and packaging
    low_stock_materials = []
    for rm in RawMaterial.query.filter_by(is_active=True).all():
        stock = rm.get_current_stock()
        if stock <= rm.reorder_level:
            low_stock_materials.append({
                'name': rm.name,
                'type': 'Raw Material',
                'current': stock,
                'reorder': rm.reorder_level,
                'unit': rm.base_unit
            })
    for pm in PackagingMaterial.query.filter_by(is_active=True).all():
        stock = pm.get_current_stock()
        if stock <= pm.reorder_level:
            low_stock_materials.append({
                'name': pm.name,
                'type': 'Packaging',
                'current': stock,
                'reorder': pm.reorder_level,
                'unit': pm.unit
            })
            
    # Production completed today
    todays_production = db.session.query(func.coalesce(func.sum(ProductionRun.actual_output), 0)).filter(
        ProductionRun.production_date == today,
        ProductionRun.status == 'completed'
    ).scalar()
    
    # Customer outstanding amount
    total_outstanding = Decimal('0.00')
    for inv in Invoice.query.filter_by(status='posted').all():
        total_outstanding += inv.outstanding_amount
        
    # Variance alerts (runs with yield alert or consumption alert)
    variance_runs = ProductionRun.query.filter(
        ProductionRun.yield_variance_alert == True
    ).order_by(ProductionRun.production_date.desc()).limit(5).all()
    
    # Recent orders
    if current_user.has_role('salesman') and not (current_user.has_role('owner') or current_user.has_role('admin')):
        recent_orders = SalesOrder.query.filter_by(salesman_id=current_user.id).order_by(SalesOrder.created_at.desc()).limit(6).all()
    else:
        recent_orders = SalesOrder.query.order_by(SalesOrder.created_at.desc()).limit(6).all()
        
    recent_runs = ProductionRun.query.order_by(ProductionRun.production_date.desc(), ProductionRun.id.desc()).limit(5).all()
    
    # Pending payments / unpaid invoices
    unpaid_invoices = [inv for inv in Invoice.query.filter_by(status='posted').order_by(Invoice.invoice_date.asc()).all() if inv.outstanding_amount > 0][:5]
    
    # Chart Data: Monthly Sales (Past 6 months)
    monthly_sales_labels = []
    monthly_sales_values = []
    for i in range(5, -1, -1):
        target_month = today.month - i
        target_year = today.year
        while target_month <= 0:
            target_month += 12
            target_year -= 1
        month_name = datetime(target_year, target_month, 1).strftime('%b %Y')
        monthly_sales_labels.append(month_name)
        
        # Calculate sales for this month
        month_total = db.session.query(func.coalesce(func.sum(Invoice.grand_total), 0)).filter(
            func.extract('year', Invoice.invoice_date) == target_year,
            func.extract('month', Invoice.invoice_date) == target_month,
            Invoice.status == 'posted'
        ).scalar()
        monthly_sales_values.append(float(month_total))
        
    # Chart Data: Product-wise Sales
    prod_sales = db.session.query(
        Product.name,
        func.coalesce(func.sum(InvoiceItem.total_amount), 0).label('total')
    ).join(InvoiceItem, InvoiceItem.product_id == Product.id) \
     .join(Invoice, Invoice.id == InvoiceItem.invoice_id) \
     .filter(Invoice.status == 'posted') \
     .group_by(Product.name).limit(5).all()
     
    product_chart_labels = [p[0] for p in prod_sales] if prod_sales else ["No sales yet"]
    product_chart_values = [float(p[1]) for p in prod_sales] if prod_sales else [0]
    
    return render_template(
        'dashboard/index.html',
        todays_orders_count=todays_orders_count,
        awaiting_approval_count=awaiting_approval_count,
        todays_sales=todays_sales,
        total_finished_pkts=total_finished_pkts,
        low_stock_materials=low_stock_materials,
        todays_production=todays_production,
        total_outstanding=total_outstanding,
        variance_runs=variance_runs,
        recent_orders=recent_orders,
        recent_runs=recent_runs,
        unpaid_invoices=unpaid_invoices,
        monthly_sales_labels=monthly_sales_labels,
        monthly_sales_values=monthly_sales_values,
        product_chart_labels=product_chart_labels,
        product_chart_values=product_chart_values
    )
