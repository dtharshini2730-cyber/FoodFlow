import pytest
from datetime import date
from decimal import Decimal
from app.services.stock_service import StockService, InsufficientStockException, DuplicatePostingException


def test_purchase_increases_stock(session, sample_master_data):
    d = sample_master_data
    # Opening stock is 0
    assert StockService.get_stock_balance('raw_material', d['flour'].id) == Decimal('0.000')
    
    # Post purchase of 60 kg flour
    purchase_data = {
        'supplier_id': d['supplier'].id,
        'purchase_date': '2024-04-01',
        'supplier_invoice_no': 'INV-001',
        'items': [{
            'item_type': 'raw_material',
            'item_id': d['flour'].id,
            'quantity': Decimal('60.000'),
            'unit': 'kg',
            'unit_rate': Decimal('45.0000'),
            'tax_rate': Decimal('5.00')
        }]
    }
    purchase = StockService.post_purchase(purchase_data, d['admin'].id)
    session.commit()
    
    # Stock must increase to 60 kg
    assert StockService.get_stock_balance('raw_material', d['flour'].id) == Decimal('60.000')
    assert d['flour'].current_rate == Decimal('45.0000')


def test_duplicate_purchase_posting_prevented(session, sample_master_data):
    d = sample_master_data
    purchase_data = {
        'supplier_id': d['supplier'].id,
        'purchase_date': '2024-04-01',
        'supplier_invoice_no': 'INV-DUP-01',
        'items': [{
            'item_type': 'raw_material',
            'item_id': d['flour'].id,
            'quantity': Decimal('10.000'),
            'unit': 'kg',
            'unit_rate': Decimal('40.0000'),
            'tax_rate': Decimal('5.00')
        }]
    }
    # First post succeeds
    StockService.post_purchase(purchase_data, d['admin'].id)
    session.commit()
    
    # Second post with identical supplier invoice must raise DuplicatePostingException
    with pytest.raises(DuplicatePostingException):
        StockService.post_purchase(purchase_data, d['admin'].id)


def test_insufficient_stock_rejected(session, sample_master_data):
    d = sample_master_data
    # Available flour is 0, attempting to issue 10 kg must raise InsufficientStockException
    with pytest.raises(InsufficientStockException):
        StockService.record_movement(
            item_type='raw_material',
            item_id=d['flour'].id,
            movement_date=date(2024, 4, 1),
            movement_type='production_issue',
            quantity=Decimal('10.000'),
            unit='kg',
            direction='OUT',
            source_document_type='Test',
            user_id=d['admin'].id
        )


def test_stock_ledger_closing_formula(session, sample_master_data):
    d = sample_master_data
    # Receipts: 100 kg, Issues: 40 kg -> Closing: 60 kg
    StockService.record_movement(
        item_type='raw_material',
        item_id=d['flour'].id,
        movement_date=date(2024, 4, 1),
        movement_type='opening_stock',
        quantity=Decimal('100.000'),
        unit='kg',
        direction='IN',
        source_document_type='Opening',
        user_id=d['admin'].id
    )
    StockService.record_movement(
        item_type='raw_material',
        item_id=d['flour'].id,
        movement_date=date(2024, 4, 2),
        movement_type='production_issue',
        quantity=Decimal('40.000'),
        unit='kg',
        direction='OUT',
        source_document_type='Production',
        user_id=d['admin'].id
    )
    session.commit()
    
    assert StockService.get_stock_balance('raw_material', d['flour'].id) == Decimal('60.000')
