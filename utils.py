import re
import datetime
from typing import Any, Optional
import pandas as pd
from .config import logger

def clean_and_parse_numeric(val: Any) -> float:
    """
    Safely converts a numeric value or string to float.
    Handles currency symbols, commas, and trailing/leading whitespaces.
    Returns 0.0 if parsing fails or input is null.
    """
    if val is None or pd.isna(val):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ["nan", "null", "none", "", "#value!"]:
        return 0.0
    
    # Remove currency symbols, commas, and other non-numeric chars except . and -
    cleaned = re.sub(r"[^\d\.\-]", "", val_str)
    try:
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        logger.warning(f"Failed to parse numeric value: {val_str}")
        return 0.0

def parse_date(val: Any) -> Optional[datetime.date]:
    """
    Safely parses a date string into a datetime.date object.
    Supports standard ISO format (YYYY-MM-DD), DD-MM-YYYY, etc.
    """
    if val is None or pd.isna(val):
        return None
    if isinstance(val, (datetime.date, datetime.datetime)):
        if isinstance(val, datetime.datetime):
            return val.date()
        return val
        
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ["nan", "null", "none", "", "-"]:
        return None
        
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.datetime.strptime(val_str, fmt).date()
        except ValueError:
            continue
            
    logger.debug(f"Could not parse date string: {val_str}")
    return None

def format_indian_currency(amount: float) -> str:
    """
    Formats a number into Indian Rupee format (Lakhs/Crores).
    E.g. 1,00,000 or 1,00,00,000.
    """
    amount = round(amount, 2)
    s = str(amount)
    parts = s.split('.')
    integer_part = parts[0]
    decimal_part = parts[1] if len(parts) > 1 else "00"
    if len(decimal_part) == 1:
        decimal_part += "0"
        
    # Handle negative values
    is_negative = integer_part.startswith('-')
    if is_negative:
        integer_part = integer_part[1:]
        
    n = len(integer_part)
    if n <= 3:
        formatted = integer_part
    else:
        last_three = integer_part[-3:]
        remaining = integer_part[:-3]
        # Group remaining digits in pairs
        pairs = []
        while len(remaining) > 2:
            pairs.append(remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            pairs.append(remaining)
        pairs.reverse()
        formatted = ",".join(pairs) + "," + last_three
        
    prefix = "-₹" if is_negative else "₹"
    return f"{prefix}{formatted}.{decimal_part}"

def handle_exceptions(default_return: Any = None):
    """
    Decorator to safely catch exceptions inside a function, log them,
    and return a default value.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
                return default_return
        return wrapper
    return decorator