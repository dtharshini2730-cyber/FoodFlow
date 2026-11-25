from decimal import Decimal
from datetime import date
from app.services.stock_service import StockService
from app.services.production_service import ProductionService


def test_production_run_and_costing(session, sample_master_data):
    d = sample_master_data
    # Add sufficient stock first
    StockService.record_movement('raw_material', d['flour'].id, date(2024, 4, 1), 'opening_stock', Decimal('100.0'), 'kg', 'IN', 'Opening', unit_rate=Decimal('43.125'), user_id=d['admin'].id)
    StockService.record_movement('raw_material', d['oil'].id, date(2024, 4, 1), 'opening_stock', Decimal('30.0'), 'litres', 'IN', 'Opening', unit_rate=Decimal('140.0'), user_id=d['admin'].id)
    StockService.record_movement('packaging_material', d['pouch'].id, date(2024, 4, 1), 'opening_stock', Decimal('500.0'), 'pieces', 'IN', 'Opening', unit_rate=Decimal('2.5'), user_id=d['admin'].id)
    session.commit()
    
    # 1 batch: planned flour = 40kg, actual = 40kg
    # planned oil = 10L, actual = 10.5L (+5% variance -> alert)
    # expected output = 200, actual = 188 (-6% yield variance -> alert)
    # damaged pouches = 6
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
            {'item_type': 'raw_material', 'item_id': d['oil'].id, 'actual_quantity': Decimal('10.5'), 'damaged_quantity': Decimal('0.0'), 'unit': 'litres'},
            {'item_type': 'packaging_material', 'item_id': d['pouch'].id, 'actual_quantity': Decimal('188.0'), 'damaged_quantity': Decimal('6.0'), 'unit': 'pieces'}
        ]
    }
    run = ProductionService.create_production_run(run_data, d['admin'].id)
    session.commit()
    
    # 1. Output verified
    assert run.actual_output == Decimal('188.00')
    assert run.expected_output == Decimal('200.00')
    
    # 2. Yield Variance: (188 - 200)/200 * 100 = -6.00%
    assert run.yield_variance_pct == Decimal('-6.00')
    assert run.yield_variance_alert is True
    
    # 3. Oil variance: (10.5 - 10)/10 * 100 = +5.00%
    oil_c = run.consumptions.filter_by(item_id=d['oil'].id).first()
    assert oil_c.variance_pct == Decimal('5.00')
    assert oil_c.variance_alert is True
    
    # 4. Finished goods stock increased by 188 pkts
    assert StockService.get_stock_balance('finished_good', d['product'].id) == Decimal('188.000')
    
    # 5. Raw material stock deducted: 100 - 40 = 60 kg flour, 30 - 10.5 = 19.5 L oil
    assert StockService.get_stock_balance('raw_material', d['flour'].id) == Decimal('60.000')
    assert StockService.get_stock_balance('raw_material', d['oil'].id) == Decimal('19.500')
    
    # 6. Packaging stock deducted: 500 - 188 - 6 = 306 pieces
    assert StockService.get_stock_balance('packaging_material', d['pouch'].id) == Decimal('306.000')
    
    # 7. Cost per packet verified
    # Total cost = (40*42) + (10.5*140) + ((188+6)*2.5) + 1200 + 600 = 1680 + 1470 + 485 + 1800 = 5435
    expected_cost = Decimal('1680.00') + Decimal('1470.00') + Decimal('485.00') + Decimal('1800.00')
    assert run.total_production_cost == expected_cost
    assert round(run.cost_per_packet, 2) == round(expected_cost / Decimal('188'), 2)
