import io
import csv
from datetime import datetime, date
from decimal import Decimal
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from sqlalchemy import func
from app import db
from app.models.billing import Invoice, InvoiceItem
from app.models.purchase import Purchase, PurchaseItem
from app.models.production import ProductionRun, ProductionConsumption, ProductionOutput
from app.models.inventory import StockLedger
from app.models.master import Customer, Product, RawMaterial, PackagingMaterial
from app.models.payment import Payment
from app.services.stock_service import StockService
from app.services.payment_service import PaymentService


class ReportService:
    
    # 1. Sales Register
    @staticmethod
    def get_sales_register(start_date=None, end_date=None):
        query = Invoice.query.filter_by(status='posted')
        if start_date:
            query = query.filter(Invoice.invoice_date >= start_date)
        if end_date:
            query = query.filter(Invoice.invoice_date <= end_date)
        return query.order_by(Invoice.invoice_date.desc(), Invoice.id.desc()).all()

    # 2. Customer-wise Sales
    @staticmethod
    def get_customer_wise_sales(start_date=None, end_date=None):
        query = db.session.query(
            Customer.id,
            Customer.name,
            Customer.state,
            func.count(Invoice.id).label('invoice_count'),
            func.sum(Invoice.total_taxable).label('total_taxable'),
            func.sum(Invoice.cgst_total + Invoice.sgst_total + Invoice.igst_total).label('total_tax'),
            func.sum(Invoice.grand_total).label('grand_total')
        ).join(Invoice, Invoice.customer_id == Customer.id).filter(Invoice.status == 'posted')
        
        if start_date:
            query = query.filter(Invoice.invoice_date >= start_date)
        if end_date:
            query = query.filter(Invoice.invoice_date <= end_date)
            
        return query.group_by(Customer.id, Customer.name, Customer.state).order_by(func.sum(Invoice.grand_total).desc()).all()

    # 3. Product-wise Sales
    @staticmethod
    def get_product_wise_sales(start_date=None, end_date=None):
        query = db.session.query(
            Product.id,
            Product.name,
            Product.sku,
            Product.category,
            func.sum(InvoiceItem.quantity).label('total_quantity'),
            func.sum(InvoiceItem.taxable_value).label('total_taxable'),
            func.sum(InvoiceItem.cgst_amount + InvoiceItem.sgst_amount + InvoiceItem.igst_amount).label('total_tax'),
            func.sum(InvoiceItem.total_amount).label('grand_total')
        ).join(InvoiceItem, InvoiceItem.product_id == Product.id).join(Invoice, Invoice.id == InvoiceItem.invoice_id).filter(Invoice.status == 'posted')
        
        if start_date:
            query = query.filter(Invoice.invoice_date >= start_date)
        if end_date:
            query = query.filter(Invoice.invoice_date <= end_date)
            
        return query.group_by(Product.id, Product.name, Product.sku, Product.category).order_by(func.sum(InvoiceItem.total_amount).desc()).all()

    # 4. GST Outward Supplies Summary (GSTR-1 & 3B Reconciliation format)
    @staticmethod
    def get_gst_outward_summary(start_date=None, end_date=None):
        invoices = ReportService.get_sales_register(start_date, end_date)
        intrastate_taxable = Decimal('0.00')
        intrastate_cgst = Decimal('0.00')
        intrastate_sgst = Decimal('0.00')
        interstate_taxable = Decimal('0.00')
        interstate_igst = Decimal('0.00')
        
        for inv in invoices:
            if inv.is_interstate:
                interstate_taxable += inv.total_taxable
                interstate_igst += inv.igst_total
            else:
                intrastate_taxable += inv.total_taxable
                intrastate_cgst += inv.cgst_total
                intrastate_sgst += inv.sgst_total
                
        total_taxable = intrastate_taxable + interstate_taxable
        total_tax = intrastate_cgst + intrastate_sgst + interstate_igst
        grand_total = total_taxable + total_tax
        
        return {
            'intrastate_taxable': intrastate_taxable,
            'intrastate_cgst': intrastate_cgst,
            'intrastate_sgst': intrastate_sgst,
            'interstate_taxable': interstate_taxable,
            'interstate_igst': interstate_igst,
            'total_taxable': total_taxable,
            'total_tax': total_tax,
            'grand_total': grand_total,
            'invoices': invoices
        }

    # 5. Purchase Register
    @staticmethod
    def get_purchase_register(start_date=None, end_date=None):
        query = Purchase.query.filter_by(status='posted')
        if start_date:
            query = query.filter(Purchase.purchase_date >= start_date)
        if end_date:
            query = query.filter(Purchase.purchase_date <= end_date)
        return query.order_by(Purchase.purchase_date.desc(), Purchase.id.desc()).all()

    # 6. Raw Material Stock Summary
    @staticmethod
    def get_raw_material_stock_summary():
        materials = RawMaterial.query.filter_by(is_active=True).all()
        summary = []
        for m in materials:
            stock = m.get_current_stock()
            val = stock * m.current_rate
            summary.append({
                'id': m.id,
                'name': m.name,
                'sku': m.sku,
                'unit': m.base_unit,
                'opening_stock': m.opening_stock,
                'current_stock': stock,
                'reorder_level': m.reorder_level,
                'is_low_stock': stock <= m.reorder_level,
                'current_rate': m.current_rate,
                'total_valuation': val
            })
        return summary

    # 7. Packaging Stock Summary
    @staticmethod
    def get_packaging_stock_summary():
        materials = PackagingMaterial.query.filter_by(is_active=True).all()
        summary = []
        for p in materials:
            stock = p.get_current_stock()
            val = stock * p.current_rate
            summary.append({
                'id': p.id,
                'name': p.name,
                'sku': p.sku,
                'unit': p.unit,
                'opening_quantity': p.opening_quantity,
                'current_stock': stock,
                'reorder_level': p.reorder_level,
                'is_low_stock': stock <= p.reorder_level,
                'current_rate': p.current_rate,
                'total_valuation': val
            })
        return summary

    # 8. Finished Goods Stock Summary
    @staticmethod
    def get_finished_goods_stock_summary():
        products = Product.query.filter_by(is_active=True).all()
        summary = []
        for prod in products:
            stock = prod.get_current_stock()
            val = stock * prod.selling_price
            summary.append({
                'id': prod.id,
                'name': prod.name,
                'sku': prod.sku,
                'unit': prod.unit,
                'current_stock': stock,
                'selling_price': prod.selling_price,
                'total_valuation': val
            })
        return summary

    # 9. Stock Movement History
    @staticmethod
    def get_stock_movement_history(item_type=None, item_id=None, start_date=None, end_date=None):
        query = StockLedger.query
        if item_type:
            query = query.filter_by(item_type=item_type)
        if item_id:
            query = query.filter_by(item_id=item_id)
        if start_date:
            query = query.filter(StockLedger.movement_date >= start_date)
        if end_date:
            query = query.filter(StockLedger.movement_date <= end_date)
        return query.order_by(StockLedger.movement_date.desc(), StockLedger.id.desc()).all()

    # 10. Production Report
    @staticmethod
    def get_production_report(start_date=None, end_date=None):
        query = ProductionRun.query
        if start_date:
            query = query.filter(ProductionRun.production_date >= start_date)
        if end_date:
            query = query.filter(ProductionRun.production_date <= end_date)
        return query.order_by(ProductionRun.production_date.desc(), ProductionRun.id.desc()).all()

    # 11. Planned vs Actual Consumption
    @staticmethod
    def get_planned_vs_actual_consumption(start_date=None, end_date=None):
        query = db.session.query(
            ProductionRun.run_number,
            ProductionRun.production_date,
            Product.name.label('product_name'),
            ProductionConsumption.item_type,
            ProductionConsumption.item_id,
            ProductionConsumption.planned_quantity,
            ProductionConsumption.actual_quantity,
            ProductionConsumption.damaged_quantity,
            ProductionConsumption.unit,
            ProductionConsumption.variance_pct,
            ProductionConsumption.variance_alert,
            ProductionConsumption.total_cost
        ).join(ProductionRun, ProductionRun.id == ProductionConsumption.production_run_id).join(Product, Product.id == ProductionRun.product_id)
        
        if start_date:
            query = query.filter(ProductionRun.production_date >= start_date)
        if end_date:
            query = query.filter(ProductionRun.production_date <= end_date)
            
        return query.order_by(ProductionRun.production_date.desc(), ProductionRun.id.desc()).all()

    # 12. Production Yield Report
    @staticmethod
    def get_production_yield_report(start_date=None, end_date=None):
        runs = ReportService.get_production_report(start_date, end_date)
        return [{
            'run_number': r.run_number,
            'date': r.production_date,
            'product_name': r.product.name,
            'batch_count': r.batch_count,
            'expected_output': r.expected_output,
            'actual_output': r.actual_output,
            'yield_variance_pct': r.yield_variance_pct,
            'yield_variance_alert': r.yield_variance_alert,
            'status': r.status
        } for r in runs]

    # 13. Wastage Report (Damaged packaging and lost yield)
    @staticmethod
    def get_wastage_report(start_date=None, end_date=None):
        query = db.session.query(
            ProductionRun.run_number,
            ProductionRun.production_date,
            Product.name.label('product_name'),
            ProductionConsumption.item_type,
            ProductionConsumption.item_id,
            ProductionConsumption.damaged_quantity,
            ProductionConsumption.unit,
            (ProductionConsumption.damaged_quantity * ProductionConsumption.unit_cost).label('wastage_cost')
        ).join(ProductionRun, ProductionRun.id == ProductionConsumption.production_run_id).join(Product, Product.id == ProductionRun.product_id).filter(ProductionConsumption.damaged_quantity > 0)
        
        if start_date:
            query = query.filter(ProductionRun.production_date >= start_date)
        if end_date:
            query = query.filter(ProductionRun.production_date <= end_date)
            
        return query.order_by(ProductionRun.production_date.desc()).all()

    # 14. Cost Per Packet Report
    @staticmethod
    def get_cost_per_packet_report(start_date=None, end_date=None):
        runs = ReportService.get_production_report(start_date, end_date)
        return [{
            'run_number': r.run_number,
            'date': r.production_date,
            'product_name': r.product.name,
            'good_packets': r.actual_output,
            'material_cost': r.total_material_cost,
            'packaging_cost': r.total_packaging_cost,
            'labour_cost': r.labour_cost,
            'gas_power_cost': r.gas_cost + r.power_cost,
            'total_cost': r.total_production_cost,
            'cost_per_packet': r.cost_per_packet,
            'selling_price': r.product.selling_price,
            'gross_contribution': r.gross_contribution_per_packet,
            'gross_margin_pct': r.gross_margin_percentage
        } for r in runs]

    # 15. Payment Collection Report
    @staticmethod
    def get_payment_collection_report(start_date=None, end_date=None):
        query = Payment.query
        if start_date:
            query = query.filter(Payment.payment_date >= start_date)
        if end_date:
            query = query.filter(Payment.payment_date <= end_date)
        return query.order_by(Payment.payment_date.desc(), Payment.id.desc()).all()

    # 16. Customer Outstanding Report
    @staticmethod
    def get_customer_outstanding_report():
        customers = Customer.query.filter_by(is_active=True).all()
        report = []
        for c in customers:
            total_inv = sum(inv.grand_total for inv in c.invoices if inv.status == 'posted')
            total_paid = sum(a.allocated_amount for inv in c.invoices for a in inv.allocations)
            total_credits = sum(cn.amount for inv in c.invoices for cn in inv.credit_notes)
            due = total_inv - total_paid - total_credits
            if due > Decimal('0.00'):
                report.append({
                    'customer_id': c.id,
                    'customer_name': c.name,
                    'state': c.state,
                    'mobile': c.mobile_number,
                    'credit_limit': c.credit_limit,
                    'total_invoiced': total_inv,
                    'total_paid': total_paid,
                    'outstanding_due': due
                })
        return report

    # 17. Customer Ageing Report
    @staticmethod
    def get_customer_ageing_report(ref_date=None):
        return PaymentService.get_customer_ageing_report(ref_date)

    # Export Helpers: CSV & Excel
    @staticmethod
    def export_to_csv(headers, rows):
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        for r in rows:
            writer.writerow(r)
        output.seek(0)
        return output.getvalue()

    @staticmethod
    def export_to_excel(title, headers, rows):
        wb = Workbook()
        ws = wb.active
        ws.title = title[:30]
        
        # Header Styling
        header_fill = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        border = Border(left=Side(style='thin', color='E2E8F0'),
                        right=Side(style='thin', color='E2E8F0'),
                        top=Side(style='thin', color='E2E8F0'),
                        bottom=Side(style='thin', color='E2E8F0'))
        
        ws.append(headers)
        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_num)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            
        for row in rows:
            ws.append([str(val) if isinstance(val, Decimal) else val for val in row])
            
        for row_cells in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=len(headers)):
            for cell in row_cells:
                cell.border = border
                
        # Auto-adjust column widths
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = col[0].column_letter
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)
            
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output
