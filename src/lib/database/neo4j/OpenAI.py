

import re

from lib.database.abstract.OpenAi import OpenAI, OpenAIClient
from neo4j import Driver, Result


_WRITE_KEYWORDS = (
    "CREATE", "MERGE", "SET", "DELETE", "DETACH", "REMOVE", "DROP",
    "LOAD", "FOREACH", "CALL", "IMPORT", "ADMIN", "INDEX", "CONSTRAINT",
)

_STRING_LITERAL_RE = re.compile(r"\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*'")

_PASSWORD_ACCESS_RE = re.compile(
    r"\.\s*password\b|\[\s*['\"]password['\"]\s*\]|\{\s*\.?password\s*\}|['\"]password['\"]\s*:"
)


class Neo4JOpenAI(OpenAIClient):
    def __init__(self, driver: Driver) -> None:
        super().__init__()
        self.driver = driver

    @staticmethod
    def _validate_read_only(query: str) -> None:
        """Rejects queries that are not plain read-only Cypher.

        String literals are stripped before the keyword scan so that keywords
        inside quoted values cannot be used to smuggle write clauses, and
        quoted values cannot hide a keyword from the scan.
        """
        stripped = _STRING_LITERAL_RE.sub("''", query)
        upper = stripped.upper()
        for keyword in _WRITE_KEYWORDS:
            if re.search(rf"\b{keyword}\b", upper):
                raise ValueError(f"Only read queries are allowed (forbidden clause: {keyword}).")
        if _PASSWORD_ACCESS_RE.search(query.lower()):
            raise ValueError("Access to password fields is not allowed.")

    def execute_query(self, query: str) -> list[dict]:
        """Executes a cypher query and returns the result as a list of dictionaries.

        Only plain read queries are permitted; any write or schema clause,
        procedure call or password access is rejected before execution.

        Parameters
        ----------
        query : str
            The cypher query to execute.

        Returns
        -------
        list[dict]
            The result of the query as a list of dictionaries.
        """
        self._validate_read_only(query)
        result = self.driver.execute_query(query, routing_="r", result_transformer_=Result.data)
        return result