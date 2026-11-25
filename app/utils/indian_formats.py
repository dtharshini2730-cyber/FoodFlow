from datetime import datetime, date
from decimal import Decimal


def get_current_financial_year(for_date=None):
    """
    Returns Indian financial year string (e.g. '2024-25').
    Indian FY starts on April 1 and ends on March 31.
    """
    if for_date is None:
        for_date = date.today()
    elif isinstance(for_date, datetime):
        for_date = for_date.date()
        
    year = for_date.year
    month = for_date.month
    
    if month >= 4:
        # April to December: Year to Year+1
        start_year = year
        end_year = year + 1
    else:
        # January to March: Year-1 to Year
        start_year = year - 1
        end_year = year
        
    return f"{start_year}-{str(end_year)[-2:]}"


def format_inr_text(number):
    """Formats numeric value to Indian currency string (e.g. ₹1,25,000.00)."""
    if number is None:
        return "₹0.00"
    try:
        dec = Decimal(str(number))
    except Exception:
        return f"₹{number}"
        
    is_neg = dec < 0
    dec = abs(dec)
    parts = f"{dec:.2f}".split('.')
    integer_part = parts[0]
    decimal_part = parts[1]
    
    if len(integer_part) > 3:
        last_three = integer_part[-3:]
        remaining = integer_part[:-3]
        groups = []
        while len(remaining) > 2:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            groups.insert(0, remaining)
        formatted_int = ','.join(groups) + ',' + last_three
    else:
        formatted_int = integer_part
        
    prefix = "-₹" if is_neg else "₹"
    return f"{prefix}{formatted_int}.{decimal_part}"
