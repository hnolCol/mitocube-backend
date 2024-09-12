from typing import List, Dict, Tuple 
from neo4j import Driver, Result
import pandas as pd 

from lib.data.database.abstract.News import NewsABC

from lib.data.database.abstract.Attributes import AttributesABC
from config.settings.metatexts import MetaTexts
from config.models.submissions.submissions import MinimalMetadataModel, DatasetSubmissionModel
from config.models.user import UserModel 
from collections import OrderedDict

from config.models.news.news import NewsModel




class Neo4JNews(NewsABC):

    def __init__(self, driver : Driver) -> None:
        
        self._driver = driver
        
    def exists(self,tag) -> bool:
        ""
        query = (
            "WITH EXISTS {(n:News {tag : $tag})} as exists "
            "RETURN exists "
        )    
        r = self._driver.execute_query(query, tag = tag, result_transformer_=Result.value)
        return r[0]
    
    def get(self, tags: List[str] = None, limit: int = 10) -> List[ NewsModel]:
        ""
        query = ("MATCH (u:User)-[:CREATED]->(n:News)-[:HAS_CONTENT]->(c:Content) ")
        
        if not (tags is None or (isinstance(tags,list) and len(tags) == 0)):
            query += "WHERE n.tag in $tags "

        query += (
            "OPTIONAL MATCH (p:Protein)<-[:ASSOCIATED_WITH]-(n) "
            "OPTIONAL MATCH (submission:Submission)<-[:ASSOCIATED_WITH]-(n) "
            "WITH [p IN collect(DISTINCT p) | p.tag] as features, [submission IN collect(DISTINCT submission) | submission.tag] as submissions, n, c, u "
            "WITH {tag : n.tag, content : c.content, user_tag : u.tag, created_at : n.created_at, submission_tags : submissions, feature_tags : features} "
            " as news "
            "RETURN news ORDER BY news.created_at DESC ")
            
        if limit is not None:
            query += "LIMIT $limit"
    
        r = self._driver.execute_query(query, routing_="r", limit=limit, tags = tags, result_transformer_=Result.value)
        return [ NewsModel(**n) for n in r]
        
        
    def insert(self, news:  NewsModel) -> bool:
        
        if self.exists(tag = news.tag):
            raise ValueError("Tag is already in the database.")
        
        query = (
            "CREATE (n:News {tag : $news.tag})-[r:HAS_CONTENT]->(c:Content)"
            "SET n.created_at = timestamp(), c.content = $news.content, r.news_tag = $news.tag "
            "WITH n, c "
            "MATCH (u:User {tag : $news.user_tag}) "
            "CREATE (u)-[:CREATED]->(n) "
            "WITH n "
            "UNWIND $news.submission_tags as sub "
            "MATCH (submission:Submission {tag  : sub}) "
            "CREATE (n)-[:ASSOCIATED_WITH]->(submission) "
            "WITH n "
            "UNWIND $news.feature_tags as feature "
            "MATCH (p:Protein {tag : feature}) "
            "CREATE (n)-[:ASSOCIATED_WITH]->(p) "
            "RETURN n"
        )
        
        r = self._driver.execute_query(query, news = news.model_dump(exclude_none=True), result_transformer_=Result.value)
        print(r)
    
    def update(self, news:  NewsModel) -> bool:
        return super().update(news)
    
    
    def delete(self, tag: str) -> bool:
        return super().delete(tag)