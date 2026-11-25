from datetime import datetime
from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.sales import SalesOrder, SalesOrderItem
from app.models.master import Customer, Product
from app.services.order_service import OrderService
from app.services.stock_service import StockService
from app.utils.decorators import roles_required

orders_bp = Blueprint('orders', __name__)


@orders_bp.route('/')
@login_required
def index():
    # Role-based filtering: Salesman sees only own orders
    if current_user.has_role('salesman') and not (current_user.has_role('owner') or current_user.has_role('admin')):
        orders_list = SalesOrder.query.filter_by(salesman_id=current_user.id).order_by(SalesOrder.created_at.desc()).all()
    else:
        orders_list = SalesOrder.query.order_by(SalesOrder.created_at.desc()).all()
        
    return render_template('orders/index.html', orders=orders_list)


@orders_bp.route('/new', methods=['GET', 'POST'])
@login_required
@roles_required('owner', 'admin', 'salesman')
def new_order():
    if request.method == 'POST':
        customer_id = request.form.get('customer_id', type=int)
        remarks = request.form.get('remarks', '').strip()
        idempotency_key = request.form.get('idempotency_key')
        
        product_ids = request.form.getlist('product_id[]')
        quantities = request.form.getlist('quantity[]')
        
        items = []
        for i in range(len(product_ids)):
            if not product_ids[i] or not quantities[i]:
                continue
            qty = Decimal(quantities[i])
            if qty > Decimal('0'):
                items.append({
                    'product_id': int(product_ids[i]),
                    'quantity': qty
                })
                
        if not items:
            flash('Please select at least one product with quantity > 0.', 'danger')
            return redirect(url_for('orders.new_order'))
            
        order_data = {
            'customer_id': customer_id,
            'remarks': remarks,
            'idempotency_key': idempotency_key,
            'items': items
        }
        
        try:
            order = OrderService.create_sales_order(order_data, current_user.id)
            db.session.commit()
            flash(f"Order #{order.order_number} submitted successfully for ₹{order.total_amount:.2f}.", 'success')
            return redirect(url_for('orders.view', id=order.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Error submitting order: {str(e)}", 'danger')
            
    # Load customers
    if current_user.has_role('salesman') and not (current_user.has_role('owner') or current_user.has_role('admin')):
        customers = Customer.query.filter_by(is_active=True, assigned_salesman_id=current_user.id).all()
        # Fallback to all customers if none explicitly assigned
        if not customers:
            customers = Customer.query.filter_by(is_active=True).all()
    else:
        customers = Customer.query.filter_by(is_active=True).all()
        
    products = Product.query.filter_by(is_active=True).all()
    # Enrich products with available stock
    product_stock = {}
    for p in products:
        product_stock[p.id] = p.get_current_stock()
        
    return render_template(
        'orders/new.html',
        customers=customers,
        products=products,
        product_stock=product_stock
    )


@orders_bp.route('/<int:id>')
@login_required
def view(id):
    order = SalesOrder.query.get_or_404(id)
    
    # Permission check: Salesman can only view their own order
    if current_user.has_role('salesman') and not (current_user.has_role('owner') or current_user.has_role('admin')):
        if order.salesman_id != current_user.id:
            flash('You do not have permission to view this order.', 'danger')
            return redirect(url_for('orders.index'))
            
    stock_check = OrderService.check_order_stock_availability(order.id)
    return render_template('orders/view.html', order=order, stock_check=stock_check)


@orders_bp.route('/<int:id>/approve', methods=['POST'])
@login_required
@roles_required('owner', 'admin')
def approve(id):
    order = SalesOrder.query.get_or_404(id)
    try:
        OrderService.approve_order(order.id, current_user.id)
        db.session.commit()
        flash(f"Order {order.order_number} approved successfully. You may now generate a GST Invoice.", 'success')
    except Exception as e:
        db.session.rollback()
        flash(f"Error approving order: {str(e)}", 'danger')
    return redirect(url_for('orders.view', id=id))


@orders_bp.route('/<int:id>/reject', methods=['POST'])
@login_required
@roles_required('owner', 'admin')
def reject(id):
    reason = request.form.get('reason', '').strip()
    if not reason:
        flash('Rejection reason is mandatory.', 'danger')
        return redirect(url_for('orders.view', id=id))
        
    try:
        OrderService.reject_order(id, reason, current_user.id)
        db.session.commit()
        flash(f"Order rejected.", 'info')
    except Exception as e:
        db.session.rollback()
        flash(f"Error rejecting order: {str(e)}", 'danger')
    return redirect(url_for('orders.view', id=id))
