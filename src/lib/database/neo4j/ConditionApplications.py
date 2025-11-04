from lib.database.abstract.ConditionApplications import ConditionApplicationABC
from config.models.conditions_applications import ConditionApplicationItemModel, ConditionApplicationTreeModel
from services.condition_application import build_condition_application_tree
from typing import Dict, List 
from neo4j import Driver, Result 

class Neo4JConditionApplications(ConditionApplicationABC):
    
    def __init__(self, driver : Driver, *args, **kwargs) -> None:
        
        self._driver = driver

    def exists(self, tag : str) -> bool: 
        """If a submission tag is associated with a condition application. 
        Condition applications are always associated with submissions, but such submissions that 
        have specific conditions applied to them.

        Parameters
        ----------
        tag : str
            _description_

        Returns
        -------
        bool
            _description_
        """
        
        query = "WITH EXISTS {(ca:ConditionApplication {tag : $ca_tag})} as exists RETURN exists"
        r = self._driver.execute_query(query, routing_="r", ca_tag=tag, result_transformer_=Result.value)
       
        return r[0] if len(r) > 0 else False

    def get(self, tag: str) -> List[List[ConditionApplicationItemModel]]:
        "Return the condition application details. Returns None if not found."

        query = (
            "MATCH (ca:ConditionApplication {tag : $ca_tag}) "
            "MATCH p = ((ca)-[:HAS_VALUE*0..]->(cv:ConditionValue)) "
            "WITH ca, collect(nodes(p)) AS paths "
            "RETURN [path IN paths | "
            "            [n IN path | "
            "                { "
            "                       label: labels(n)[0], " #label of the node 
            "                   tag : n.tag, "
            "                   trait_tag: [(n)-[:INSTANCE_OF]->(t:Trait) | t.tag][0], "
            "                    attribute_tag: [(n)-[:OF_ATTRIBUTE]->(a:Attribute) | a.tag][0], "
            "                    value : n.value      "           
            "                    } "
            "            ] "
            "    ] AS children "
        )

        r = self._driver.execute_query(query, routing_="r", ca_tag=tag, result_transformer_=Result.value)
        return [[ConditionApplicationItemModel(**rii) for rii in ri] for ri in r[0]] if len(r) > 0 and len(r[0]) > 0 else [[]]


    def get_tree(self, tag: str) -> ConditionApplicationTreeModel:
        "Return a human-readable text representation of the condition application."

        ca = self.get(tag)
        return build_condition_application_tree(ca)

    def insert(self, condition_application : Dict) -> bool:
        """Inserts a new condition application into the database.

        Parameters
        ----------
        condition_application : Dict
            The condition application data to insert.

        Returns
        -------
        bool
            True if the insertion was successful, False otherwise.
        """

    def delete(self, tag: str) -> bool:
        """Deletes a condition application from the database.

        Parameters
        ----------
        tag : str
            The tag of the condition application to delete.

        Returns
        -------
        bool
            True if the deletion was successful, False otherwise.
        """
        
        
    def find(self, samples_only : bool = True, submission_tag : str = None, attribute_tag : str = None, trait_tag : str = None, sort_by_frequency : bool = True, limit : int = None) -> List[str]:
        "Returns the tags of matching condition applications"
        
        query = "MATCH (ca:ConditionApplication)<-[r:HAS_APPLICATION]-(:Sample|Submission)"
        
        if samples_only:
            if submission_tag is not None:
                query += "WHERE EXISTS {(ca)<-[:HAS_APPLICATION]-(s:Sample)-[:HAS_SAMPLE]-(submission:Submission {tag : $submission_tag})} "
            else:
                query += "WHERE EXISTS {(ca)<-[:HAS_APPLICATION]-(s:Sample)} "
        
        if attribute_tag is not None or trait_tag is not None:
            if not samples_only:
                query += "WHERE "
            else:
                query += "AND "
                
            if attribute_tag is not None:
                query += "(EXISTS {(ca)-[:OF_ATTRIBUTE]->(a:Attribute {tag : $attribute_tag})} OR EXISTS {(ca)-[:HAS_VALUE*0..]->(:ConditionValue)-[:OF_ATTRIBUTE]->(:Attribute {tag : $attribute_tag})}) "
            if trait_tag is not None:
                if attribute_tag is not None:
                    query += "AND "
                query += "(EXISTS {(ca)-[:INSTANCE_OF]->(t:Trait {tag : $trait_tag})} OR EXISTS {(ca)-[:HAS_VALUE*0..]->(:ConditionValue)-[:INSTANCE_OF]->(t:Trait {tag : $trait_tag})}) "
        
        query += "RETURN ca.tag, count(r) as freq "

        if sort_by_frequency:
            query += "ORDER BY freq DESC "
        if limit is not None:
            query += "LIMIT $limit "

        r = self._driver.execute_query( query_= query, routing_="r", submission_tag=submission_tag, attribute_tag=attribute_tag, trait_tag=trait_tag, limit = limit, result_transformer_=Result.value)
        print(r)

        return r