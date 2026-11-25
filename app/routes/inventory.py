from datetime import datetime
from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models.inventory import StockLedger, StockAdjustment
from app.models.master import RawMaterial, PackagingMaterial, Product
from app.models.audit import AuditLog
from app.services.stock_service import StockService, InsufficientStockException
from app.services.report_service import ReportService
from app.utils.decorators import roles_required

inventory_bp = Blueprint('inventory', __name__)


@inventory_bp.route('/')
@login_required
def index():
    raw_materials = ReportService.get_raw_material_stock_summary()
    packaging = ReportService.get_packaging_stock_summary()
    finished_goods = ReportService.get_finished_goods_stock_summary()
    return render_template(
        'inventory/index.html',
        raw_materials=raw_materials,
        packaging=packaging,
        finished_goods=finished_goods
    )


@inventory_bp.route('/ledger')
@login_required
def ledger():
    item_type = request.args.get('item_type', '').strip()
    item_id = request.args.get('item_id', type=int)
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')
    
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
    
    movements = ReportService.get_stock_movement_history(
        item_type=item_type or None,
        item_id=item_id,
        start_date=start_date,
        end_date=end_date
    )
    
    return render_template(
        'inventory/ledger.html',
        movements=movements,
        item_type=item_type,
        item_id=item_id,
        start_date=start_date_str,
        end_date=end_date_str
    )


@inventory_bp.route('/adjust', methods=['GET', 'POST'])
@login_required
@roles_required('owner', 'admin')
def adjust():
    if request.method == 'POST':
        item_type = request.form.get('item_type')
        item_id = request.form.get('item_id', type=int)
        quantity = Decimal(request.form.get('quantity', '0'))
        direction = request.form.get('direction', 'IN')
        reason = request.form.get('reason', '').strip()
        
        if quantity <= Decimal('0'):
            flash('Adjustment quantity must be greater than zero.', 'danger')
            return redirect(url_for('inventory.adjust'))
        if not reason:
            flash('Mandatory reason required for manual stock adjustment.', 'danger')
            return redirect(url_for('inventory.adjust'))
            
        try:
            adj = StockAdjustment(
                item_type=item_type,
                item_id=item_id,
                adjustment_date=datetime.utcnow().date(),
                quantity=quantity,
                unit='kg' if item_type == 'raw_material' else ('pcs' if item_type == 'packaging_material' else 'packets'),
                direction=direction,
                reason=reason,
                created_by_id=current_user.id
            )
            db.session.add(adj)
            db.session.flush()
            
            # Post to Stock Ledger
            StockService.record_movement(
                item_type=item_type,
                item_id=item_id,
                movement_date=datetime.utcnow().date(),
                movement_type='stock_adjustment',
                quantity=quantity,
                unit=adj.unit,
                direction=direction,
                source_document_type='StockAdjustment',
                source_document_id=adj.id,
                user_id=current_user.id
            )
            
            AuditLog.log(
                user_id=current_user.id,
                action='POST',
                module='Stock',
                record_id=adj.id,
                new_values={'direction': direction, 'quantity': str(quantity), 'reason': reason},
                description=f"Stock adjustment #{adj.id}: {direction} {quantity} {adj.unit} ({reason})."
            )
            
            db.session.commit()
            flash('Stock adjustment recorded successfully.', 'success')
            return redirect(url_for('inventory.index'))
        except InsufficientStockException as e:
            db.session.rollback()
            flash(str(e), 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f"Error during stock adjustment: {str(e)}", 'danger')
            
    raw_materials = RawMaterial.query.filter_by(is_active=True).all()
    packaging = PackagingMaterial.query.filter_by(is_active=True).all()
    products = Product.query.filter_by(is_active=True).all()
    
    return render_template(
        'inventory/adjust.html',
        raw_materials=raw_materials,
        packaging=packaging,
        products=products
    )
