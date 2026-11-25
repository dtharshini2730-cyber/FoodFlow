from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models.bom import ProductBOM, BOMVersion, BOMItem
from app.models.master import Product, RawMaterial, PackagingMaterial
from app.models.audit import AuditLog
from app.utils.decorators import roles_required

bom_bp = Blueprint('bom', __name__)


@bom_bp.route('/')
@login_required
@roles_required('owner', 'admin', 'production', 'auditor')
def index():
    boms = ProductBOM.query.all()
    products_without_bom = Product.query.filter(~Product.id.in_([b.product_id for b in boms])).all()
    return render_template('bom/index.html', boms=boms, products_without_bom=products_without_bom)


@bom_bp.route('/<int:bom_id>')
@login_required
@roles_required('owner', 'admin', 'production', 'auditor')
def view(bom_id):
    bom = ProductBOM.query.get_or_404(bom_id)
    raw_materials = RawMaterial.query.filter_by(is_active=True).all()
    packaging_materials = PackagingMaterial.query.filter_by(is_active=True).all()
    return render_template(
        'bom/view.html',
        bom=bom,
        raw_materials=raw_materials,
        packaging_materials=packaging_materials
    )


@bom_bp.route('/create', methods=['POST'])
@login_required
@roles_required('owner', 'admin', 'production')
def create():
    product_id = request.form.get('product_id', type=int)
    expected_output = Decimal(request.form.get('expected_output', '200'))
    notes = request.form.get('notes', '')
    
    product = Product.query.get_or_404(product_id)
    
    bom = ProductBOM(product_id=product_id, is_active=True)
    db.session.add(bom)
    db.session.flush()
    
    version = BOMVersion(
        bom_id=bom.id,
        version_number=1,
        batch_size=Decimal('1.00'),
        expected_output=expected_output,
        expected_yield_pct=Decimal('100.00'),
        notes=notes,
        is_active=True
    )
    db.session.add(version)
    db.session.commit()
    
    flash(f"Recipe created for '{product.name}'. Now add raw and packaging materials.", 'success')
    return redirect(url_for('bom.view', bom_id=bom.id))


@bom_bp.route('/<int:bom_id>/add-item', methods=['POST'])
@login_required
@roles_required('owner', 'admin', 'production')
def add_item(bom_id):
    bom = ProductBOM.query.get_or_404(bom_id)
    active_version = bom.active_version
    if not active_version:
        flash('No active recipe version found.', 'danger')
        return redirect(url_for('bom.view', bom_id=bom.id))
        
    item_type = request.form.get('item_type')
    item_id = request.form.get('item_id', type=int)
    quantity = Decimal(request.form.get('quantity', '0'))
    unit = request.form.get('unit', '')
    notes = request.form.get('notes', '')
    
    if quantity <= Decimal('0'):
        flash('Quantity must be greater than zero.', 'danger')
        return redirect(url_for('bom.view', bom_id=bom.id))
        
    bom_item = BOMItem(
        bom_version_id=active_version.id,
        item_type=item_type,
        item_id=item_id,
        standard_quantity=quantity,
        unit=unit,
        notes=notes
    )
    db.session.add(bom_item)
    db.session.commit()
    
    flash('Ingredient added to recipe.', 'success')
    return redirect(url_for('bom.view', bom_id=bom.id))


@bom_bp.route('/<int:bom_id>/new-version', methods=['POST'])
@login_required
@roles_required('owner', 'admin', 'production')
def new_version(bom_id):
    bom = ProductBOM.query.get_or_404(bom_id)
    latest_v = bom.versions.order_by(BOMVersion.version_number.desc()).first()
    new_v_num = (latest_v.version_number + 1) if latest_v else 1
    
    # Deactivate older versions
    for v in bom.versions:
        v.is_active = False
        
    expected_output = Decimal(request.form.get('expected_output', '200'))
    notes = request.form.get('notes', f'Version {new_v_num}')
    
    new_v = BOMVersion(
        bom_id=bom.id,
        version_number=new_v_num,
        batch_size=Decimal('1.00'),
        expected_output=expected_output,
        expected_yield_pct=Decimal('100.00'),
        notes=notes,
        is_active=True
    )
    db.session.add(new_v)
    db.session.flush()
    
    # Optionally clone items from previous active version
    if latest_v:
        for old_item in latest_v.items:
            db.session.add(BOMItem(
                bom_version_id=new_v.id,
                item_type=old_item.item_type,
                item_id=old_item.item_id,
                standard_quantity=old_item.standard_quantity,
                unit=old_item.unit,
                notes=old_item.notes
            ))
            
    db.session.commit()
    flash(f"Created new Recipe Version {new_v_num}. Previous production runs remain preserved.", 'success')
    return redirect(url_for('bom.view', bom_id=bom.id))
