from datetime import datetime
from decimal import Decimal
from flask import Blueprint, render_template, request, Response, send_file
from flask_login import login_required, current_user
from app.services.report_service import ReportService
from app.utils.decorators import roles_required

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/')
@login_required
@roles_required('owner', 'admin', 'auditor')
def index():
    report_type = request.args.get('type', 'sales_register')
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')
    export_format = request.args.get('export', '')
    
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
    
    data = None
    headers = []
    rows = []
    
    if report_type == 'sales_register':
        data = ReportService.get_sales_register(start_date, end_date)
        headers = ['Invoice No', 'Date', 'Customer', 'State', 'GSTIN', 'Taxable (₹)', 'CGST (₹)', 'SGST (₹)', 'IGST (₹)', 'Total (₹)']
        rows = [[inv.invoice_number, inv.invoice_date.strftime('%d-%m-%Y'), inv.customer_name, inv.place_of_supply, inv.customer_gstin or 'URP',
                 f"{inv.total_taxable:.2f}", f"{inv.cgst_total:.2f}", f"{inv.sgst_total:.2f}", f"{inv.igst_total:.2f}", f"{inv.grand_total:.2f}"]
                for inv in data]
                
    elif report_type == 'customer_sales':
        data = ReportService.get_customer_wise_sales(start_date, end_date)
        headers = ['Customer Name', 'State', 'Invoices', 'Taxable Value (₹)', 'Total GST (₹)', 'Grand Total (₹)']
        rows = [[c.name, c.state, c.invoice_count, f"{c.total_taxable:.2f}", f"{c.total_tax:.2f}", f"{c.grand_total:.2f}"] for c in data]
        
    elif report_type == 'product_sales':
        data = ReportService.get_product_wise_sales(start_date, end_date)
        headers = ['Product Name', 'SKU', 'Category', 'Total Qty Sold', 'Taxable (₹)', 'GST (₹)', 'Total (₹)']
        rows = [[p.name, p.sku, p.category, f"{p.total_quantity:.0f}", f"{p.total_taxable:.2f}", f"{p.total_tax:.2f}", f"{p.grand_total:.2f}"] for p in data]
        
    elif report_type == 'gst_outward':
        data = ReportService.get_gst_outward_summary(start_date, end_date)
        headers = ['Supply Type', 'Taxable Value (₹)', 'CGST (₹)', 'SGST (₹)', 'IGST (₹)', 'Total Tax (₹)', 'Total Supply (₹)']
        rows = [
            ['Intrastate (Tamil Nadu B2B/B2C)', f"{data['intrastate_taxable']:.2f}", f"{data['intrastate_cgst']:.2f}", f"{data['intrastate_sgst']:.2f}", "0.00", f"{(data['intrastate_cgst'] + data['intrastate_sgst']):.2f}", f"{(data['intrastate_taxable'] + data['intrastate_cgst'] + data['intrastate_sgst']):.2f}"],
            ['Interstate (Karnataka & Others)', f"{data['interstate_taxable']:.2f}", "0.00", "0.00", f"{data['interstate_igst']:.2f}", f"{data['interstate_igst']:.2f}", f"{(data['interstate_taxable'] + data['interstate_igst']):.2f}"],
            ['Total Outward Supplies', f"{data['total_taxable']:.2f}", f"{data['intrastate_cgst']:.2f}", f"{data['intrastate_sgst']:.2f}", f"{data['interstate_igst']:.2f}", f"{data['total_tax']:.2f}", f"{data['grand_total']:.2f}"]
        ]
        
    elif report_type == 'purchase_register':
        data = ReportService.get_purchase_register(start_date, end_date)
        headers = ['Purchase No', 'Date', 'Supplier', 'Supplier Inv No', 'Taxable (₹)', 'Tax (₹)', 'Grand Total (₹)']
        rows = [[p.purchase_number, p.purchase_date.strftime('%d-%m-%Y'), p.supplier.name, p.supplier_invoice_no,
                 f"{p.total_taxable_amount:.2f}", f"{p.total_tax_amount:.2f}", f"{p.grand_total:.2f}"] for p in data]
                 
    elif report_type == 'raw_material_stock':
        data = ReportService.get_raw_material_stock_summary()
        headers = ['Material Name', 'SKU', 'Current Stock', 'Unit', 'Reorder Level', 'Status', 'Weighted Avg Rate (₹)', 'Valuation (₹)']
        rows = [[m['name'], m['sku'], f"{m['current_stock']:.3f}", m['unit'], f"{m['reorder_level']:.3f}",
                 'LOW STOCK' if m['is_low_stock'] else 'Optimal', f"{m['current_rate']:.4f}", f"{m['total_valuation']:.2f}"] for m in data]
                 
    elif report_type == 'packaging_stock':
        data = ReportService.get_packaging_stock_summary()
        headers = ['Packaging Name', 'SKU', 'Current Stock', 'Unit', 'Reorder Level', 'Status', 'Rate (₹)', 'Valuation (₹)']
        rows = [[p['name'], p['sku'], f"{p['current_stock']:.3f}", p['unit'], f"{p['reorder_level']:.3f}",
                 'LOW STOCK' if p['is_low_stock'] else 'Optimal', f"{p['current_rate']:.4f}", f"{p['total_valuation']:.2f}"] for p in data]
                 
    elif report_type == 'finished_goods_stock':
        data = ReportService.get_finished_goods_stock_summary()
        headers = ['Product Name', 'SKU', 'Stock Available', 'Unit', 'Selling Price (₹)', 'Valuation (₹)']
        rows = [[fg['name'], fg['sku'], f"{fg['current_stock']:.0f}", fg['unit'], f"{fg['selling_price']:.2f}", f"{fg['total_valuation']:.2f}"] for fg in data]
        
    elif report_type == 'stock_movement':
        data = ReportService.get_stock_movement_history(start_date=start_date, end_date=end_date)
        headers = ['Date', 'Item Type', 'Item Name', 'Movement Type', 'Direction', 'Quantity', 'Unit', 'Source Doc', 'Ref #']
        rows = [[m.movement_date.strftime('%d-%m-%Y'), m.item_type, m.get_item_name(), m.movement_type, m.direction,
                 f"{m.quantity:.3f}", m.unit, m.source_document_type, m.source_document_id or '-'] for m in data]
                 
    elif report_type == 'production_report':
        data = ReportService.get_production_report(start_date, end_date)
        headers = ['Run No', 'Date', 'Product', 'Batches', 'Good Output', 'Damaged', 'Yield Var %', 'Status', 'Run Cost (₹)', 'Cost/Pkt (₹)']
        rows = [[r.run_number, r.production_date.strftime('%d-%m-%Y'), r.product.name, f"{r.batch_count:.1f}",
                 f"{r.actual_output:.0f}", f"{sum(o.damaged_quantity for o in r.outputs):.0f}",
                 f"{r.yield_variance_pct:+.2f}%", r.status, f"{r.total_production_cost:.2f}", f"{r.cost_per_packet:.2f}"] for r in data]
                 
    elif report_type == 'consumption_analysis':
        data = ReportService.get_planned_vs_actual_consumption(start_date, end_date)
        headers = ['Run No', 'Date', 'Product', 'Type', 'Item ID', 'Planned Qty', 'Actual Qty', 'Damaged Qty', 'Unit', 'Variance %', 'Cost (₹)']
        rows = [[c.run_number, c.production_date.strftime('%d-%m-%Y'), c.product_name, c.item_type, c.item_id,
                 f"{c.planned_quantity:.3f}", f"{c.actual_quantity:.3f}", f"{c.damaged_quantity:.3f}", c.unit,
                 f"{c.variance_pct:+.2f}%", f"{c.total_cost:.2f}"] for c in data]
                 
    elif report_type == 'yield_report':
        data = ReportService.get_production_yield_report(start_date, end_date)
        headers = ['Run No', 'Date', 'Product', 'Expected Output', 'Actual Output', 'Yield Variance %', 'Alert Triggered']
        rows = [[y['run_number'], y['date'].strftime('%d-%m-%Y'), y['product_name'], f"{y['expected_output']:.0f}",
                 f"{y['actual_output']:.0f}", f"{y['yield_variance_pct']:+.2f}%", 'YES (EXCEEDED 3%)' if y['yield_variance_alert'] else 'Normal'] for y in data]
                 
    elif report_type == 'wastage_report':
        data = ReportService.get_wastage_report(start_date, end_date)
        headers = ['Run No', 'Date', 'Product', 'Material Type', 'Item ID', 'Damaged Qty', 'Unit', 'Wastage Cost (₹)']
        rows = [[w.run_number, w.production_date.strftime('%d-%m-%Y'), w.product_name, w.item_type, w.item_id,
                 f"{w.damaged_quantity:.3f}", w.unit, f"{w.wastage_cost:.2f}"] for w in data]
                 
    elif report_type == 'cost_per_packet':
        data = ReportService.get_cost_per_packet_report(start_date, end_date)
        headers = ['Run No', 'Product', 'Good Output', 'Material (₹)', 'Pkg (₹)', 'Labour (₹)', 'Gas/Pwr (₹)', 'Total Cost (₹)', 'Cost/Pkt (₹)', 'Selling Price (₹)', 'Gross Margin %']
        rows = [[cp['run_number'], cp['product_name'], f"{cp['good_packets']:.0f}", f"{cp['material_cost']:.2f}",
                 f"{cp['packaging_cost']:.2f}", f"{cp['labour_cost']:.2f}", f"{cp['gas_power_cost']:.2f}",
                 f"{cp['total_cost']:.2f}", f"{cp['cost_per_packet']:.2f}", f"{cp['selling_price']:.2f}", f"{cp['gross_margin_pct']:.1f}%"] for cp in data]
                 
    elif report_type == 'payment_collection':
        data = ReportService.get_payment_collection_report(start_date, end_date)
        headers = ['Payment No', 'Date', 'Customer', 'Mode', 'Ref No', 'Amount (₹)', 'Allocated (₹)']
        rows = [[p.payment_number, p.payment_date.strftime('%d-%m-%Y'), p.customer.name, p.payment_mode,
                 p.reference_number or '-', f"{p.amount:.2f}", f"{p.total_allocated:.2f}"] for p in data]
                 
    elif report_type == 'customer_outstanding':
        data = ReportService.get_customer_outstanding_report()
        headers = ['Customer Name', 'State', 'Mobile', 'Credit Limit (₹)', 'Total Invoiced (₹)', 'Total Paid (₹)', 'Outstanding Due (₹)']
        rows = [[o['customer_name'], o['state'], o['mobile'], f"{o['credit_limit']:.2f}",
                 f"{o['total_invoiced']:.2f}", f"{o['total_paid']:.2f}", f"{o['outstanding_due']:.2f}"] for o in data]
                 
    elif report_type == 'customer_ageing':
        data = ReportService.get_customer_ageing_report()
        headers = ['Customer Name', 'State', 'Credit Limit (₹)', '0 - 30 Days (₹)', '31 - 60 Days (₹)', '61 - 90 Days (₹)', '> 90 Days (₹)', 'Total Due (₹)']
        rows = [[a['customer_name'], a['state'], f"{a['credit_limit']:.2f}",
                 f"{a['bucket_0_30']:.2f}", f"{a['bucket_31_60']:.2f}", f"{a['bucket_61_90']:.2f}", f"{a['bucket_90_plus']:.2f}", f"{a['total_outstanding']:.2f}"] for a in data]

    # Handle Exports
    if export_format == 'csv':
        csv_data = ReportService.export_to_csv(headers, rows)
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-disposition": f"attachment; filename={report_type}.csv"}
        )
    elif export_format == 'excel':
        excel_buffer = ReportService.export_to_excel(report_type.replace('_', ' ').title(), headers, rows)
        return send_file(
            excel_buffer,
            as_attachment=True,
            download_name=f"{report_type}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    return render_template(
        'reports/index.html',
        report_type=report_type,
        start_date=start_date_str,
        end_date=end_date_str,
        headers=headers,
        rows=rows,
        data=data
    )
