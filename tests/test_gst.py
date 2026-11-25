from decimal import Decimal
from app.services.order_service import OrderService
from app.services.invoice_service import InvoiceService


def test_intrastate_gst_calculation(session, sample_master_data):
    d = sample_master_data
    # Customer TN: 150 pkts @ ₹50.00 = Taxable ₹7,500
    # CGST (2.5%) = ₹187.50, SGST (2.5%) = ₹187.50, Total = ₹7,875.00
    calc = OrderService.calculate_item_gst(
        customer=d['cust_tn'],
        selling_price=Decimal('50.00'),
        quantity=Decimal('150.00'),
        gst_rate=Decimal('5.00')
    )
    assert calc['taxable_amount'] == Decimal('7500.00')
    assert calc['cgst_amount'] == Decimal('187.50')
    assert calc['sgst_amount'] == Decimal('187.50')
    assert calc['igst_amount'] == Decimal('0.00')
    assert calc['total_amount'] == Decimal('7875.00')


def test_interstate_igst_calculation(session, sample_master_data):
    d = sample_master_data
    # Customer Karnataka: 120 pkts @ ₹50.00 = Taxable ₹6,000
    # IGST (5.0%) = ₹300.00, Total = ₹6,300.00
    calc = OrderService.calculate_item_gst(
        customer=d['cust_ka'],
        selling_price=Decimal('50.00'),
        quantity=Decimal('120.00'),
        gst_rate=Decimal('5.00')
    )
    assert calc['taxable_amount'] == Decimal('6000.00')
    assert calc['cgst_amount'] == Decimal('0.00')
    assert calc['sgst_amount'] == Decimal('0.00')
    assert calc['igst_amount'] == Decimal('300.00')
    assert calc['total_amount'] == Decimal('6300.00')


def test_invoice_generation_and_credit_notes(session, sample_master_data):
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
    
    assert invoice.total_taxable == Decimal('7500.00')
    assert invoice.cgst_total == Decimal('187.50')
    assert invoice.sgst_total == Decimal('187.50')
    assert invoice.igst_total == Decimal('0.00')
    assert invoice.grand_total == Decimal('7875.00')
    assert invoice.outstanding_amount == Decimal('7875.00')
    
    # Test Credit Note
    cn = InvoiceService.create_credit_note(invoice.id, Decimal('500.00'), 'Damaged return', d['admin'].id)
    session.commit()
    
    assert invoice.total_credits == Decimal('500.00')
    assert invoice.outstanding_amount == Decimal('7375.00')
