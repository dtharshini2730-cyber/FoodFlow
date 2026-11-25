import pytest
from decimal import Decimal
from app.services.order_service import OrderService
from app.services.invoice_service import InvoiceService
from app.services.payment_service import PaymentService


def test_partial_payment_and_outstanding(session, sample_master_data):
    d = sample_master_data
    # Create invoice for ₹7,875.00
    order_data = {
        'customer_id': d['cust_tn'].id,
        'order_date': '2024-04-12',
        'items': [{'product_id': d['product'].id, 'quantity': Decimal('150.00')}]
    }
    order = OrderService.create_sales_order(order_data, d['admin'].id)
    OrderService.approve_order(order.id, d['admin'].id)
    invoice = InvoiceService.create_invoice_from_order(order.id, d['admin'].id)
    session.commit()
    
    # Partial payment of ₹4,000.00
    payment_data = {
        'customer_id': d['cust_tn'].id,
        'amount': Decimal('4000.00'),
        'payment_mode': 'UPI',
        'allocations': [{'invoice_id': invoice.id, 'amount': Decimal('4000.00')}]
    }
    payment = PaymentService.record_payment(payment_data, d['admin'].id)
    session.commit()
    
    # Outstanding must be 7875 - 4000 = 3875
    assert invoice.total_allocated == Decimal('4000.00')
    assert invoice.outstanding_amount == Decimal('3875.00')
    assert invoice.is_fully_paid is False
    
    # Pay remaining balance of ₹3,875.00
    payment_data_2 = {
        'customer_id': d['cust_tn'].id,
        'amount': Decimal('3875.00'),
        'payment_mode': 'Bank Transfer',
        'allocations': [{'invoice_id': invoice.id, 'amount': Decimal('3875.00')}]
    }
    PaymentService.record_payment(payment_data_2, d['admin'].id)
    session.commit()
    
    assert invoice.total_allocated == Decimal('7875.00')
    assert invoice.outstanding_amount == Decimal('0.00')
    assert invoice.is_fully_paid is True


def test_over_allocation_prevented(session, sample_master_data):
    d = sample_master_data
    order_data = {
        'customer_id': d['cust_tn'].id,
        'order_date': '2024-04-12',
        'items': [{'product_id': d['product'].id, 'quantity': Decimal('150.00')}]
    }
    order = OrderService.create_sales_order(order_data, d['admin'].id)
    OrderService.approve_order(order.id, d['admin'].id)
    invoice = InvoiceService.create_invoice_from_order(order.id, d['admin'].id)
    session.commit()
    
    # Invoice is ₹7,875. Attempting to allocate ₹8,000 must fail
    payment_data = {
        'customer_id': d['cust_tn'].id,
        'amount': Decimal('10000.00'),
        'payment_mode': 'Cash',
        'allocations': [{'invoice_id': invoice.id, 'amount': Decimal('8000.00')}]
    }
    with pytest.raises(ValueError):
        PaymentService.record_payment(payment_data, d['admin'].id)
