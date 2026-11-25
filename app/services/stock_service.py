from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import func
from app import db
from app.models.inventory import StockLedger
from app.models.master import RawMaterial, PackagingMaterial, Product
from app.models.audit import AuditLog


class InsufficientStockException(Exception):
    """Raised when an operation would cause stock to become negative."""
    pass


class DuplicatePostingException(Exception):
    """Raised when an operation is posted more than once."""
    pass


class StockService:
    
    @staticmethod
    def get_stock_balance(item_type, item_id):
        """
        Calculates closing stock from posted ledger entries.
        Closing stock = Receipts (IN) - Issues (OUT)
        """
        total_in = db.session.query(func.coalesce(func.sum(StockLedger.quantity), 0)).filter(
            StockLedger.item_type == item_type,
            StockLedger.item_id == item_id,
            StockLedger.direction == 'IN'
        ).scalar()
        
        total_out = db.session.query(func.coalesce(func.sum(StockLedger.quantity), 0)).filter(
            StockLedger.item_type == item_type,
            StockLedger.item_id == item_id,
            StockLedger.direction == 'OUT'
        ).scalar()
        
        return Decimal(str(total_in)) - Decimal(str(total_out))
    
    @staticmethod
    def get_stock_item_details(item_type, item_id):
        """Fetch model instance for a given item type and ID."""
        if item_type == 'raw_material':
            return RawMaterial.query.get(item_id)
        elif item_type == 'packaging_material':
            return PackagingMaterial.query.get(item_id)
        elif item_type == 'finished_good':
            return Product.query.get(item_id)
        return None
    
    @classmethod
    def record_movement(cls, item_type, item_id, movement_date, movement_type,
                        quantity, unit, direction, source_document_type,
                        source_document_id=None, unit_rate=Decimal('0.0000'),
                        batch_reference=None, user_id=None, allow_negative=False):
        """
        Records an atomic stock ledger entry with database locking and validation.
        Prevents negative stock and updates running balance.
        """
        quantity = Decimal(str(quantity))
        unit_rate = Decimal(str(unit_rate))
        if quantity <= Decimal('0'):
            raise ValueError("Movement quantity must be positive.")
        
        # Lock item record if applicable
        if item_type == 'raw_material':
            item = RawMaterial.query.with_for_update().get(item_id)
        elif item_type == 'packaging_material':
            item = PackagingMaterial.query.with_for_update().get(item_id)
        elif item_type == 'finished_good':
            item = Product.query.with_for_update().get(item_id)
        else:
            item = None
            
        if not item:
            raise ValueError(f"Item of type '{item_type}' with ID {item_id} not found.")
        
        # Calculate current balance before this movement
        current_balance = cls.get_stock_balance(item_type, item_id)
        
        if direction == 'OUT':
            if not allow_negative and current_balance < quantity:
                item_name = getattr(item, 'name', f"Item #{item_id}")
                shortage = quantity - current_balance
                raise InsufficientStockException(
                    f"Insufficient stock for '{item_name}'. Available: {current_balance} {unit}, "
                    f"Requested: {quantity} {unit}, Shortage: {shortage} {unit}."
                )
            new_balance = current_balance - quantity
        elif direction == 'IN':
            new_balance = current_balance + quantity
        else:
            raise ValueError(f"Invalid direction '{direction}'. Must be 'IN' or 'OUT'.")
        
        total_value = quantity * unit_rate
        
        ledger_entry = StockLedger(
            item_type=item_type,
            item_id=item_id,
            movement_date=movement_date,
            movement_type=movement_type,
            quantity=quantity,
            unit=unit,
            direction=direction,
            source_document_type=source_document_type,
            source_document_id=source_document_id,
            unit_rate=unit_rate,
            total_value=total_value,
            running_balance=new_balance,
            batch_reference=batch_reference,
            created_by_id=user_id
        )
        db.session.add(ledger_entry)
        return ledger_entry
    
    @classmethod
    def post_purchase(cls, purchase_data, user_id):
        """
        Posts a purchase:
        1. Creates Purchase record.
        2. Creates PurchaseItem records.
        3. Updates moving weighted-average valuation.
        4. Adds StockLedger entry (direction IN).
        5. Logs audit event.
        Idempotent: prevents duplicate submission.
        """
        from app.models.purchase import Purchase, PurchaseItem
        
        supplier_invoice_no = purchase_data.get('supplier_invoice_no', '').strip()
        supplier_id = purchase_data.get('supplier_id')
        
        # Duplicate check by supplier invoice
        existing = Purchase.query.filter_by(
            supplier_id=supplier_id,
            supplier_invoice_no=supplier_invoice_no
        ).first()
        if existing:
            raise DuplicatePostingException(
                f"Purchase with Supplier Invoice #{supplier_invoice_no} has already been posted (Purchase ID #{existing.purchase_number})."
            )
        
        # Generate sequential purchase number
        count = Purchase.query.count() + 1
        purchase_number = f"PUR-{datetime.now().year}-{count:04d}"
        
        purchase_date = purchase_data.get('purchase_date')
        if isinstance(purchase_date, str):
            purchase_date = datetime.strptime(purchase_date, '%Y-%m-%d').date()
            
        purchase = Purchase(
            purchase_number=purchase_number,
            supplier_id=supplier_id,
            purchase_date=purchase_date,
            supplier_invoice_no=supplier_invoice_no,
            status='posted',
            created_by_id=user_id
        )
        db.session.add(purchase)
        db.session.flush()
        
        total_taxable = Decimal('0.00')
        total_tax = Decimal('0.00')
        
        for item_data in purchase_data.get('items', []):
            item_type = item_data['item_type']
            item_id = int(item_data['item_id'])
            qty = Decimal(str(item_data['quantity']))
            rate = Decimal(str(item_data['unit_rate']))
            tax_rate = Decimal(str(item_data.get('tax_rate', '5.0')))
            
            taxable = qty * rate
            tax = taxable * (tax_rate / Decimal('100.0'))
            item_total = taxable + tax
            
            total_taxable += taxable
            total_tax += tax
            
            p_item = PurchaseItem(
                purchase_id=purchase.id,
                item_type=item_type,
                item_id=item_id,
                quantity=qty,
                unit=item_data['unit'],
                unit_rate=rate,
                tax_rate=tax_rate,
                tax_amount=tax,
                total_amount=item_total
            )
            db.session.add(p_item)
            
            # Update moving weighted-average valuation for raw materials
            if item_type == 'raw_material':
                material = RawMaterial.query.with_for_update().get(item_id)
                current_qty = cls.get_stock_balance('raw_material', item_id)
                current_rate = material.current_rate
                
                # Formula: (Previous stock value + New purchase value) / (Previous stock quantity + Purchased quantity)
                prev_value = current_qty * current_rate
                new_value = qty * rate
                new_total_qty = current_qty + qty
                
                if new_total_qty > Decimal('0'):
                    new_avg_rate = (prev_value + new_value) / new_total_qty
                else:
                    new_avg_rate = rate
                    
                material.current_rate = new_avg_rate
            elif item_type == 'packaging_material':
                material = PackagingMaterial.query.with_for_update().get(item_id)
                material.current_rate = rate
            
            # Add stock ledger entry
            cls.record_movement(
                item_type=item_type,
                item_id=item_id,
                movement_date=purchase_date,
                movement_type='purchase_receipt',
                quantity=qty,
                unit=item_data['unit'],
                direction='IN',
                source_document_type='Purchase',
                source_document_id=purchase.id,
                unit_rate=rate,
                user_id=user_id
            )
            
        purchase.total_taxable_amount = total_taxable
        purchase.total_tax_amount = total_tax
        purchase.grand_total = total_taxable + total_tax
        
        AuditLog.log(
            user_id=user_id,
            action='POST',
            module='Purchases',
            record_id=purchase.id,
            new_values={'purchase_number': purchase_number, 'grand_total': str(purchase.grand_total)},
            description=f"Posted purchase {purchase_number} from supplier #{supplier_id}."
        )
        return purchase
