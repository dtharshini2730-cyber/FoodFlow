from decimal import Decimal
from datetime import date
import pytest
from app.services.stock_service import StockService
from app.services.production_service import ProductionService


def test_production_reversal(session, sample_master_data):
    d = sample_master_data
    StockService.record_movement('raw_material', d['flour'].id, date(2024, 4, 1), 'opening_stock', Decimal('100.0'), 'kg', 'IN', 'Opening', unit_rate=Decimal('43.125'), user_id=d['admin'].id)
    StockService.record_movement('raw_material', d['oil'].id, date(2024, 4, 1), 'opening_stock', Decimal('30.0'), 'litres', 'IN', 'Opening', unit_rate=Decimal('140.0'), user_id=d['admin'].id)
    StockService.record_movement('packaging_material', d['pouch'].id, date(2024, 4, 1), 'opening_stock', Decimal('500.0'), 'pieces', 'IN', 'Opening', unit_rate=Decimal('2.5'), user_id=d['admin'].id)
    session.commit()
    
    run_data = {
        'product_id': d['product'].id,
        'bom_version_id': d['bom_v'].id,
        'batch_count': Decimal('1.00'),
        'actual_output': Decimal('188.00'),
        'damaged_output': Decimal('0.00'),
        'production_date': '2024-04-10',
        'labour_cost': Decimal('1200.00'),
        'gas_cost': Decimal('600.00'),
        'consumptions': [
            {'item_type': 'raw_material', 'item_id': d['flour'].id, 'actual_quantity': Decimal('40.0'), 'damaged_quantity': Decimal('0.0'), 'unit': 'kg'},
            {'item_type': 'raw_material', 'item_id': d['oil'].id, 'actual_quantity': Decimal('10.0'), 'damaged_quantity': Decimal('0.0'), 'unit': 'litres'},
            {'item_type': 'packaging_material', 'item_id': d['pouch'].id, 'actual_quantity': Decimal('188.0'), 'damaged_quantity': Decimal('6.0'), 'unit': 'pieces'}
        ]
    }
    run = ProductionService.create_production_run(run_data, d['admin'].id)
    session.commit()
    
    # After run: Finished good is 188, Flour is 60 (100 - 40), Pouch is 306 (500 - 194)
    assert StockService.get_stock_balance('finished_good', d['product'].id) == Decimal('188.000')
    assert StockService.get_stock_balance('raw_material', d['flour'].id) == Decimal('60.000')
    assert StockService.get_stock_balance('packaging_material', d['pouch'].id) == Decimal('306.000')
    
    # Reversal
    rev_run = ProductionService.reverse_production_run(run.id, "Batch spoiled due to power cut", d['admin'].id)
    session.commit()
    
    assert rev_run.status == 'reversed'
    assert "Batch spoiled due to power cut" in (rev_run.remarks or "")
    
    # Stock should be fully restored
    assert StockService.get_stock_balance('finished_good', d['product'].id) == Decimal('0.000')
    assert StockService.get_stock_balance('raw_material', d['flour'].id) == Decimal('100.000')
    assert StockService.get_stock_balance('packaging_material', d['pouch'].id) == Decimal('500.000')
