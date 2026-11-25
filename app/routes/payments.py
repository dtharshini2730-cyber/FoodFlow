from datetime import datetime
from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.payment import Payment
from app.models.master import Customer
from app.models.billing import Invoice
from app.services.payment_service import PaymentService
from app.utils.decorators import roles_required

payments_bp = Blueprint('payments', __name__)


@payments_bp.route('/')
@login_required
@roles_required('owner', 'admin', 'auditor')
def index():
    payments_list = Payment.query.order_by(Payment.payment_date.desc(), Payment.id.desc()).all()
    customers = Customer.query.filter_by(is_active=True).all()
    outstanding_summary = []
    for c in customers:
        due = PaymentService.get_customer_outstanding(c.id)
        if due > Decimal('0.00'):
            outstanding_summary.append({
                'customer_id': c.id,
                'name': c.name,
                'state': c.state,
                'outstanding': due
            })
    return render_template(
        'payments/index.html',
        payments=payments_list,
        outstanding_summary=outstanding_summary
    )


@payments_bp.route('/new', methods=['GET', 'POST'])
@login_required
@roles_required('owner', 'admin')
def new_payment():
    if request.method == 'POST':
        customer_id = request.form.get('customer_id', type=int)
        amount = Decimal(request.form.get('amount', '0.00'))
        payment_mode = request.form.get('payment_mode', 'UPI')
        payment_date = request.form.get('payment_date')
        reference_number = request.form.get('reference_number', '').strip()
        remarks = request.form.get('remarks', '').strip()
        
        # Allocations
        inv_ids = request.form.getlist('inv_id[]')
        alloc_amounts = request.form.getlist('alloc_amount[]')
        
        allocations = []
        for i in range(len(inv_ids)):
            if not inv_ids[i] or not alloc_amounts[i]:
                continue
            amt = Decimal(alloc_amounts[i])
            if amt > Decimal('0.00'):
                allocations.append({
                    'invoice_id': int(inv_ids[i]),
                    'amount': amt
                })
                
        payment_data = {
            'customer_id': customer_id,
            'amount': amount,
            'payment_mode': payment_mode,
            'payment_date': payment_date,
            'reference_number': reference_number,
            'remarks': remarks,
            'allocations': allocations
        }
        
        try:
            pay = PaymentService.record_payment(payment_data, current_user.id)
            db.session.commit()
            flash(f"Payment #{pay.payment_number} of ₹{pay.amount:.2f} recorded successfully.", 'success')
            return redirect(url_for('payments.index'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error recording payment: {str(e)}", 'danger')
            
    customers = Customer.query.filter_by(is_active=True).all()
    today_str = datetime.utcnow().strftime('%Y-%m-%d')
    return render_template(
        'payments/new.html',
        customers=customers,
        today_str=today_str
    )


@payments_bp.route('/customer-invoices/<int:customer_id>')
@login_required
def get_customer_invoices(customer_id):
    """API endpoint to get unpaid invoices for payment allocation form."""
    invoices = Invoice.query.filter_by(customer_id=customer_id, status='posted').all()
    result = []
    for inv in invoices:
        due = inv.outstanding_amount
        if due > Decimal('0.00'):
            result.append({
                'id': inv.id,
                'invoice_number': inv.invoice_number,
                'invoice_date': inv.invoice_date.strftime('%d-%m-%Y'),
                'grand_total': float(inv.grand_total),
                'outstanding': float(due)
            })
    return jsonify(result)
