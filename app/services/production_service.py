from datetime import datetime
from decimal import Decimal
from app import db
from app.models.master import Product, RawMaterial, PackagingMaterial
from app.models.bom import BOMVersion
from app.models.production import (
    ProductionRun, ProductionConsumption, ProductionOutput, ProductionOverhead
)
from app.models.audit import AuditLog
from app.services.stock_service import StockService, InsufficientStockException


class ProductionService:
    
    @classmethod
    def create_production_run(cls, run_data, user_id):
        """
        Executes a production run atomically:
        1. Validates material and packaging availability.
        2. Calculates planned vs actual and variances.
        3. Reduces raw material stock.
        4. Reduces packaging stock (including damaged items).
        5. Increases finished goods stock.
        6. Computes weighted-average costing & cost per packet.
        7. Records audit log.
        Rolls back on any error.
        """
        product_id = int(run_data['product_id'])
        bom_version_id = int(run_data['bom_version_id'])
        batch_count = Decimal(str(run_data.get('batch_count', '1.0')))
        actual_output = Decimal(str(run_data['actual_output']))  # Good packets
        damaged_output = Decimal(str(run_data.get('damaged_output', '0.0')))
        production_date = run_data['production_date']
        if isinstance(production_date, str):
            production_date = datetime.strptime(production_date, '%Y-%m-%d').date()
            
        tolerance_pct = Decimal(str(run_data.get('tolerance_pct', '3.0')))
        
        bom_version = BOMVersion.query.get(bom_version_id)
        if not bom_version:
            raise ValueError(f"BOM Version #{bom_version_id} not found.")
            
        product = Product.query.get(product_id)
        if not product:
            raise ValueError(f"Product #{product_id} not found.")
            
        # Expected output = recipe yield * batch_count
        expected_output = bom_version.expected_output * batch_count
        
        # Yield variance % = (Actual output - Expected output) / Expected output * 100
        if expected_output > Decimal('0'):
            yield_variance_pct = ((actual_output - expected_output) / expected_output) * Decimal('100.0')
        else:
            yield_variance_pct = Decimal('0.00')
            
        yield_variance_alert = abs(yield_variance_pct) > tolerance_pct
        
        # Overheads
        labour_cost = Decimal(str(run_data.get('labour_cost', '0.00')))
        gas_cost = Decimal(str(run_data.get('gas_cost', '0.00')))
        power_cost = Decimal(str(run_data.get('power_cost', '0.00')))
        other_overhead_cost = Decimal(str(run_data.get('other_overhead_cost', '0.00')))
        
        # Generate sequential run number
        count = ProductionRun.query.count() + 1
        run_number = f"PR-{datetime.now().year}-{count:04d}"
        
        prod_run = ProductionRun(
            run_number=run_number,
            production_date=production_date,
            product_id=product_id,
            bom_version_id=bom_version_id,
            batch_count=batch_count,
            expected_output=expected_output,
            actual_output=actual_output,
            yield_variance_pct=yield_variance_pct,
            yield_variance_alert=yield_variance_alert,
            labour_cost=labour_cost,
            gas_cost=gas_cost,
            power_cost=power_cost,
            other_overhead_cost=other_overhead_cost,
            status='completed',
            remarks=run_data.get('remarks', ''),
            created_by_id=user_id
        )
        db.session.add(prod_run)
        db.session.flush()
        
        # Add output entry
        p_output = ProductionOutput(
            production_run_id=prod_run.id,
            product_id=product_id,
            good_quantity=actual_output,
            damaged_quantity=damaged_output,
            unit=product.unit
        )
        db.session.add(p_output)
        
        # Track costs
        total_material_cost = Decimal('0.00')
        total_packaging_cost = Decimal('0.00')
        
        # Process consumptions
        # items_consumed: list of dicts with {item_type, item_id, actual_qty, damaged_qty, unit}
        consumptions_input = run_data.get('consumptions', [])
        
        for c_input in consumptions_input:
            item_type = c_input['item_type']
            item_id = int(c_input['item_id'])
            actual_qty = Decimal(str(c_input['actual_quantity']))
            damaged_qty = Decimal(str(c_input.get('damaged_quantity', '0.0')))
            unit = c_input['unit']
            
            # Find planned quantity from BOM
            bom_item = bom_version.items.filter_by(item_type=item_type, item_id=item_id).first()
            if bom_item:
                planned_qty = bom_item.standard_quantity * batch_count
            else:
                planned_qty = actual_qty
                
            # Consumption variance % = (Actual - Planned) / Planned * 100
            if planned_qty > Decimal('0'):
                c_variance_pct = ((actual_qty - planned_qty) / planned_qty) * Decimal('100.0')
            else:
                c_variance_pct = Decimal('0.00')
                
            c_variance_alert = abs(c_variance_pct) > tolerance_pct
            
            # Costing
            if item_type == 'raw_material':
                material = RawMaterial.query.with_for_update().get(item_id)
                unit_cost = material.current_rate
                line_cost = actual_qty * unit_cost
                total_material_cost += line_cost
                
                # Reduce stock
                StockService.record_movement(
                    item_type='raw_material',
                    item_id=item_id,
                    movement_date=production_date,
                    movement_type='production_issue',
                    quantity=actual_qty,
                    unit=unit,
                    direction='OUT',
                    source_document_type='ProductionRun',
                    source_document_id=prod_run.id,
                    unit_rate=unit_cost,
                    user_id=user_id
                )
            elif item_type == 'packaging_material':
                packaging = PackagingMaterial.query.with_for_update().get(item_id)
                unit_cost = packaging.current_rate
                # For packaging: total consumed is actual good used + damaged
                total_pkg_qty = actual_qty + damaged_qty
                line_cost = total_pkg_qty * unit_cost
                total_packaging_cost += line_cost
                
                # Deduct good packaging issue
                if actual_qty > Decimal('0'):
                    StockService.record_movement(
                        item_type='packaging_material',
                        item_id=item_id,
                        movement_date=production_date,
                        movement_type='production_issue',
                        quantity=actual_qty,
                        unit=unit,
                        direction='OUT',
                        source_document_type='ProductionRun',
                        source_document_id=prod_run.id,
                        unit_rate=unit_cost,
                        user_id=user_id
                    )
                # Deduct damaged packaging as production damage
                if damaged_qty > Decimal('0'):
                    StockService.record_movement(
                        item_type='packaging_material',
                        item_id=item_id,
                        movement_date=production_date,
                        movement_type='production_damage',
                        quantity=damaged_qty,
                        unit=unit,
                        direction='OUT',
                        source_document_type='ProductionRun',
                        source_document_id=prod_run.id,
                        unit_rate=unit_cost,
                        user_id=user_id
                    )
            else:
                unit_cost = Decimal('0.0000')
                line_cost = Decimal('0.00')
                
            consumption = ProductionConsumption(
                production_run_id=prod_run.id,
                item_type=item_type,
                item_id=item_id,
                planned_quantity=planned_qty,
                actual_quantity=actual_qty,
                damaged_quantity=damaged_qty,
                unit=unit,
                variance_pct=c_variance_pct,
                variance_alert=c_variance_alert,
                unit_cost=unit_cost,
                total_cost=line_cost
            )
            db.session.add(consumption)
            
        # Add finished goods output to inventory
        StockService.record_movement(
            item_type='finished_good',
            item_id=product_id,
            movement_date=production_date,
            movement_type='production_output',
            quantity=actual_output,
            unit=product.unit,
            direction='IN',
            source_document_type='ProductionRun',
            source_document_id=prod_run.id,
            user_id=user_id
        )
        
        # Calculate total production cost & cost per packet
        total_overheads = labour_cost + gas_cost + power_cost + other_overhead_cost
        total_production_cost = total_material_cost + total_packaging_cost + total_overheads
        
        if actual_output > Decimal('0'):
            cost_per_packet = total_production_cost / actual_output
        else:
            cost_per_packet = Decimal('0.0000')
            
        prod_run.total_material_cost = total_material_cost
        prod_run.total_packaging_cost = total_packaging_cost
        prod_run.total_production_cost = total_production_cost
        prod_run.cost_per_packet = cost_per_packet
        
        # Record Overheads breakdown
        if labour_cost > Decimal('0'):
            db.session.add(ProductionOverhead(production_run_id=prod_run.id, overhead_type='labour', amount=labour_cost))
        if gas_cost > Decimal('0'):
            db.session.add(ProductionOverhead(production_run_id=prod_run.id, overhead_type='gas', amount=gas_cost))
        if power_cost > Decimal('0'):
            db.session.add(ProductionOverhead(production_run_id=prod_run.id, overhead_type='power', amount=power_cost))
        if other_overhead_cost > Decimal('0'):
            db.session.add(ProductionOverhead(production_run_id=prod_run.id, overhead_type='other', amount=other_overhead_cost))
            
        AuditLog.log(
            user_id=user_id,
            action='POST',
            module='Production',
            record_id=prod_run.id,
            new_values={
                'run_number': run_number,
                'actual_output': str(actual_output),
                'cost_per_packet': str(cost_per_packet),
                'yield_variance_pct': str(yield_variance_pct)
            },
            description=f"Completed production run {run_number}: {actual_output} pkts produced @ ₹{cost_per_packet:.2f}/pkt."
        )
        return prod_run

    @classmethod
    def reverse_production_run(cls, run_id, reason, user_id):
        """
        Reverses a posted production run with controlled correction and audit trail.
        Restores raw material and packaging stock, decrements finished goods stock.
        """
        prod_run = ProductionRun.query.with_for_update().get(run_id)
        if not prod_run:
            raise ValueError(f"Production Run #{run_id} not found.")
        if prod_run.status == 'reversed':
            raise ValueError(f"Production Run {prod_run.run_number} is already reversed.")
            
        # Verify sufficient FG stock to reverse output
        current_fg_stock = StockService.get_stock_balance('finished_good', prod_run.product_id)
        if current_fg_stock < prod_run.actual_output:
            raise InsufficientStockException(
                f"Cannot reverse production run {prod_run.run_number}: "
                f"Available FG stock is {current_fg_stock}, but run produced {prod_run.actual_output} pkts."
            )
            
        # Reverse FG
        StockService.record_movement(
            item_type='finished_good',
            item_id=prod_run.product_id,
            movement_date=datetime.utcnow().date(),
            movement_type='stock_adjustment',
            quantity=prod_run.actual_output,
            unit=prod_run.product.unit,
            direction='OUT',
            source_document_type='ProductionRunReversal',
            source_document_id=prod_run.id,
            user_id=user_id
        )
        
        # Restore consumed items
        for consumption in prod_run.consumptions:
            total_qty_to_restore = consumption.actual_quantity + consumption.damaged_quantity
            StockService.record_movement(
                item_type=consumption.item_type,
                item_id=consumption.item_id,
                movement_date=datetime.utcnow().date(),
                movement_type='stock_adjustment',
                quantity=total_qty_to_restore,
                unit=consumption.unit,
                direction='IN',
                source_document_type='ProductionRunReversal',
                source_document_id=prod_run.id,
                unit_rate=consumption.unit_cost,
                user_id=user_id
            )
            
        prod_run.status = 'reversed'
        prod_run.remarks = f"{prod_run.remarks} [REVERSED on {datetime.utcnow().strftime('%d-%m-%Y')}: {reason}]"
        
        AuditLog.log(
            user_id=user_id,
            action='REVERSE',
            module='Production',
            record_id=prod_run.id,
            new_values={'status': 'reversed', 'reason': reason},
            description=f"Reversed production run {prod_run.run_number}: {reason}"
        )
        return prod_run
