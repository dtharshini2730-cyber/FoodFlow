from decimal import Decimal
from datetime import date
import pytest
from app.services.stock_service import StockService
from app.services.order_service import OrderService


def test_order_stock_check_and_shortage(session, sample_master_data):
    d = sample_master_data
    # Opening stock of product = 88 packets
    StockService.record_movement('finished_good', d['product'].id, date(2024, 4, 1), 'opening_stock', Decimal('88.0'), 'packets', 'IN', 'Opening', unit_rate=Decimal('31.14'), user_id=d['admin'].id)
    session.commit()
    
    # Customer orders 120 packets (shortage of 32 packets)
    order_data = {
        'customer_id': d['cust_tn'].id,
        'order_date': '2024-04-12',
        'items': [{
            'product_id': d['product'].id,
            'quantity': Decimal('120.00'),
            'unit_price': Decimal('50.00')
        }]
    }
    order = OrderService.create_sales_order(order_data, d['admin'].id)
    session.commit()
    
    # Check availability
    check = OrderService.check_order_stock_availability(order.id)
    assert check['has_shortage'] is True
    item_check = check['items'][0]
    assert item_check['requested_qty'] == Decimal('120.00')
    assert item_check['available_qty'] == Decimal('88.000')
    assert item_check['shortage_qty'] == Decimal('32.000')
    assert item_check['has_sufficient_stock'] is False


def test_order_approval_and_rejection(session, sample_master_data):
    d = sample_master_data
    StockService.record_movement('finished_good', d['product'].id, date(2024, 4, 1), 'opening_stock', Decimal('100.0'), 'packets', 'IN', 'Opening', unit_rate=Decimal('31.14'), user_id=d['admin'].id)
    session.commit()
    
    order_data = {
        'customer_id': d['cust_tn'].id,
        'order_date': '2024-04-12',
        'items': [{
            'product_id': d['product'].id,
            'quantity': Decimal('50.00'),
            'unit_price': Decimal('50.00')
        }]
    }
    order = OrderService.create_sales_order(order_data, d['admin'].id)
    session.commit()
    
    assert order.status == 'Submitted'
    
    # Admin approves
    approved_order = OrderService.approve_order(order.id, d['admin'].id)
    session.commit()
    assert approved_order.status == 'Approved'
    
    # New order for rejection test
    order_data_2 = {
        'customer_id': d['cust_tn'].id,
        'order_date': '2024-04-12',
        'items': [{
            'product_id': d['product'].id,
            'quantity': Decimal('10.00'),
            'unit_price': Decimal('50.00')
        }]
    }
    order2 = OrderService.create_sales_order(order_data_2, d['admin'].id)
    session.commit()
    
    rejected_order = OrderService.reject_order(order2.id, "Exceeded credit limit", d['admin'].id)
    session.commit()
    assert rejected_order.status == 'Rejected'
    assert rejected_order.rejection_reason == "Exceeded credit limit"
