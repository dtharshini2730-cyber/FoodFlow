from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from app import db
from app.models.billing import Invoice
from app.models.sales import SalesOrder
from app.services.invoice_service import InvoiceService
from app.utils.decorators import roles_required

invoices_bp = Blueprint('invoices', __name__)


@invoices_bp.route('/')
@login_required
@roles_required('owner', 'admin', 'auditor')
def index():
    invoices_list = Invoice.query.order_by(Invoice.invoice_date.desc(), Invoice.id.desc()).all()
    return render_template('invoices/index.html', invoices=invoices_list)


@invoices_bp.route('/generate/<int:order_id>', methods=['POST'])
@login_required
@roles_required('owner', 'admin')
def generate(order_id):
    try:
        invoice = InvoiceService.create_invoice_from_order(order_id, current_user.id)
        db.session.commit()
        flash(f"GST Tax Invoice #{invoice.invoice_number} generated successfully for ₹{invoice.grand_total:.2f}.", 'success')
        return redirect(url_for('invoices.view', id=invoice.id))
    except Exception as e:
        db.session.rollback()
        flash(f"Error generating invoice: {str(e)}", 'danger')
        return redirect(url_for('orders.view', id=order_id))


@invoices_bp.route('/<int:id>')
@login_required
@roles_required('owner', 'admin', 'auditor')
def view(id):
    invoice = Invoice.query.get_or_404(id)
    return render_template('invoices/view.html', invoice=invoice)


@invoices_bp.route('/<int:id>/pdf')
@login_required
@roles_required('owner', 'admin', 'auditor')
def download_pdf(id):
    invoice = Invoice.query.get_or_404(id)
    pdf_buffer = InvoiceService.generate_invoice_pdf(invoice.id)
    safe_filename = invoice.invoice_number.replace('/', '_') + '.pdf'
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=safe_filename,
        mimetype='application/pdf'
    )


@invoices_bp.route('/<int:id>/credit-note', methods=['POST'])
@login_required
@roles_required('owner', 'admin')
def credit_note(id):
    amount = Decimal(request.form.get('amount', '0.00'))
    reason = request.form.get('reason', '').strip()
    
    if amount <= Decimal('0.00') or not reason:
        flash('Valid amount and reason required for Credit Note.', 'danger')
        return redirect(url_for('invoices.view', id=id))
        
    try:
        cn = InvoiceService.create_credit_note(id, amount, reason, current_user.id)
        db.session.commit()
        flash(f"Credit Note #{cn.credit_note_number} for ₹{amount:.2f} issued successfully.", 'info')
    except Exception as e:
        db.session.rollback()
        flash(f"Error issuing credit note: {str(e)}", 'danger')
        
    return redirect(url_for('invoices.view', id=id))
