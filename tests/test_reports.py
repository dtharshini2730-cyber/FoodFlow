import os
from datetime import date
from decimal import Decimal
from app.services.stock_service import StockService
from app.services.report_service import ReportService
from app.services.invoice_service import InvoiceService
from app.services.order_service import OrderService


def test_reports_and_exports(session, sample_master_data):
    d = sample_master_data
    # 1. Stock ledger movement
    StockService.record_movement('raw_material', d['flour'].id, date.today(), 'opening_stock', Decimal('100.0'), 'kg', 'IN', 'Opening', unit_rate=Decimal('43.125'), user_id=d['admin'].id)
    StockService.record_movement('finished_good', d['product'].id, date.today(), 'opening_stock', Decimal('200.0'), 'packets', 'IN', 'Opening', unit_rate=Decimal('31.14'), user_id=d['admin'].id)
    session.commit()
    
    # 2. Sales order and invoice
    order_data = {
        'customer_id': d['cust_tn'].id,
        'order_date': str(date.today()),
        'items': [{
            'product_id': d['product'].id,
            'quantity': Decimal('50.00'),
            'unit_price': Decimal('50.00')
        }]
    }
    order = OrderService.create_sales_order(order_data, d['admin'].id)
    OrderService.approve_order(order.id, d['admin'].id)
    invoice = InvoiceService.create_invoice_from_order(order.id, d['admin'].id)
    session.commit()
    
    # 3. Test Raw Material Stock Summary report
    raw_stock_report = ReportService.get_raw_material_stock_summary()
    assert len(raw_stock_report) >= 1
    flour_item = [r for r in raw_stock_report if r['id'] == d['flour'].id][0]
    assert flour_item['current_stock'] == Decimal('100.000')
    
    # 4. Test Sales Register report (no date filter)
    sales_report = ReportService.get_sales_register()
    assert len(sales_report) >= 1
    assert sales_report[0].invoice_number == invoice.invoice_number
    
    # 5. Test GST Outward Summary report
    gst_report = ReportService.get_gst_outward_summary()
    assert gst_report['total_taxable'] == Decimal('2500.00')
    assert gst_report['intrastate_cgst'] == Decimal('62.50')
    assert gst_report['intrastate_sgst'] == Decimal('62.50')
    assert gst_report['total_tax'] == Decimal('125.00')
    
    # 6. Test Excel Export (.xlsx)
    xlsx_bytes = ReportService.export_to_excel(
        title="Sales Register",
        headers=["Invoice No", "Date", "Customer", "Taxable (₹)", "CGST (₹)", "SGST (₹)", "IGST (₹)", "Total (₹)"],
        rows=[[inv.invoice_number, str(inv.invoice_date), inv.customer.name, float(inv.total_taxable), float(inv.cgst_total), float(inv.sgst_total), float(inv.igst_total), float(inv.grand_total)] for inv in sales_report]
    )
    assert len(xlsx_bytes.getvalue()) > 1000  # Valid Excel file generated
    
    # 7. Test PDF Invoice Generation
    pdf_bytes = InvoiceService.generate_invoice_pdf(invoice.id)
    assert len(pdf_bytes.getvalue()) > 1000  # Valid PDF file generated
    assert pdf_bytes.getvalue().startswith(b'%PDF')
