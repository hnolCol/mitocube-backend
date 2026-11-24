import re
from typing import List

def tokenize_search_string(search_string: str) -> List[str]:
    """
    Splits a free-text search string into lowercase tokens on whitespace.
    A multi-word search (e.g. "WT MB") is matched token-wise with AND semantics,
    so it still matches strings like "MB10 treated WT" (order-independent).

    Parameters
    ----------
    search_string : str
        The raw search string.

    Returns
    -------
    List[str]
        The lowercase tokens; empty list for empty/whitespace-only/non-string input.
    """
    if not isinstance(search_string, str):
        return []
    return [token.lower() for token in re.split(r"\s+", search_string.strip()) if token]

def build_token_contains_clause(field: str, search_string: str, prefix: str = "token") -> tuple:
    """
    Builds a Cypher clause requiring every token of the search string to be contained
    in the given field, e.g. "a.s CONTAINS $token_0 AND a.s CONTAINS $token_1".

    Parameters
    ----------
    field : str
        The node property to search, e.g. "a.s".
    search_string : str
        The raw search string (tokenized internally).
    prefix : str
        The parameter name prefix; the i-th token is bound to $<prefix>_<i>.

    Returns
    -------
    tuple
        (clause, params) where clause is the Cypher fragment ("true" for no tokens)
        and params maps the parameter names to the lowercase tokens.
    """
    tokens = tokenize_search_string(search_string)
    params = {}
    clauses = []
    for index, token in enumerate(tokens):
        name = f"{prefix}_{index}"
        clauses.append(f"{field} CONTAINS ${name}")
        params[name] = token
    return (" AND ".join(clauses) if clauses else "true"), params

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
        if n == 0: #avoid extract group warning.
            reg_exp += r'(?:{})|'.format(search_string) 
        else:
            reg_exp += r'({})|'.format(search_string)
    reg_exp = reg_exp[:-1] #strip of last |
    
    return reg_exp

def get_cursor_from_header_link(link : str) -> str:
    """Gets the cursor from a header link when pagination is used"""
    cursor = re.search('cursor=(.*)&',link).group(0)[:-1]
    return cursor.split("=")[1]

