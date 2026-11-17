from lib.database.abstract.OpenAi import OpenAI, OpenAIClient
from lib.database.neo4j.query_guard import validate_read_only_query
from neo4j import Driver, Result


class Neo4JOpenAI(OpenAIClient):
    def __init__(self, driver: Driver) -> None:
        super().__init__()
        self.driver = driver

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
        validate_read_only_query(query)
        result = self.driver.execute_query(query, routing_="r", result_transformer_=Result.data)
        return result
