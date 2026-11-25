from decimal import Decimal
from datetime import date
import pytest
from app.services.stock_service import StockService
from app.services.order_service import OrderService
from app.services.dispatch_service import DispatchService


def test_order_dispatch_workflow(session, sample_master_data):
    d = sample_master_data
    # Opening finished goods stock: 200 packets
    StockService.record_movement('finished_good', d['product'].id, date(2024, 4, 1), 'opening_stock', Decimal('200.0'), 'packets', 'IN', 'Opening', unit_rate=Decimal('31.14'), user_id=d['admin'].id)
    session.commit()
    
    # Create and approve order for 150 packets
    order_data = {
        'customer_id': d['cust_tn'].id,
        'order_date': '2024-04-12',
        'items': [{
            'product_id': d['product'].id,
            'quantity': Decimal('150.00'),
            'unit_price': Decimal('50.00')
        }]
    }
    order = OrderService.create_sales_order(order_data, d['admin'].id)
    OrderService.approve_order(order.id, d['admin'].id)
    session.commit()
    
    # 1. Partial dispatch: 100 packets
    dispatch_data_1 = {
        'sales_order_id': order.id,
        'dispatch_date': '2024-04-13',
        'vehicle_no': 'TN-45-AB-1234',
        'driver_name': 'Murugan',
        'items': [{
            'product_id': d['product'].id,
            'quantity': Decimal('100.00')
        }]
    }
    disp1 = DispatchService.create_dispatch(dispatch_data_1, d['admin'].id)
    session.commit()
    
    assert order.status == 'Partially Dispatched'
    assert StockService.get_stock_balance('finished_good', d['product'].id) == Decimal('100.000') # 200 - 100
    
    # 2. Final dispatch: remaining 50 packets
    dispatch_data_2 = {
        'sales_order_id': order.id,
        'dispatch_date': '2024-04-14',
        'vehicle_no': 'TN-45-AB-1234',
        'driver_name': 'Murugan',
        'items': [{
            'product_id': d['product'].id,
            'quantity': Decimal('50.00')
        }]
    }
    disp2 = DispatchService.create_dispatch(dispatch_data_2, d['admin'].id)
    session.commit()
    
    assert order.status == 'Dispatched'
    assert StockService.get_stock_balance('finished_good', d['product'].id) == Decimal('50.000') # 100 - 50
