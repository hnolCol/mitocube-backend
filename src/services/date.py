import time 
from datetime import datetime, timezone, date

def get_time_stamp() -> float:
    """Returns the current time in milliseconds from epoch to align the format to the databases."""
    return time.time() * 1000

def get_current_date_as_string() -> str:
    """Returns current date as string"""
    return datetime.now().strftime("%Y-%m-%d")


def get_current_datetime() -> datetime:
    """Returns UTC timezone datetime"""
    return datetime.now(timezone.utc)

def validate_date_string(date_string : str, date_format : str = "%Y%m%d"):
    """
    Raises
    --------
    ValueError 
        If date_string is not of the expected format.
    """
    try:
        datetime.strptime(date_string, date_format)
        return True
    except:
        return False 