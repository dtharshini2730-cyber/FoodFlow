from datetime import datetime
from decimal import Decimal
from app import db
from app.models.sales import SalesOrder, SalesOrderItem
from app.models.master import Customer, Product
from app.models.audit import AuditLog
from app.services.stock_service import StockService


class OrderService:
    
    @classmethod
    def calculate_item_gst(cls, customer, selling_price, quantity, gst_rate=Decimal('5.0')):
        """
        Calculates taxable value and GST breakdown (CGST/SGST vs IGST).
        Customer in Tamil Nadu -> CGST (2.5%) + SGST (2.5%)
        Customer outside Tamil Nadu (Karnataka) -> IGST (5.0%)
        """
        taxable_amount = quantity * selling_price
        gst_fraction = gst_rate / Decimal('100.0')
        
        if customer.is_interstate:
            cgst_amount = Decimal('0.00')
            sgst_amount = Decimal('0.00')
            igst_amount = round(taxable_amount * gst_fraction, 2)
            total_tax = igst_amount
        else:
            half_rate = gst_fraction / Decimal('2.0')
            cgst_amount = round(taxable_amount * half_rate, 2)
            sgst_amount = round(taxable_amount * half_rate, 2)
            igst_amount = Decimal('0.00')
            total_tax = cgst_amount + sgst_amount
            
        total_amount = taxable_amount + total_tax
        return {
            'taxable_amount': taxable_amount,
            'cgst_amount': cgst_amount,
            'sgst_amount': sgst_amount,
            'igst_amount': igst_amount,
            'total_tax': total_tax,
            'total_amount': total_amount
        }
    
    @classmethod
    def create_sales_order(cls, order_data, salesman_id):
        """
        Creates a new salesman order with idempotency check.
        """
        customer_id = int(order_data['customer_id'])
        customer = Customer.query.get(customer_id)
        if not customer:
            raise ValueError(f"Customer #{customer_id} not found.")
            
        # Idempotency check
        idempotency_key = order_data.get('idempotency_key')
        if idempotency_key:
            existing = SalesOrder.query.filter_by(idempotency_key=idempotency_key).first()
            if existing:
                return existing
                
        # Generate sequential order number
        count = SalesOrder.query.count() + 1
        order_number = f"SO-{datetime.now().year}-{count:04d}"
        
        order_date = order_data.get('order_date')
        if isinstance(order_date, str):
            order_date = datetime.strptime(order_date, '%Y-%m-%d').date()
        elif not order_date:
            order_date = datetime.utcnow().date()
            
        sales_order = SalesOrder(
            order_number=order_number,
            customer_id=customer_id,
            salesman_id=salesman_id,
            order_date=order_date,
            status='Submitted',
            remarks=order_data.get('remarks', ''),
            idempotency_key=idempotency_key
        )
        db.session.add(sales_order)
        db.session.flush()
        
        total_taxable = Decimal('0.00')
        total_tax = Decimal('0.00')
        total_amount = Decimal('0.00')
        
        for item_data in order_data.get('items', []):
            product_id = int(item_data['product_id'])
            product = Product.query.get(product_id)
            if not product:
                continue
                
            qty = Decimal(str(item_data['quantity']))
            price = Decimal(str(item_data.get('unit_price', product.selling_price)))
            gst_rate = product.gst_rate
            
            calc = cls.calculate_item_gst(customer, price, qty, gst_rate)
            
            order_item = SalesOrderItem(
                sales_order_id=sales_order.id,
                product_id=product_id,
                quantity=qty,
                unit_price=price,
                gst_rate=gst_rate,
                taxable_amount=calc['taxable_amount'],
                cgst_amount=calc['cgst_amount'],
                sgst_amount=calc['sgst_amount'],
                igst_amount=calc['igst_amount'],
                total_amount=calc['total_amount']
            )
            db.session.add(order_item)
            
            total_taxable += calc['taxable_amount']
            total_tax += calc['total_tax']
            total_amount += calc['total_amount']
            
        sales_order.total_taxable_amount = total_taxable
        sales_order.total_tax_amount = total_tax
        sales_order.total_amount = total_amount
        
        AuditLog.log(
            user_id=salesman_id,
            action='CREATE',
            module='Orders',
            record_id=sales_order.id,
            new_values={'order_number': order_number, 'total_amount': str(total_amount)},
            description=f"Salesman #{salesman_id} submitted Order {order_number} for customer {customer.name} (₹{total_amount:.2f})."
        )
        return sales_order

    @classmethod
    def check_order_stock_availability(cls, order_id):
        """
        Checks whether stock is sufficient for all items in an order.
        Returns a list of items with requested, available, and shortage quantities.
        """
        order = SalesOrder.query.get(order_id)
        if not order:
            raise ValueError(f"SalesOrder #{order_id} not found.")
            
        results = []
        has_shortage = False
        
        for item in order.items:
            available = StockService.get_stock_balance('finished_good', item.product_id)
            shortage = max(Decimal('0.00'), item.quantity - available)
            if shortage > Decimal('0.00'):
                has_shortage = True
                
            results.append({
                'product_id': item.product_id,
                'product_name': item.product.name,
                'requested_qty': item.quantity,
                'available_qty': available,
                'shortage_qty': shortage,
                'has_sufficient_stock': shortage == Decimal('0.00')
            })
            
        return {
            'order_id': order.id,
            'order_number': order.order_number,
            'has_shortage': has_shortage,
            'items': results
        }

    @classmethod
    def approve_order(cls, order_id, user_id, updated_items=None):
        """
        Approves an order by Admin. Updates status to 'Approved'.
        """
        order = SalesOrder.query.with_for_update().get(order_id)
        if not order:
            raise ValueError(f"SalesOrder #{order_id} not found.")
        if order.status not in ['Submitted', 'Under Review']:
            raise ValueError(f"Order {order.order_number} is already in '{order.status}' status.")
            
        # If permitted quantities were edited by Admin
        if updated_items:
            total_taxable = Decimal('0.00')
            total_tax = Decimal('0.00')
            total_amount = Decimal('0.00')
            customer = order.customer
            
            for item in order.items:
                if item.id in updated_items:
                    item.quantity = Decimal(str(updated_items[item.id].get('quantity', item.quantity)))
                    item.unit_price = Decimal(str(updated_items[item.id].get('unit_price', item.unit_price)))
                    calc = cls.calculate_item_gst(customer, item.unit_price, item.quantity, item.gst_rate)
                    item.taxable_amount = calc['taxable_amount']
                    item.cgst_amount = calc['cgst_amount']
                    item.sgst_amount = calc['sgst_amount']
                    item.igst_amount = calc['igst_amount']
                    item.total_amount = calc['total_amount']
                    
                total_taxable += item.taxable_amount
                total_tax += (item.cgst_amount + item.sgst_amount + item.igst_amount)
                total_amount += item.total_amount
                
            order.total_taxable_amount = total_taxable
            order.total_tax_amount = total_tax
            order.total_amount = total_amount
            
        order.status = 'Approved'
        
        AuditLog.log(
            user_id=user_id,
            action='APPROVE',
            module='Orders',
            record_id=order.id,
            new_values={'status': 'Approved', 'total_amount': str(order.total_amount)},
            description=f"Order {order.order_number} approved by Admin #{user_id}."
        )
        return order

    @classmethod
    def reject_order(cls, order_id, reason, user_id):
        """
        Rejects an order by Admin with mandatory reason.
        """
        order = SalesOrder.query.with_for_update().get(order_id)
        if not order:
            raise ValueError(f"SalesOrder #{order_id} not found.")
            
        order.status = 'Rejected'
        order.rejection_reason = reason
        
        AuditLog.log(
            user_id=user_id,
            action='REJECT',
            module='Orders',
            record_id=order.id,
            new_values={'status': 'Rejected', 'reason': reason},
            description=f"Order {order.order_number} rejected: {reason}"
        )
        return order
