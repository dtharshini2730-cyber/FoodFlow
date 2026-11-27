from datetime import datetime, date, timedelta
from decimal import Decimal
from flask import Blueprint, render_template, redirect, url_for
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
from app.services.report_service import ReportService

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    user_roles = [r.name for r in current_user.roles]
    
    if 'owner' in user_roles:
        return owner_dashboard()
    elif 'admin' in user_roles:
        return admin_dashboard()
    elif 'salesman' in user_roles:
        return salesman_dashboard()
    elif 'production' in user_roles:
        return production_dashboard()
    elif 'auditor' in user_roles:
        return auditor_dashboard()
    else:
        return admin_dashboard()


def owner_dashboard():
    today = date.today()
    
    # 1. Cards
    total_sales = db.session.query(func.coalesce(func.sum(Invoice.grand_total), 0)).filter(
        Invoice.status == 'posted'
    ).scalar()
    
    total_orders = SalesOrder.query.count()
    pending_orders_count = SalesOrder.query.filter(SalesOrder.status.in_(['Submitted', 'Under Review'])).count()
    
    # Finished Goods Stock
    total_finished_pkts = Decimal('0')
    for p in Product.query.filter_by(is_active=True).all():
        total_finished_pkts += p.get_current_stock()
        
    # Raw Material Stock Alerts
    raw_alerts = []
    for rm in RawMaterial.query.filter_by(is_active=True).all():
        stk = rm.get_current_stock()
        if stk <= rm.reorder_level:
            raw_alerts.append({
                'name': rm.name,
                'current': stk,
                'reorder': rm.reorder_level,
                'unit': rm.base_unit
            })
    for pm in PackagingMaterial.query.filter_by(is_active=True).all():
        stk = pm.get_current_stock()
        if stk <= pm.reorder_level:
            raw_alerts.append({
                'name': pm.name,
                'current': stk,
                'reorder': pm.reorder_level,
                'unit': pm.unit
            })
            
    # Outstanding Payments
    total_outstanding = Decimal('0.00')
    for inv in Invoice.query.filter_by(status='posted').all():
        total_outstanding += inv.outstanding_amount
        
    # Production Performance & Cost
    completed_runs = ProductionRun.query.filter_by(status='completed').all()
    total_production_cost = sum(r.total_production_cost for r in completed_runs)
    avg_yield_variance = (sum(r.yield_variance_pct for r in completed_runs) / len(completed_runs)) if completed_runs else Decimal('0.00')
    
    # 2. Charts
    monthly_sales_labels = []
    monthly_sales_values = []
    monthly_prod_cost_values = []
    
    for i in range(5, -1, -1):
        target_month = today.month - i
        target_year = today.year
        while target_month <= 0:
            target_month += 12
            target_year -= 1
        m_name = datetime(target_year, target_month, 1).strftime('%b %Y')
        monthly_sales_labels.append(m_name)
        
        s_val = db.session.query(func.coalesce(func.sum(Invoice.grand_total), 0)).filter(
            func.extract('year', Invoice.invoice_date) == target_year,
            func.extract('month', Invoice.invoice_date) == target_month,
            Invoice.status == 'posted'
        ).scalar()
        monthly_sales_values.append(float(s_val))
        
        c_val = db.session.query(func.coalesce(func.sum(ProductionRun.total_production_cost), 0)).filter(
            func.extract('year', ProductionRun.production_date) == target_year,
            func.extract('month', ProductionRun.production_date) == target_month,
            ProductionRun.status == 'completed'
        ).scalar()
        monthly_prod_cost_values.append(float(c_val))
        
    # Outstanding Receivables Trend by Customer
    cust_dues = {}
    for inv in Invoice.query.filter_by(status='posted').all():
        if inv.outstanding_amount > Decimal('0.00'):
            c_name = inv.customer.name
            cust_dues[c_name] = cust_dues.get(c_name, Decimal('0.00')) + inv.outstanding_amount
            
    sorted_dues = sorted(cust_dues.items(), key=lambda x: x[1], reverse=True)[:5]
    due_labels = [c[0] for c in sorted_dues] if sorted_dues else ["No outstanding dues"]
    due_values = [float(c[1]) for c in sorted_dues] if sorted_dues else [0]
    
    # 3. Alerts
    high_variance_runs = ProductionRun.query.filter_by(yield_variance_alert=True).order_by(ProductionRun.production_date.desc()).limit(5).all()
    pending_orders_list = SalesOrder.query.filter(SalesOrder.status.in_(['Submitted', 'Under Review'])).order_by(SalesOrder.order_date.desc()).limit(5).all()
    overdue_invoices = [inv for inv in Invoice.query.filter_by(status='posted').all() if inv.outstanding_amount > 0 and (today - inv.invoice_date).days > 30][:5]
    
    return render_template(
        'dashboard/owner.html',
        total_sales=total_sales,
        total_orders=total_orders,
        pending_orders_count=pending_orders_count,
        total_finished_pkts=total_finished_pkts,
        raw_material_alerts_count=len(raw_alerts),
        raw_alerts=raw_alerts,
        total_outstanding=total_outstanding,
        avg_yield_variance=avg_yield_variance,
        total_production_cost=total_production_cost,
        monthly_sales_labels=monthly_sales_labels,
        monthly_sales_values=monthly_sales_values,
        monthly_prod_cost_values=monthly_prod_cost_values,
        due_labels=due_labels,
        due_values=due_values,
        high_variance_runs=high_variance_runs,
        pending_orders_list=pending_orders_list,
        overdue_invoices=overdue_invoices
    )


def admin_dashboard():
    today = date.today()
    
    new_orders_count = SalesOrder.query.filter(SalesOrder.order_date == today).count()
    awaiting_approval = SalesOrder.query.filter(SalesOrder.status.in_(['Submitted', 'Under Review'])).count()
    ready_dispatch = SalesOrder.query.filter(SalesOrder.status.in_(['Approved', 'Invoiced'])).count()
    
    todays_sales = db.session.query(func.coalesce(func.sum(Invoice.grand_total), 0)).filter(
        Invoice.invoice_date == today,
        Invoice.status == 'posted'
    ).scalar()
    
    pending_payments = Decimal('0.00')
    for inv in Invoice.query.filter_by(status='posted').all():
        pending_payments += inv.outstanding_amount
        
    low_stock_count = 0
    for rm in RawMaterial.query.filter_by(is_active=True).all():
        if rm.get_current_stock() <= rm.reorder_level:
            low_stock_count += 1
    for pm in PackagingMaterial.query.filter_by(is_active=True).all():
        if pm.get_current_stock() <= pm.reorder_level:
            low_stock_count += 1
            
    recent_orders = SalesOrder.query.order_by(SalesOrder.created_at.desc()).limit(7).all()
    unpaid_invoices = [inv for inv in Invoice.query.filter_by(status='posted').order_by(Invoice.invoice_date.asc()).all() if inv.outstanding_amount > 0][:5]
    
    return render_template(
        'dashboard/admin.html',
        new_orders_count=new_orders_count,
        awaiting_approval=awaiting_approval,
        ready_dispatch=ready_dispatch,
        todays_sales=todays_sales,
        pending_payments=pending_payments,
        low_stock_count=low_stock_count,
        recent_orders=recent_orders,
        unpaid_invoices=unpaid_invoices
    )


def salesman_dashboard():
    # Only current salesman's metrics
    my_orders = SalesOrder.query.filter_by(salesman_id=current_user.id).order_by(SalesOrder.created_at.desc()).all()
    
    my_total_orders = len(my_orders)
    my_pending_orders = len([o for o in my_orders if o.status in ['Submitted', 'Under Review']])
    my_approved_orders = len([o for o in my_orders if o.status == 'Approved'])
    my_dispatched_orders = len([o for o in my_orders if o.status in ['Partially Dispatched', 'Dispatched']])
    my_sales_summary = sum(o.total_amount for o in my_orders)
    
    # Active products with current stock in factory
    products = Product.query.filter_by(is_active=True).all()
    catalog = []
    for p in products:
        catalog.append({
            'name': p.name,
            'sku': p.sku,
            'pack_size': p.pack_size,
            'price': p.selling_price,
            'available_stock': p.get_current_stock()
        })
        
    return render_template(
        'dashboard/salesman.html',
        my_total_orders=my_total_orders,
        my_pending_orders=my_pending_orders,
        my_approved_orders=my_approved_orders,
        my_dispatched_orders=my_dispatched_orders,
        my_sales_summary=my_sales_summary,
        recent_orders=my_orders[:7],
        catalog=catalog
    )


def production_dashboard():
    today = date.today()
    
    todays_production = db.session.query(func.coalesce(func.sum(ProductionRun.actual_output), 0)).filter(
        ProductionRun.production_date == today,
        ProductionRun.status == 'completed'
    ).scalar()
    
    completed_runs = ProductionRun.query.filter_by(status='completed').all()
    total_planned = sum(r.expected_output for r in completed_runs)
    total_actual = sum(r.actual_output for r in completed_runs)
    
    # Finished goods produced
    fg_produced_total = total_actual
    
    # Raw materials inventory status
    materials = []
    avail_count = 0
    for rm in RawMaterial.query.filter_by(is_active=True).all():
        stk = rm.get_current_stock()
        is_ok = stk > rm.reorder_level
        if is_ok: avail_count += 1
        materials.append({
            'name': rm.name,
            'sku': rm.sku,
            'current': stk,
            'reorder': rm.reorder_level,
            'unit': rm.base_unit,
            'status': 'Optimal' if is_ok else 'Low Stock'
        })
        
    for pm in PackagingMaterial.query.filter_by(is_active=True).all():
        stk = pm.get_current_stock()
        is_ok = stk > pm.reorder_level
        if is_ok: avail_count += 1
        materials.append({
            'name': pm.name,
            'sku': pm.sku,
            'current': stk,
            'reorder': pm.reorder_level,
            'unit': pm.unit,
            'status': 'Optimal' if is_ok else 'Low Stock'
        })
        
    pending_runs = ProductionRun.query.order_by(ProductionRun.production_date.desc(), ProductionRun.id.desc()).limit(8).all()
    variance_alerts_count = ProductionRun.query.filter_by(yield_variance_alert=True).count()
    
    return render_template(
        'dashboard/production.html',
        todays_production=todays_production,
        total_planned=total_planned,
        total_actual=total_actual,
        avail_count=avail_count,
        total_materials=len(materials),
        fg_produced_total=fg_produced_total,
        pending_runs=pending_runs,
        variance_alerts_count=variance_alerts_count,
        materials=materials
    )


def auditor_dashboard():
    today = date.today()
    
    # Total Invoiced Amount
    total_invoiced = db.session.query(func.coalesce(func.sum(Invoice.grand_total), 0)).filter(
        Invoice.status == 'posted'
    ).scalar()
    
    # Total Payments Received
    total_payments = db.session.query(func.coalesce(func.sum(Payment.amount), 0)).scalar()
    
    # Outstanding Receivables
    total_outstanding = Decimal('0.00')
    for inv in Invoice.query.filter_by(status='posted').all():
        total_outstanding += inv.outstanding_amount
        
    # GST Summary
    gst_outward = ReportService.get_gst_outward_summary()
    total_gst = gst_outward['total_tax']
    
    # Monthly Sales Summary (Current Month)
    current_month_sales = db.session.query(func.coalesce(func.sum(Invoice.grand_total), 0)).filter(
        func.extract('year', Invoice.invoice_date) == today.year,
        func.extract('month', Invoice.invoice_date) == today.month,
        Invoice.status == 'posted'
    ).scalar()
    
    # Total Production Cost Summary
    total_production_cost = db.session.query(func.coalesce(func.sum(ProductionRun.total_production_cost), 0)).filter(
        ProductionRun.status == 'completed'
    ).scalar()
    
    # Customer Ageing
    ageing = ReportService.get_customer_ageing_report()
    
    # Recent Invoices
    recent_invoices = Invoice.query.filter_by(status='posted').order_by(Invoice.invoice_date.desc(), Invoice.id.desc()).limit(6).all()
    
    return render_template(
        'dashboard/auditor.html',
        total_invoiced=total_invoiced,
        total_payments=total_payments,
        total_outstanding=total_outstanding,
        total_gst=total_gst,
        current_month_sales=current_month_sales,
        total_production_cost=total_production_cost,
        gst_outward=gst_outward,
        ageing=ageing,
        recent_invoices=recent_invoices
    )
