

from lib.database.abstract.OpenAi import OpenAI, OpenAIClient
from neo4j import Driver, Result


class Neo4JOpenAI(OpenAIClient):
    def __init__(self, driver: Driver) -> None:
        super().__init__()
        self.driver = driver
    
        
        
        
    def execute_query(self, query: str) -> list[dict]:
        """Executes a cypher query and returns the result as a list of dictionaries.

        Parameters
        ----------
        query : str
            The cypher query to execute.

        Returns
        -------
        list[dict]
            The result of the query as a list of dictionaries.
        """
        if ("DELETE " in query.upper()) or ("REMOVE " in query.upper()) or ("CREATE " in query.upper()) or ("MERGE " in query.upper()):
            raise ValueError("Only read queries are allowed.")
        if (".password") in query.lower():
            raise ValueError("Access to password fields is not allowed.")
        
        result = self.driver.execute_query(query, routing_="r", result_transformer_=Result.data)
        return result