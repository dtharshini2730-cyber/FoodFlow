import io
from datetime import datetime
from decimal import Decimal
from flask import current_app
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from app import db
from app.models.billing import Invoice, InvoiceItem, CreditNote
from app.models.sales import SalesOrder
from app.models.audit import AuditLog
from app.utils.indian_formats import format_inr_text, get_current_financial_year


class InvoiceService:
    
    @classmethod
    def generate_invoice_number(cls, financial_year):
        """Generates sequential invoice number for a given Financial Year (e.g. FF/24-25/0001)."""
        count = Invoice.query.filter_by(financial_year=financial_year).count() + 1
        fy_short = financial_year.replace('20', '') if '20' in financial_year else financial_year
        return f"FF/{fy_short}/{count:04d}"

    @classmethod
    def create_invoice_from_order(cls, order_id, user_id):
        """
        Generates a GST invoice from an approved sales order.
        """
        order = SalesOrder.query.with_for_update().get(order_id)
        if not order:
            raise ValueError(f"SalesOrder #{order_id} not found.")
        if order.status not in ['Approved', 'Partially Dispatched']:
            raise ValueError(f"Cannot generate invoice for order in '{order.status}' status. Order must be Approved.")
            
        financial_year = get_current_financial_year()
        invoice_number = cls.generate_invoice_number(financial_year)
        customer = order.customer
        
        factory_name = current_app.config['SUPPLIER_FACTORY_NAME']
        factory_address = current_app.config['SUPPLIER_FACTORY_ADDRESS']
        factory_gstin = current_app.config['SUPPLIER_GSTIN']
        
        is_interstate = customer.is_interstate
        place_of_supply = customer.state
        
        invoice = Invoice(
            invoice_number=invoice_number,
            sales_order_id=order.id,
            customer_id=customer.id,
            invoice_date=datetime.utcnow().date(),
            financial_year=financial_year,
            place_of_supply=place_of_supply,
            supplier_name=factory_name,
            supplier_address=factory_address,
            supplier_gstin=factory_gstin,
            customer_name=customer.name,
            customer_address=customer.address,
            customer_gstin=customer.gstin or 'URP',
            is_interstate=is_interstate,
            status='posted',
            created_by_id=user_id
        )
        db.session.add(invoice)
        db.session.flush()
        
        total_taxable = Decimal('0.00')
        cgst_total = Decimal('0.00')
        sgst_total = Decimal('0.00')
        igst_total = Decimal('0.00')
        
        for order_item in order.items:
            product = order_item.product
            taxable_val = order_item.taxable_amount
            gst_rate = order_item.gst_rate
            
            if is_interstate:
                cgst_r = Decimal('0.00')
                cgst_amt = Decimal('0.00')
                sgst_r = Decimal('0.00')
                sgst_amt = Decimal('0.00')
                igst_r = gst_rate
                igst_amt = order_item.igst_amount
            else:
                cgst_r = gst_rate / Decimal('2.0')
                cgst_amt = order_item.cgst_amount
                sgst_r = gst_rate / Decimal('2.0')
                sgst_amt = order_item.sgst_amount
                igst_r = Decimal('0.00')
                igst_amt = Decimal('0.00')
                
            inv_item = InvoiceItem(
                invoice_id=invoice.id,
                product_id=product.id,
                hsn_code=product.hsn_code,
                quantity=order_item.quantity,
                unit_price=order_item.unit_price,
                taxable_value=taxable_val,
                gst_rate=gst_rate,
                cgst_rate=cgst_r,
                cgst_amount=cgst_amt,
                sgst_rate=sgst_r,
                sgst_amount=sgst_amt,
                igst_rate=igst_r,
                igst_amount=igst_amt,
                total_amount=order_item.total_amount
            )
            db.session.add(inv_item)
            
            total_taxable += taxable_val
            cgst_total += cgst_amt
            sgst_total += sgst_amt
            igst_total += igst_amt
            
        invoice.total_taxable = total_taxable
        invoice.cgst_total = cgst_total
        invoice.sgst_total = sgst_total
        invoice.igst_total = igst_total
        invoice.grand_total = total_taxable + cgst_total + sgst_total + igst_total
        
        order.status = 'Invoiced'
        
        AuditLog.log(
            user_id=user_id,
            action='POST',
            module='Invoices',
            record_id=invoice.id,
            new_values={'invoice_number': invoice_number, 'grand_total': str(invoice.grand_total)},
            description=f"Generated Tax Invoice {invoice_number} for Order {order.order_number} (₹{invoice.grand_total:.2f})."
        )
        return invoice

    @classmethod
    def create_credit_note(cls, invoice_id, amount, reason, user_id):
        """
        Creates a Credit Note against an invoice for returns or adjustments.
        """
        invoice = Invoice.query.with_for_update().get(invoice_id)
        if not invoice:
            raise ValueError(f"Invoice #{invoice_id} not found.")
            
        amount = Decimal(str(amount))
        if amount <= Decimal('0'):
            raise ValueError("Credit note amount must be positive.")
        if amount > invoice.outstanding_amount + invoice.total_allocated:
            raise ValueError("Credit note amount cannot exceed invoice total.")
            
        count = CreditNote.query.count() + 1
        fy = invoice.financial_year
        cn_number = f"CN/{fy.replace('20', '')}/{count:04d}"
        
        cn = CreditNote(
            credit_note_number=cn_number,
            invoice_id=invoice.id,
            customer_id=invoice.customer_id,
            credit_date=datetime.utcnow().date(),
            amount=amount,
            reason=reason,
            created_by_id=user_id
        )
        db.session.add(cn)
        
        AuditLog.log(
            user_id=user_id,
            action='POST',
            module='Invoices',
            record_id=cn.id,
            new_values={'credit_note_number': cn_number, 'amount': str(amount)},
            description=f"Issued Credit Note {cn_number} against Invoice {invoice.invoice_number}: ₹{amount:.2f} ({reason})."
        )
        return cn

    @classmethod
    def generate_invoice_pdf(cls, invoice_id):
        """
        Generates a professional GST Tax Invoice PDF using ReportLab.
        Returns bytes buffer.
        """
        invoice = Invoice.query.get(invoice_id)
        if not invoice:
            raise ValueError(f"Invoice #{invoice_id} not found.")
            
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=12 * mm,
            rightMargin=12 * mm,
            topMargin=12 * mm,
            bottomMargin=12 * mm
        )
        
        styles = getSampleStyleSheet()
        normal = styles['Normal']
        
        title_style = ParagraphStyle(
            'InvTitle',
            parent=normal,
            fontName='Helvetica-Bold',
            fontSize=16,
            leading=20,
            textColor=colors.HexColor('#1E293B')
        )
        subtitle_style = ParagraphStyle(
            'InvSub',
            parent=normal,
            fontName='Helvetica',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#64748B')
        )
        bold_style = ParagraphStyle(
            'InvBold',
            parent=normal,
            fontName='Helvetica-Bold',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#1E293B')
        )
        small_style = ParagraphStyle(
            'InvSmall',
            parent=normal,
            fontName='Helvetica',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#334155')
        )
        
        elements = []
        
        # Header Table: Company details on left, Invoice details on right
        supplier_info = f"""<b>{invoice.supplier_name}</b><br/>
{invoice.supplier_address}<br/>
<b>GSTIN:</b> {invoice.supplier_gstin}<br/>
<b>State:</b> Tamil Nadu (Code: 33)
"""
        inv_meta = f"""<b>TAX INVOICE</b><br/>
<b>Invoice No:</b> {invoice.invoice_number}<br/>
<b>Date:</b> {invoice.invoice_date.strftime('%d-%m-%Y')}<br/>
<b>Place of Supply:</b> {invoice.place_of_supply}<br/>
<b>State Code:</b> {'29' if invoice.is_interstate else '33'}
"""
        header_table = Table(
            [[Paragraph(supplier_info, small_style), Paragraph(inv_meta, small_style)]],
            colWidths=[100 * mm, 86 * mm]
        )
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 4 * mm))
        
        # Bill To Table
        bill_to = f"""<b>BILL TO / RECIPIENT:</b><br/>
<b>Name:</b> {invoice.customer_name}<br/>
<b>Address:</b> {invoice.customer_address}<br/>
<b>GSTIN:</b> {invoice.customer_gstin or 'URP (Unregistered Person)'}<br/>
<b>State:</b> {invoice.place_of_supply}
"""
        order_meta = f"""<b>ORDER & DISPATCH DETAILS:</b><br/>
<b>Order No:</b> {invoice.sales_order.order_number}<br/>
<b>Order Date:</b> {invoice.sales_order.order_date.strftime('%d-%m-%Y')}<br/>
<b>Payment Terms:</b> Immediate / Credit<br/>
<b>Supply Type:</b> {'Interstate (IGST)' if invoice.is_interstate else 'Intrastate (CGST + SGST)'}
"""
        customer_table = Table(
            [[Paragraph(bill_to, small_style), Paragraph(order_meta, small_style)]],
            colWidths=[100 * mm, 86 * mm]
        )
        customer_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(customer_table)
        elements.append(Spacer(1, 4 * mm))
        
        # Item Table Headers
        if invoice.is_interstate:
            item_headers = ['#', 'Item Description', 'HSN', 'Qty', 'Rate (₹)', 'Taxable (₹)', 'IGST %', 'IGST (₹)', 'Total (₹)']
            col_widths = [8*mm, 52*mm, 20*mm, 16*mm, 18*mm, 22*mm, 14*mm, 18*mm, 22*mm]
        else:
            item_headers = ['#', 'Item Description', 'HSN', 'Qty', 'Rate (₹)', 'Taxable (₹)', 'CGST', 'SGST', 'Total (₹)']
            col_widths = [8*mm, 48*mm, 18*mm, 16*mm, 18*mm, 22*mm, 18*mm, 18*mm, 24*mm]
            
        table_rows = [item_headers]
        
        for idx, item in enumerate(invoice.items, 1):
            prod_name = item.product.name if hasattr(item, 'product') and item.product else 'Food Item'
            if invoice.is_interstate:
                row = [
                    str(idx),
                    prod_name,
                    item.hsn_code,
                    f"{item.quantity:.0f}",
                    f"{item.unit_price:.2f}",
                    f"{item.taxable_value:.2f}",
                    f"{item.igst_rate:.1f}%",
                    f"{item.igst_amount:.2f}",
                    f"{item.total_amount:.2f}"
                ]
            else:
                row = [
                    str(idx),
                    prod_name,
                    item.hsn_code,
                    f"{item.quantity:.0f}",
                    f"{item.unit_price:.2f}",
                    f"{item.taxable_value:.2f}",
                    f"{item.cgst_amount:.2f}",
                    f"{item.sgst_amount:.2f}",
                    f"{item.total_amount:.2f}"
                ]
            table_rows.append(row)
            
        items_table = Table(table_rows, colWidths=col_widths)
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563EB')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (2, -1), 'LEFT'),
            ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 4 * mm))
        
        # Summary & Total Table
        summary_rows = [
            ['Total Taxable Value:', f"₹{invoice.total_taxable:.2f}"]
        ]
        if invoice.is_interstate:
            summary_rows.append(['Integrated GST (IGST 5%):', f"₹{invoice.igst_total:.2f}"])
        else:
            summary_rows.append(['Central GST (CGST 2.5%):', f"₹{invoice.cgst_total:.2f}"])
            summary_rows.append(['State GST (SGST 2.5%):', f"₹{invoice.sgst_total:.2f}"])
            
        summary_rows.append(['Grand Total (INR):', f"₹{invoice.grand_total:.2f}"])
        
        summary_table = Table(summary_rows, colWidths=[50 * mm, 36 * mm])
        summary_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F1F5F9')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        # Wrap summary aligned to right
        summary_wrapper = Table([['', summary_table]], colWidths=[100 * mm, 86 * mm])
        summary_wrapper.setStyle(TableStyle([('ALIGN', (1, 0), (1, 0), 'RIGHT')]))
        elements.append(summary_wrapper)
        elements.append(Spacer(1, 6 * mm))
        
        # Signatures & Declaration
        declaration = """<b>Declaration:</b> We declare that this invoice shows the actual price of the goods described and that all particulars are true and correct. This is a computer-generated invoice."""
        footer_table = Table([
            [Paragraph(declaration, small_style), Paragraph("<b>For " + invoice.supplier_name + "</b><br/><br/><br/>Authorized Signatory", small_style)]
        ], colWidths=[120 * mm, 66 * mm])
        footer_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(KeepTogether(footer_table))
        
        doc.build(elements)
        buffer.seek(0)
        return buffer
