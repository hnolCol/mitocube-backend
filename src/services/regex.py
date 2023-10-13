import re

def get_cursor_from_header_link(link : str) -> str:
    """Gets the cursor from a header link when pagination is used"""
    cursor = re.search('cursor=(.*)&',link).group(0)[:-1]
    return cursor.split("=")[1]

