from datetime import datetime, date
from decimal import Decimal
from app import db
from app.models.payment import Payment, PaymentAllocation
from app.models.billing import Invoice
from app.models.master import Customer
from app.models.audit import AuditLog


class PaymentService:
    
    @classmethod
    def record_payment(cls, payment_data, user_id):
        """
        Records a customer payment and allocates to specified invoices.
        Validates that allocations do not exceed invoice outstanding or total payment amount.
        """
        customer_id = int(payment_data['customer_id'])
        customer = Customer.query.get(customer_id)
        if not customer:
            raise ValueError(f"Customer #{customer_id} not found.")
            
        amount = Decimal(str(payment_data['amount']))
        if amount <= Decimal('0.00'):
            raise ValueError("Payment amount must be greater than zero.")
            
        payment_date = payment_data.get('payment_date')
        if isinstance(payment_date, str):
            payment_date = datetime.strptime(payment_date, '%Y-%m-%d').date()
        elif not payment_date:
            payment_date = datetime.utcnow().date()
            
        count = Payment.query.count() + 1
        payment_number = f"PAY-{datetime.now().year}-{count:04d}"
        
        payment = Payment(
            payment_number=payment_number,
            customer_id=customer_id,
            payment_date=payment_date,
            amount=amount,
            payment_mode=payment_data.get('payment_mode', 'UPI'),
            reference_number=payment_data.get('reference_number', ''),
            remarks=payment_data.get('remarks', ''),
            created_by_id=user_id
        )
        db.session.add(payment)
        db.session.flush()
        
        # Allocations: list of dicts with {invoice_id, amount}
        allocations_data = payment_data.get('allocations', [])
        total_allocated = Decimal('0.00')
        
        # If no explicit allocations provided, auto-allocate FIFO to oldest open invoices
        if not allocations_data:
            open_invoices = Invoice.query.filter_by(
                customer_id=customer_id,
                status='posted'
            ).order_by(Invoice.invoice_date.asc()).all()
            
            remaining_to_allocate = amount
            for inv in open_invoices:
                if remaining_to_allocate <= Decimal('0.00'):
                    break
                due = inv.outstanding_amount
                if due > Decimal('0.00'):
                    alloc_amt = min(due, remaining_to_allocate)
                    alloc = PaymentAllocation(
                        payment_id=payment.id,
                        invoice_id=inv.id,
                        allocated_amount=alloc_amt
                    )
                    db.session.add(alloc)
                    total_allocated += alloc_amt
                    remaining_to_allocate -= alloc_amt
        else:
            for item in allocations_data:
                inv_id = int(item['invoice_id'])
                alloc_amt = Decimal(str(item['amount']))
                if alloc_amt <= Decimal('0.00'):
                    continue
                    
                invoice = Invoice.query.with_for_update().get(inv_id)
                if not invoice:
                    continue
                if invoice.customer_id != customer_id:
                    raise ValueError(f"Invoice {invoice.invoice_number} does not belong to customer {customer.name}.")
                    
                outstanding = invoice.outstanding_amount
                if alloc_amt > outstanding:
                    raise ValueError(
                        f"Cannot allocate ₹{alloc_amt:.2f} to Invoice {invoice.invoice_number}. "
                        f"Outstanding balance is only ₹{outstanding:.2f}."
                    )
                    
                alloc = PaymentAllocation(
                    payment_id=payment.id,
                    invoice_id=inv_id,
                    allocated_amount=alloc_amt
                )
                db.session.add(alloc)
                total_allocated += alloc_amt
                
            if total_allocated > amount:
                raise ValueError(
                    f"Total allocated amount (₹{total_allocated:.2f}) exceeds total payment amount (₹{amount:.2f})."
                )
                
        AuditLog.log(
            user_id=user_id,
            action='POST',
            module='Payments',
            record_id=payment.id,
            new_values={'payment_number': payment_number, 'amount': str(amount), 'allocated': str(total_allocated)},
            description=f"Received payment {payment_number} of ₹{amount:.2f} from {customer.name} via {payment.payment_mode}."
        )
        return payment

    @classmethod
    def get_customer_outstanding(cls, customer_id):
        """Calculates total outstanding balance for a customer."""
        invoices = Invoice.query.filter_by(customer_id=customer_id, status='posted').all()
        return sum(inv.outstanding_amount for inv in invoices)

    @classmethod
    def get_customer_ageing_report(cls, reference_date=None):
        """
        Generates customer receivables ageing report:
        Buckets: 0-30 days, 31-60 days, 61-90 days, >90 days.
        """
        if reference_date is None:
            reference_date = date.today()
            
        customers = Customer.query.filter_by(is_active=True).all()
        report = []
        
        for cust in customers:
            invoices = Invoice.query.filter_by(customer_id=cust.id, status='posted').all()
            b_0_30 = Decimal('0.00')
            b_31_60 = Decimal('0.00')
            b_61_90 = Decimal('0.00')
            b_90_plus = Decimal('0.00')
            total_due = Decimal('0.00')
            
            for inv in invoices:
                due = inv.outstanding_amount
                if due > Decimal('0.00'):
                    total_due += due
                    age_days = (reference_date - inv.invoice_date).days
                    if age_days <= 30:
                        b_0_30 += due
                    elif age_days <= 60:
                        b_31_60 += due
                    elif age_days <= 90:
                        b_61_90 += due
                    else:
                        b_90_plus += due
                        
            if total_due > Decimal('0.00'):
                report.append({
                    'customer_id': cust.id,
                    'customer_name': cust.name,
                    'state': cust.state,
                    'credit_limit': cust.credit_limit,
                    'bucket_0_30': b_0_30,
                    'bucket_31_60': b_31_60,
                    'bucket_61_90': b_61_90,
                    'bucket_90_plus': b_90_plus,
                    'total_outstanding': total_due
                })
                
        return report
