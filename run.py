import os
from app import create_app, db
from app.models import (
    User, Role, Unit, Customer, Supplier, RawMaterial, PackagingMaterial, Product,
    ProductBOM, BOMVersion, BOMItem, Purchase, PurchaseItem,
    StockLedger, StockAdjustment, StockBatch,
    ProductionRun, ProductionConsumption, ProductionOutput, ProductionOverhead,
    SalesOrder, SalesOrderItem, Invoice, InvoiceItem, CreditNote,
    Dispatch, DispatchItem, Payment, PaymentAllocation,
    AuditLog, SystemSetting
)

app = create_app(os.getenv('FLASK_ENV') or 'default')


@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'Role': Role,
        'Customer': Customer,
        'Supplier': Supplier,
        'RawMaterial': RawMaterial,
        'PackagingMaterial': PackagingMaterial,
        'Product': Product,
        'ProductBOM': ProductBOM,
        'BOMVersion': BOMVersion,
        'Purchase': Purchase,
        'StockLedger': StockLedger,
        'ProductionRun': ProductionRun,
        'SalesOrder': SalesOrder,
        'Invoice': Invoice,
        'Dispatch': Dispatch,
        'Payment': Payment,
        'AuditLog': AuditLog,
        'SystemSetting': SystemSetting
    }


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
