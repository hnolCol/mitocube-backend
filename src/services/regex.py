import re
from typing import List

def build_regex_for_search(search_strings : List[str]) -> str:
    """
    Creates a regex to search for groups (e.g. multiple strings)
    following the style ({string1})|({string}).

    Parameters
    ----------
    search_strings : List[str]
        The search strings (groups) the regex should be created for.

    Returns
    -------
    str 
        Regex of style ({string1})|({string}).
    """
    reg_exp = r'' #init reg ex
    for n,search_string in enumerate(search_strings):
        if n == 0:
            reg_exp += r'(?:{})|'.format(search_string)
        else:
            reg_exp += r'({})|'.format(search_string)
    reg_exp = reg_exp[:-1] #strip of last |
    
    return reg_exp

def get_cursor_from_header_link(link : str) -> str:
    """Gets the cursor from a header link when pagination is used"""
    cursor = re.search('cursor=(.*)&',link).group(0)[:-1]
    return cursor.split("=")[1]

