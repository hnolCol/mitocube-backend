import re

_WRITE_KEYWORDS = (
    "CREATE", "MERGE", "SET", "DELETE", "DETACH", "REMOVE", "DROP",
    "LOAD", "FOREACH", "CALL", "IMPORT", "ADMIN", "INDEX", "CONSTRAINT",
)

_STRING_LITERAL_RE = re.compile(r"\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*'")

_PASSWORD_ACCESS_RE = re.compile(
    r"\.\s*password\b|\[\s*['\"]password['\"]\s*\]|\{\s*\.?password\s*\}|['\"]password['\"]\s*:"
)


def validate_read_only_query(query: str) -> None:
    """Rejects queries that are not plain read-only Cypher.

    String literals are stripped before the keyword scan so that keywords
    inside quoted values cannot be used to smuggle write clauses, and
    quoted values cannot hide a keyword from the scan. Password access is
    checked on the raw query text so quoted forms cannot hide it either.
    """
    stripped = _STRING_LITERAL_RE.sub("''", query)
    upper = stripped.upper()
    for keyword in _WRITE_KEYWORDS:
        if re.search(rf"\b{keyword}\b", upper):
            raise ValueError(f"Only read queries are allowed (forbidden clause: {keyword}).")
    if _PASSWORD_ACCESS_RE.search(query.lower()):
        raise ValueError("Access to password fields is not allowed.")
