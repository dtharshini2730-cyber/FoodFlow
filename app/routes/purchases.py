from datetime import datetime
from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models.purchase import Purchase
from app.models.master import Supplier, RawMaterial, PackagingMaterial
from app.services.stock_service import StockService, DuplicatePostingException
from app.utils.decorators import roles_required

purchases_bp = Blueprint('purchases', __name__)


@purchases_bp.route('/')
@login_required
@roles_required('owner', 'admin', 'auditor')
def index():
    purchases_list = Purchase.query.order_by(Purchase.purchase_date.desc(), Purchase.id.desc()).all()
    return render_template('purchases/index.html', purchases=purchases_list)


@purchases_bp.route('/new', methods=['GET', 'POST'])
@login_required
@roles_required('owner', 'admin')
def new_purchase():
    if request.method == 'POST':
        supplier_id = request.form.get('supplier_id', type=int)
        purchase_date = request.form.get('purchase_date')
        supplier_invoice_no = request.form.get('supplier_invoice_no', '').strip()
        
        # Parse items from form
        item_types = request.form.getlist('item_type[]')
        item_ids = request.form.getlist('item_id[]')
        quantities = request.form.getlist('quantity[]')
        units = request.form.getlist('unit[]')
        rates = request.form.getlist('unit_rate[]')
        tax_rates = request.form.getlist('tax_rate[]')
        
        items = []
        for i in range(len(item_types)):
            if not item_ids[i] or not quantities[i] or not rates[i]:
                continue
            items.append({
                'item_type': item_types[i],
                'item_id': int(item_ids[i]),
                'quantity': Decimal(quantities[i]),
                'unit': units[i],
                'unit_rate': Decimal(rates[i]),
                'tax_rate': Decimal(tax_rates[i] if i < len(tax_rates) and tax_rates[i] else '5.0')
            })
            
        if not items:
            flash('Please add at least one material to the purchase.', 'danger')
            return redirect(url_for('purchases.new_purchase'))
            
        purchase_data = {
            'supplier_id': supplier_id,
            'purchase_date': purchase_date,
            'supplier_invoice_no': supplier_invoice_no,
            'items': items
        }
        
        try:
            purchase = StockService.post_purchase(purchase_data, current_user.id)
            db.session.commit()
            flash(f"Purchase #{purchase.purchase_number} posted successfully. Inventory and moving weighted-average valuation updated.", 'success')
            return redirect(url_for('purchases.view', id=purchase.id))
        except DuplicatePostingException as e:
            db.session.rollback()
            flash(str(e), 'warning')
            return redirect(url_for('purchases.index'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error posting purchase: {str(e)}", 'danger')
            return redirect(url_for('purchases.new_purchase'))
            
    suppliers = Supplier.query.filter_by(is_active=True).all()
    raw_materials = RawMaterial.query.filter_by(is_active=True).all()
    packaging_materials = PackagingMaterial.query.filter_by(is_active=True).all()
    today_str = datetime.utcnow().strftime('%Y-%m-%d')
    
    return render_template(
        'purchases/new.html',
        suppliers=suppliers,
        raw_materials=raw_materials,
        packaging_materials=packaging_materials,
        today_str=today_str
    )


@purchases_bp.route('/<int:id>')
@login_required
@roles_required('owner', 'admin', 'auditor')
def view(id):
    purchase = Purchase.query.get_or_404(id)
    return render_template('purchases/view.html', purchase=purchase)
