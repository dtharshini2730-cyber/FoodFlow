from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models.dispatch import Dispatch
from app.models.sales import SalesOrder
from app.services.dispatch_service import DispatchService
from app.services.stock_service import InsufficientStockException
from app.utils.decorators import roles_required

dispatch_bp = Blueprint('dispatch', __name__)


@dispatch_bp.route('/')
@login_required
@roles_required('owner', 'admin', 'auditor')
def index():
    dispatches_list = Dispatch.query.order_by(Dispatch.dispatch_date.desc(), Dispatch.id.desc()).all()
    return render_template('dispatch/index.html', dispatches=dispatches_list)


@dispatch_bp.route('/new', methods=['GET'])
@login_required
@roles_required('owner', 'admin')
def select_order_for_dispatch():
    order_id = request.args.get('order_id')
    if order_id:
        return redirect(url_for('dispatch.new_dispatch', order_id=order_id))
    
    pending_orders = SalesOrder.query.filter(SalesOrder.status.in_(['Approved', 'Invoiced', 'Partially Dispatched'])).all()
    if not pending_orders:
        flash('No approved orders are currently awaiting dispatch.', 'info')
        return redirect(url_for('dispatch.index'))
    return redirect(url_for('dispatch.new_dispatch', order_id=pending_orders[0].id))


@dispatch_bp.route('/new/<int:order_id>', methods=['GET', 'POST'])
@login_required
@roles_required('owner', 'admin')
def new_dispatch(order_id):
    order = SalesOrder.query.get_or_404(order_id)
    if order.status not in ['Approved', 'Invoiced', 'Partially Dispatched']:
        flash(f"Cannot dispatch order in '{order.status}' status.", 'danger')
        return redirect(url_for('orders.view', id=order_id))
        
    if request.method == 'POST':
        vehicle_no = request.form.get('vehicle_no', '').strip()
        remarks = request.form.get('remarks', '').strip()
        
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
            flash('Please enter dispatch quantity for at least one item.', 'danger')
            return redirect(url_for('dispatch.new_dispatch', order_id=order.id))
            
        invoice = order.invoices.first()
        dispatch_data = {
            'sales_order_id': order.id,
            'invoice_id': invoice.id if invoice else None,
            'vehicle_no': vehicle_no,
            'remarks': remarks,
            'items': items
        }
        
        try:
            dsp = DispatchService.create_dispatch(dispatch_data, current_user.id)
            db.session.commit()
            flash(f"Dispatch #{dsp.dispatch_number} posted successfully! Finished goods stock reduced.", 'success')
            return redirect(url_for('dispatch.view', id=dsp.id))
        except InsufficientStockException as e:
            db.session.rollback()
            flash(str(e), 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f"Error processing dispatch: {str(e)}", 'danger')
            
    # Items with remaining quantities to dispatch
    order_items_remaining = []
    for item in order.items:
        remaining = item.quantity - item.dispatched_quantity
        avail = item.product.get_current_stock()
        order_items_remaining.append({
            'product_id': item.product_id,
            'product_name': item.product.name,
            'ordered_qty': item.quantity,
            'already_dispatched': item.dispatched_quantity,
            'remaining_qty': remaining,
            'available_fg_stock': avail
        })
        
    return render_template(
        'dispatch/new.html',
        order=order,
        items=order_items_remaining
    )


@dispatch_bp.route('/<int:id>')
@login_required
@roles_required('owner', 'admin', 'auditor')
def view(id):
    dispatch = Dispatch.query.get_or_404(id)
    return render_template('dispatch/view.html', dispatch=dispatch)
