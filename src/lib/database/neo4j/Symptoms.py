from neo4j import Driver, Result 
from typing import List, Literal
import pandas as pd 

from lib.database.abstract.Symptoms import SymptomABC

from config.models.symptoms import SymptomModel, SymptomResponseModel

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
        
    def exists(self, tag : str) -> bool:
        "Checks if a symptom exists"
        
        query = "WITH EXISTS {(s:Symptom {tag : $tag})} as symptom_exists RETURN symptom_exists "
        exists = self._driver.execute_query(query, tag = tag, routing_ = "r")    
        return exists[0]
        
    def find(self, search_string : str = "", limit : int = 20) -> List[str]:
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
        query = "MATCH (s:Symptom) "
        if len(search_string) > 0:
            query += "WHERE s.s CONTAINS $search_string "
        query += "RETURN s.tag ORDER BY s.priority LIMIT $limit "
               
        symptoms = self._driver.execute_query(query, 
                                              search_string = search_string.lower(), 
                                              limit = limit, 
                                              routing_="r", 
                                              result_transformer_=Result.value)
        
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
        
        return SymptomResponseModel(**symptom[0])
    
    
    