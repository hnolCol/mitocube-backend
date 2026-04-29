from typing import List, Dict, Tuple, Literal
from neo4j import Driver, Result
import pandas as pd 

from lib.database.abstract.News import NewsABC

from lib.database.abstract.Attributes import AttributesABC
from config.settings.metatexts import MetaTexts
from config.models.submissions.submissions import MinimalMetadataModel, DatasetSubmissionModel
from config.models.user import UserModel 
from collections import OrderedDict

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
        
        query = ("MATCH (u:User)-[:CREATED]->(n:News)-[:HAS_CONTENT]->(c:Content) WHERE n.tag = $tag ")


        query += (
            "OPTIONAL MATCH (p:Protein)<-[:ASSOCIATED_WITH]-(n) "
            "OPTIONAL MATCH (submission:Submission)<-[:ASSOCIATED_WITH]-(n) "
            "WITH [p IN collect(DISTINCT p) | p.tag] as features, [submission IN collect(DISTINCT submission) | submission.tag] as submissions, n, c, u "
            "WITH {tag : n.tag, title : n.title, content : c.content, user_tag : u.tag, created_at : n.created_at, submission_tags : submissions, feature_tags : features} "
            " as news "
            "RETURN news ORDER BY news.created_at DESC ")
            
    
        r = self._driver.execute_query(query, routing_="r", tag = tag, result_transformer_=Result.value)
        return  NewsModel(**r[0])

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
        
        query = ("MATCH (n:News) RETURN n.tag ORDER BY n.created_at ")
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
    
    
    
    def insert(self, news:  NewsInsertModel) -> bool:

        if self.exists(tag = news.tag):
            raise ValueError("Tag is already in the database.")
        query = (
            "CREATE (n:News {tag : $news.tag})-[r:HAS_CONTENT]->(c:Content)"
            "SET n.created_at = timestamp(), c.content = $news.content, r.news_tag = $news.tag, n.title = $news.title "
            "WITH n, c "
            "MATCH (u:User {tag : $news.user_tag}) "
            "CREATE (u)-[:CREATED]->(n) "
            "WITH n "
            "UNWIND $news.submission_tags as sub "
            "MATCH (submission:Submission {tag  : sub}) "
            "MERGE (n)-[:ASSOCIATED_WITH]->(submission) "
            "WITH n "
            "UNWIND $news.feature_tags as feature "
            "MATCH (p:Protein {tag : feature}) "
            "CREATE (n)-[:ASSOCIATED_WITH]->(p) "
            "RETURN n"
        )
        
        r = self._driver.execute_query(query, news = news.model_dump(exclude_none=True), result_transformer_=Result.value)
        return True if r and len(r) > 0 else False
    
    def update(self, news:  NewsModel) -> bool:
        return super().update(news)
    
    
    def delete(self, tag: str) -> bool:
        "Deletes a news by its tag, returns True if deletion was successful."
        query = (
            "MATCH (n:News {tag : $tag})-[:HAS_CONTENT]->(c:Content) "
            "DETACH DELETE n, c "
            "RETURN COUNT(n) as count"
        )
        r = self._driver.execute_query(query, tag=tag, result_transformer_=Result.value)
        return True if r and len(r) > 0 else False