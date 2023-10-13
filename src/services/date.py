import time 
from datetime import datetime, timezone

def get_time_stamp() -> float:
    """Returns the current time in seconds from epoch"""
    return time.time()

def get_current_date_as_string() -> str:
    """Returns current date as string"""
    return datetime.now().strftime("%Y-%m-%d")


def get_current_datetime() -> datetime:
    """Returns UTC timezone datetime"""
    return datetime.now(timezone.utc)

