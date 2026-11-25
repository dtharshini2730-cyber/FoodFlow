from datetime import datetime
from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.production import ProductionRun
from app.models.bom import ProductBOM, BOMVersion
from app.models.master import Product, RawMaterial, PackagingMaterial
from app.services.production_service import ProductionService
from app.services.stock_service import InsufficientStockException
from app.utils.decorators import roles_required

production_bp = Blueprint('production', __name__)


@production_bp.route('/')
@login_required
@roles_required('owner', 'admin', 'production', 'auditor')
def index():
    runs = ProductionRun.query.order_by(ProductionRun.production_date.desc(), ProductionRun.id.desc()).all()
    return render_template('production/index.html', runs=runs)


@production_bp.route('/new', methods=['GET', 'POST'])
@login_required
@roles_required('owner', 'admin', 'production')
def new_run():
    if request.method == 'POST':
        product_id = request.form.get('product_id', type=int)
        bom_version_id = request.form.get('bom_version_id', type=int)
        batch_count = Decimal(request.form.get('batch_count', '1.0'))
        actual_output = Decimal(request.form.get('actual_output', '0'))
        damaged_output = Decimal(request.form.get('damaged_output', '0'))
        production_date = request.form.get('production_date')
        
        labour_cost = Decimal(request.form.get('labour_cost', '0.00'))
        gas_cost = Decimal(request.form.get('gas_cost', '0.00'))
        power_cost = Decimal(request.form.get('power_cost', '0.00'))
        other_overhead_cost = Decimal(request.form.get('other_overhead_cost', '0.00'))
        remarks = request.form.get('remarks', '')
        
        # Consumptions
        item_types = request.form.getlist('c_item_type[]')
        item_ids = request.form.getlist('c_item_id[]')
        actual_qtys = request.form.getlist('c_actual_qty[]')
        damaged_qtys = request.form.getlist('c_damaged_qty[]')
        units = request.form.getlist('c_unit[]')
        
        consumptions = []
        for i in range(len(item_types)):
            if not item_ids[i] or not actual_qtys[i]:
                continue
            consumptions.append({
                'item_type': item_types[i],
                'item_id': int(item_ids[i]),
                'actual_quantity': Decimal(actual_qtys[i]),
                'damaged_quantity': Decimal(damaged_qtys[i] if i < len(damaged_qtys) and damaged_qtys[i] else '0.0'),
                'unit': units[i]
            })
            
        run_data = {
            'product_id': product_id,
            'bom_version_id': bom_version_id,
            'batch_count': batch_count,
            'actual_output': actual_output,
            'damaged_output': damaged_output,
            'production_date': production_date,
            'labour_cost': labour_cost,
            'gas_cost': gas_cost,
            'power_cost': power_cost,
            'other_overhead_cost': other_overhead_cost,
            'remarks': remarks,
            'consumptions': consumptions
        }
        
        try:
            prod_run = ProductionService.create_production_run(run_data, current_user.id)
            db.session.commit()
            flash(
                f"Production Run #{prod_run.run_number} posted successfully! "
                f"Finished goods increased by {actual_output} pkts @ ₹{prod_run.cost_per_packet:.2f}/pkt.",
                'success'
            )
            return redirect(url_for('production.view', id=prod_run.id))
        except InsufficientStockException as e:
            db.session.rollback()
            flash(str(e), 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f"Error executing production run: {str(e)}", 'danger')
            
    products = Product.query.filter_by(is_active=True).all()
    boms = ProductBOM.query.filter_by(is_active=True).all()
    today_str = datetime.utcnow().strftime('%Y-%m-%d')
    
    return render_template(
        'production/new.html',
        products=products,
        boms=boms,
        today_str=today_str
    )


@production_bp.route('/bom-details/<int:version_id>')
@login_required
def get_bom_details(version_id):
    """API endpoint to get recipe items for interactive production run form."""
    bom_v = BOMVersion.query.get_or_404(version_id)
    items = []
    for item in bom_v.items:
        items.append({
            'item_type': item.item_type,
            'item_id': item.item_id,
            'name': item.get_item_name(),
            'standard_quantity': float(item.standard_quantity),
            'unit': item.unit
        })
    return jsonify({
        'expected_output': float(bom_v.expected_output),
        'items': items
    })


@production_bp.route('/<int:id>')
@login_required
@roles_required('owner', 'admin', 'production', 'auditor')
def view(id):
    prod_run = ProductionRun.query.get_or_404(id)
    return render_template('production/view.html', run=prod_run)


@production_bp.route('/<int:id>/reverse', methods=['POST'])
@login_required
@roles_required('owner', 'admin')
def reverse(id):
    reason = request.form.get('reason', '').strip()
    if not reason:
        flash('Mandatory reason required for production run reversal.', 'danger')
        return redirect(url_for('production.view', id=id))
        
    try:
        ProductionService.reverse_production_run(id, reason, current_user.id)
        db.session.commit()
        flash('Production run reversed successfully. Stock balances restored.', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f"Error reversing run: {str(e)}", 'danger')
        
    return redirect(url_for('production.view', id=id))
