from typing import List, Dict, Tuple, Literal
from neo4j import Driver, Result
import pandas as pd 

from lib.database.abstract.News import NewsABC

from config.models.news.news import NewsModel, NewsInsertModel




class Neo4JNews(NewsABC):

    def __init__(self, driver : Driver) -> None:
        
        self._driver = driver
        
    def exists(self, tag : str) -> bool:
        "Check if a news item with the given tag exists."
        query = (
            "WITH EXISTS {(n:News {tag : $tag})} as exists "
            "RETURN exists "
        )    
        r = self._driver.execute_query(query, tag = tag, result_transformer_=Result.value)
        return r[0]
    
    def get(self, tag: str) -> NewsModel:
        """Returns the news item by its tag.
        Parameters
        ----------
        tag : str
            The tag of the news item to retrieve.   
        Returns
        -------
        NewsModel
            The news item with the given tag.
        """
        
        query = (
            "MATCH (n:News {tag: $tag})-[:HAS_CONTENT]->(c:Content) "
            "OPTIONAL MATCH (u:User)-[:CREATED]->(n) "
            "OPTIONAL MATCH (submission:Submission)<-[:ASSOCIATED_WITH]-(n) "
        )
        
        query += (
            "WITH n.tag as tag, n.title as title, c.content as content, "
            "COALESCE(u.tag, 'system') as user_tag, n.created_at as created_at, "
            "collect(DISTINCT submission.tag) as submission_tags_raw "
            "RETURN {tag: tag, title: title, content: content, user_tag: user_tag, "
            "created_at: created_at, submission_tags: [s IN submission_tags_raw WHERE s IS NOT NULL]} as news"
        )
        
        r = self._driver.execute_query(query, routing_="r", tag=tag, result_transformer_=Result.value)
        
        if not r or len(r) == 0:
            raise ValueError(f"News item with tag '{tag}' not found")
        
        return NewsModel(**r[0])

    def find(self, limit : int = None, order : Literal["desc","asc"] = "desc") -> List[str]:
        """
        Finds the latest news items, returns their tags. Limit can be set to restrict the number of items returned.
        Parameters
        ----------
        limit : int, optional
            The maximum number of news items to return, by default None
        order : Literal["desc","asc"], optional
            The order in which to return the news items, by default "desc"  
            
        Returns
        -------
        List[str]
            A list of news item tags.
        """
        
        query = ("MATCH (n:News)-[:HAS_CONTENT]->(c:Content) RETURN n.tag ORDER BY n.created_at ")
        
        if order == "desc":
            query += "DESC "
        elif order == "asc":
            query += "ASC "
        else: 
            raise ValueError("Order must be 'asc' or 'desc'.")
        
        if limit is not None:
            query += "LIMIT $limit"
        r = self._driver.execute_query(query, routing_="r", limit=limit, result_transformer_=Result.value)
        return r
    
    def insert(self, news: NewsInsertModel) -> bool:
        """Creates a new news item.
        Parameters
        ----------
        news : NewsInsertModel
            The news item to create.
        Returns
        -------
        bool
            True if insertion was successful.
        """
        if self.exists(tag=news.tag):
            raise ValueError("Tag is already in the database.")
        
        query = (
            "CREATE (n:News {tag: $news.tag})-[r:HAS_CONTENT]->(c:Content) "
            "SET n.created_at = timestamp(), c.content = $news.content, r.news_tag = $news.tag, n.title = $news.title "
            "WITH n "
            "OPTIONAL MATCH (u:User {tag: $news.user_tag}) "
            "FOREACH (user IN CASE WHEN u IS NOT NULL THEN [u] ELSE [] END | CREATE (user)-[:CREATED]->(n)) "
            "WITH n "
            "UNWIND COALESCE($news.submission_tags, []) as sub "
            "OPTIONAL MATCH (submission:Submission {tag: sub}) "
            "FOREACH (s IN CASE WHEN submission IS NOT NULL THEN [submission] ELSE [] END | MERGE (n)-[:ASSOCIATED_WITH]->(s)) "
            "RETURN n"
        )
        
        r = self._driver.execute_query(query, news=news.model_dump(exclude_none=True), result_transformer_=Result.value)
        return True if r and len(r) > 0 else False
    
    def update(self, news: NewsModel) -> bool:
        """Updates an existing news item.
        Parameters
        ----------
        news : NewsModel
            The news item with updated data.
        Returns
        -------
        bool
            True if update was successful.
        """
        if not self.exists(tag=news.tag):
            raise ValueError(f"News item with tag '{news.tag}' does not exist.")
        
        query = (
            "MATCH (n:News {tag: $tag})-[:HAS_CONTENT]->(c:Content) "
            "SET n.title = $title, c.content = $content, n.modified_at = timestamp() "
            "WITH n "
            "OPTIONAL MATCH (n)-[r:ASSOCIATED_WITH]->() "
            "DELETE r "
            "WITH n "
            "FOREACH (sub IN COALESCE($submission_tags, []) | "
            "  MERGE (submission:Submission {tag: sub}) "
            "  MERGE (n)-[:ASSOCIATED_WITH]->(submission)) "
            "RETURN n"
        )
        
        r = self._driver.execute_query(
            query,
            tag=news.tag,
            title=news.title,
            content=news.content,
            submission_tags=news.submission_tags or [],
            result_transformer_=Result.value
        )
        return True if r and len(r) > 0 else False
    
    def delete(self, tag: str) -> bool:
        """Deletes a news item by its tag, returns True if deletion was successful.
        Parameters
        ----------
        tag : str
            The tag of the news item to delete.
        Returns
        -------
        bool
            True if deletion was successful.
        """
        query = (
            "MATCH (n:News {tag : $tag})-[:HAS_CONTENT]->(c:Content) "
            "DETACH DELETE n, c "
            "RETURN COUNT(n) as count"
        )
        r = self._driver.execute_query(query, tag=tag, result_transformer_=Result.value)
        return True if r and len(r) > 0 else False