from neo4j import Driver, Result 
from typing import List, Literal
import pandas as pd 
from services.encryption import create_hierarchical_hash

from lib.database.abstract.Symptoms import SymptomABC

from config.models.symptoms import SymptomModel, SymptomResponseModel, SymptomInsertModel

class Neo4jSymptoms(SymptomABC):
    
    def __init__(self, driver : Driver):
        
        self._driver = driver 
    
    def _utils_insert_from_file(self, file_path : str = "", *args, **kwargs):
        ""
        
        symptoms = pd.read_csv(file_path, *args, **kwargs)
        #creating the models here checks if all the types are correct. 
        symptoms_models = [SymptomModel(**s, s = [s["text"],s["description"]]).model_dump(exclude_none=True) for s in symptoms.to_dict(orient="records")] 
        
        query = (
            "UNWIND $symptoms as s_props "
            "MERGE (s:Symptom {tag : s_props.tag}) "
            "ON CREATE "
            "SET s.created_at = timestamp(), s.description = s_props.description, s.priority = s_props.priority, s.s = s_props.s, s.text = s_props.text "
            "ON MATCH "
            "SET s.modified_at = timestamp(), s.description = s_props.description, s.priority = s_props.priority, s.s = s_props.s, s.text = s_props.text "
            "RETURN count(s) as count"
        )
    
        r = self._driver.execute_query(query, symptoms = symptoms_models, routing_="w", result_transformer_=Result.value)
        print(f"The database contains {r} symptoms")
        
    def count(self) -> int:
        """Returns the number of symptoms in 
        the database. 

        Returns
        -------
        int
            The number of symptoms in the database.
        """
        
        query = "MATCH (s:Symptom) RETURN count(s) as symptom_count "
        count = self._driver.execute_query(query, routing_="r", result_transformer_= Result.value)
        return count[0]
        
    def exists(self, tag : str) -> bool:
        "Checks if a symptom exists"
        
        query = "WITH EXISTS {(s:Symptom {tag : $tag})} as symptom_exists RETURN symptom_exists "
        exists = self._driver.execute_query(query, tag = tag, routing_ = "r")    
        return exists[0]
    
    def find(self, search_string: str = "", limit: int = 20, is_active: bool = True, sort : bool = True) -> List[str]:
        """Find symptoms by a search string. 

        Parameters
        ----------
        search_string : str, optional
            The query string, by default ""
        limit : int, optional
            The maximum number of symptoms to be returned., by default 20

        Returns
        -------
        List[str]
            The symptom tags. 
        """
        query = (
            "MATCH (s:Symptom) "
            "WHERE s.is_active = $is_active "
        )

        if len(search_string) > 0:
            query += "AND s.s CONTAINS $search_string "

        query += "RETURN s.tag " 
        
        if sort:
            query += "ORDER BY s.priority  "

        if limit is not None:
            query +=  "LIMIT $limit" 

        symptoms = self._driver.execute_query(query,
                                                search_string=search_string.lower(),
                                                limit=limit,
                                                is_active=is_active,
                                                routing_="r",
                                                result_transformer_=Result.value
                                            )

        return symptoms
    
    def get(self, tag : str) -> SymptomResponseModel:
        "" 
        
        if not self.exists(tag):
            raise ValueError("Tag not associated with a symptom.")
        
        query = (
            "MATCH (s:Symptom {tag : $tag}) "
            "return properties(s) "
        )
        
        
        symptom = self._driver.execute_query(query, tag = tag, routing_= "r", result_transformer_= Result.value)
        if len(symptom) == 0: 
            raise ValueError("Symptom tag found but no properties associated with it.")
        
        return SymptomResponseModel(**symptom[0])
    
    def get_text(self, tag : str) -> str:           
        """Get symptom texts by its tag. 

        Parameters
        ----------
            The symptom tag.

        Returns
        -------
        [str]
            The symptom text.
        """
        
        if not self.exists(tag):
            raise ValueError("Tag not associated with a symptom.")
        
        query = (
            "MATCH (s:Symptom {tag : $tag}) "
            "RETURN s.text as text "
        )
        
        text = self._driver.execute_query(query, tag = tag, routing_="r", result_transformer_= Result.value)
        return text[0]  
    
    def get_description(self, tag : str) -> str:    
        """Get symptom descriptions by its tag. 

        Parameters
        ----------
          The symptom tag.

        Returns
        -------
        str
            The symptom description.
        """
        
        if not self.exists(tag):
            raise ValueError("Tag not associated with a symptom.")
        
        query = (
            "MATCH (s:Symptom {tag : $tag}) "
            "RETURN s.description as description "
        )
        
        description = self._driver.execute_query(query, tag = tag, routing_="r", result_transformer_= Result.value)
        return description[0]
    
    def get_priority(self, tag : str) -> int:    
        """Get symptom priorities by its tag. 

        Parameters
        ----------
          The symptom tag.

        Returns
        -------
        int
            The symptom priority.
        """
        
        if not self.exists(tag):
            raise ValueError("Tag not associated with a symptom.")
        
        query = (
            "MATCH (s:Symptom {tag : $tag}) "
            "RETURN s.priority as priority "
        )
        
        priority = self._driver.execute_query(query, tag = tag, routing_="r", result_transformer_= Result.value)
        return priority[0]
    
    
    def insert(self, symptom :  SymptomInsertModel, user_tag : str, is_active : bool = True) -> bool:
        """Inserts a symptom in the database. 

        Parameters
        ----------
        symptom : SymptomModel
            The symptom to insert.

        Returns
        -------
        bool
            Indicates if the insertion was successful.
        """
        tag = create_hierarchical_hash([symptom.text, symptom.description])[:20]

        query = (
            "MATCH (u:User {tag: $user_tag}) "
            "MERGE (s:Symptom {tag: $tag}) "
            "ON CREATE SET s.is_active = true, "
            "              s.created_at = timestamp(), "
            "              s.description = $description, "
            "              s.priority = $priority, "
            "              s.s = toLower($text)+' '+toLower($description), "
            "              s.text = $text "
            "ON MATCH SET  s.modified_at = timestamp(), "
            "              s.description = $description, "
            "              s.priority = $priority, "
            "              s.s = toLower($text)+' '+toLower($description), "
            "              s.text = $text "
            "WITH u, s "
            "CREATE (u)-[:CREATED {created_at: timestamp()}]->(s) "
            "CREATE (u)-[:MODIFIED {modified_at: timestamp()}]->(s) "
            "RETURN true as ok"
)
        
        ok = self._driver.execute_query(query, 
                                        tag = tag,
                                        is_active = is_active,
                                        description = symptom.description,
                                        priority = symptom.priority,
                                        text = symptom.text,
                                        user_tag = user_tag,
                                        routing_="w",
                                        result_transformer_= Result.value)
        
        return ok[0]
    
    
    def update(self, tag: str, symptom :  SymptomInsertModel, user_tag : str) -> bool:
        """Updates a symptom in the database.

        Parameters
        ----------
        symptom : SymptomModel
            The symptom to update.
        user_tag : str
            The user tag of the user updating the symptom.

        Returns
        -------
        bool
            Indicates if the update was successful.
        """
        
        if not self.exists(tag):
            raise ValueError("Symptom does not exist and cannot be updated. Please use insert method.")

        query = (
                "MATCH (s:Symptom {tag: $tag})"
                "SET s.text = $text,"
                "    s.description = $description,"
                "    s.priority = $priority,"
                "    s.modified_at = timestamp(),"
                "    s.s = toLower($text) + ' ' + toLower($description)"
               "WITH s "
                "MATCH (u:User {tag: $user_tag}) "
                "MERGE (u)-[:MODIFIED {modified_at: timestamp()}]->(s) "
                "RETURN true AS ok"
    )

        ok = self._driver.execute_query(query,
                                        tag=tag,
                                        text=symptom.text,
                                        description=symptom.description,
                                        priority=symptom.priority,
                                        user_tag=user_tag,
                                        routing_="w",
                                        result_transformer_=Result.value,
                                    )

        return ok[0]
    
    def delete(self, tag : str, is_active : bool = False) -> bool:
        """Deletes a symptom from the database.

        Parameters
        ----------
        tag : str
            The symptom tag.

        Returns
        -------
        bool
            Indicates if the deletion was successful.
        """
        
        query = (
            "MATCH (s:Symptom {tag : $tag}) "
            "WHERE s.is_active = false "
            "RETURN true as ok "
        )
        
        ok = self._driver.execute_query(query, 
                                        tag = tag,
                                        is_active = is_active,
                                        routing_="w",
                                        result_transformer_= Result.value)
        
        return ok[0]