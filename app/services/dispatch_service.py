from datetime import datetime
from decimal import Decimal
from app import db
from app.models.dispatch import Dispatch, DispatchItem
from app.models.sales import SalesOrder
from app.models.billing import Invoice
from app.models.audit import AuditLog
from app.services.stock_service import StockService, InsufficientStockException


class DispatchService:
    
    @classmethod
    def create_dispatch(cls, dispatch_data, user_id):
        """
        Executes a dispatch atomically:
        1. Verifies order and stock availability.
        2. Deducts finished goods stock via StockLedger.
        3. Updates dispatched quantities on order items.
        4. Updates order status ('Partially Dispatched' or 'Dispatched').
        5. Logs audit event.
        """
        sales_order_id = int(dispatch_data['sales_order_id'])
        order = SalesOrder.query.with_for_update().get(sales_order_id)
        if not order:
            raise ValueError(f"SalesOrder #{sales_order_id} not found.")
            
        if order.status not in ['Approved', 'Invoiced', 'Partially Dispatched']:
            raise ValueError(f"Cannot dispatch order in '{order.status}' status. Order must be Approved or Invoiced.")
            
        invoice_id = dispatch_data.get('invoice_id')
        if invoice_id:
            invoice_id = int(invoice_id)
            
        dispatch_date = dispatch_data.get('dispatch_date')
        if isinstance(dispatch_date, str):
            dispatch_date = datetime.strptime(dispatch_date, '%Y-%m-%d').date()
        elif not dispatch_date:
            dispatch_date = datetime.utcnow().date()
            
        count = Dispatch.query.count() + 1
        dispatch_number = f"DSP-{datetime.now().year}-{count:04d}"
        
        dispatch = Dispatch(
            dispatch_number=dispatch_number,
            sales_order_id=order.id,
            invoice_id=invoice_id,
            dispatch_date=dispatch_date,
            vehicle_no=dispatch_data.get('vehicle_no', ''),
            remarks=dispatch_data.get('remarks', ''),
            created_by_id=user_id
        )
        db.session.add(dispatch)
        db.session.flush()
        
        # Items to dispatch: list of dicts with {product_id, quantity}
        items_data = dispatch_data.get('items', [])
        total_order_qty = sum(item.quantity for item in order.items)
        
        for item_data in items_data:
            product_id = int(item_data['product_id'])
            qty_to_dispatch = Decimal(str(item_data['quantity']))
            
            if qty_to_dispatch <= Decimal('0'):
                continue
                
            # Find matching order item
            order_item = order.items.filter_by(product_id=product_id).first()
            if not order_item:
                continue
                
            remaining_to_dispatch = order_item.quantity - order_item.dispatched_quantity
            if qty_to_dispatch > remaining_to_dispatch:
                raise ValueError(
                    f"Cannot dispatch {qty_to_dispatch} pkts for {order_item.product.name}. "
                    f"Only {remaining_to_dispatch} pkts remaining on order."
                )
                
            # Verify stock availability in finished goods
            current_fg = StockService.get_stock_balance('finished_good', product_id)
            if current_fg < qty_to_dispatch:
                shortage = qty_to_dispatch - current_fg
                raise InsufficientStockException(
                    f"Insufficient finished goods stock for '{order_item.product.name}'. "
                    f"Available: {current_fg} pkts, Dispatch Requested: {qty_to_dispatch} pkts, Shortage: {shortage} pkts."
                )
                
            # Create dispatch item
            d_item = DispatchItem(
                dispatch_id=dispatch.id,
                product_id=product_id,
                quantity=qty_to_dispatch,
                unit=order_item.product.unit
            )
            db.session.add(d_item)
            
            # Update order item dispatched quantity
            order_item.dispatched_quantity += qty_to_dispatch
            
            # Reduce stock via StockLedger
            StockService.record_movement(
                item_type='finished_good',
                item_id=product_id,
                movement_date=dispatch_date,
                movement_type='sales_dispatch',
                quantity=qty_to_dispatch,
                unit=order_item.product.unit,
                direction='OUT',
                source_document_type='Dispatch',
                source_document_id=dispatch.id,
                user_id=user_id
            )
            
        # Update Order Status
        total_dispatched_now = sum(item.dispatched_quantity for item in order.items)
        if total_dispatched_now >= total_order_qty:
            order.status = 'Dispatched'
        else:
            order.status = 'Partially Dispatched'
            
        AuditLog.log(
            user_id=user_id,
            action='DISPATCH',
            module='Dispatch',
            record_id=dispatch.id,
            new_values={'dispatch_number': dispatch_number, 'order_status': order.status},
            description=f"Recorded dispatch {dispatch_number} for Order {order.order_number} (New Status: {order.status})."
        )
        return dispatch
