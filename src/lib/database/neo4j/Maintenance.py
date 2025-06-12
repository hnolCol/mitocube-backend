from neo4j import Driver, Result 
from typing import List, Literal
import pandas as pd 

from lib.database.abstract.Maintenance import MaintenanceABC, MaintenanceEventABC
from config.models.maintenance import MaintenanceBaseModel, MaintenanceInsertModel, MaintenanceEventInsertModel, MaintenanceEventModel #,InstrumentMaintenanceModel

REQUIRED_COLUMNS = ["tag","text","description","priority"]


class Neo4JMaintenanceEvent(MaintenanceEventABC):
    def __init__(self, driver : Driver):
        self._driver = driver 
    
    def exists(self, tag : str) ->  bool:
        ""
        
        query = "WITH EXISTS {(me:MaintenanceEvent) WHERE me.tag = $tag} as me_exists RETURN me_exists"
        r = self._driver.execute_query(query, tag = tag, result_transformer_=Result.value)
        return r[0]
        
    def get(self, tags : List[str] = None, limit : int = 50) -> List[MaintenanceEventModel]:
        
        query = "MATCH (av:AttributeValue)-[:HAS_EVENT]->(me:MaintenanceEvent)<-[CREATED]-(u:User) " 
        
        if tags is not None:
            query += "WHERE me.tag in $tags "
            
        query += ("MATCH (me)-[:PERFORMED]->(m:Maintenance) "
                  "WITH  collect(m.tag) as maintenance_tags, me, u, av ")
        query += "RETURN {user_tag : u.tag, instrument_tag : av.tag, description : me.description, costs : me.costs, maintenance_tags : maintenance_tags} ORDER BY me.timestamp DESC limit $limit"
        r = self._driver.execute_query(query, routing_="r", limit = limit, result_transformer_=Result.value) 

        print(r)
        
        
        
    def insert(self, maintenance_event : MaintenanceEventInsertModel):
        "Inserts a maintenance event"
        query = (
            "MERGE (me:MaintenanceEvent {tag : $maintenance_event.tag}) "
            "SET me.created_at = timestamp(), me.costs = $maintenance_event.costs,  "
            "me.description = $maintenance_event.description "
            "WITH me "
            "MATCH (av:AttributeValue {tag : $maintenance_event.instrument_tag}) "
            "MATCH (u:User {tag : $maintenance_event.user_tag}) "
            "MERGE (u)-[:CREATED]->(me) "
            "MERGE (av)-[:HAS_EVENT]->(me) "
            "WITH me "
            "UNWIND $maintenance_event.maintenance_tags as m_tag "
            "MATCH (m:Maintenance {tag : m_tag}) "
            "MERGE (me)-[:PERFORMED]->(m) "
            
        )
        
        self._driver.execute_query(query, maintenance_event = maintenance_event.model_dump(exclude_none=True))
        


class Neo4JMaintenance(MaintenanceABC):
    ""
    def __init__(self, driver : Driver) -> None:
        
        self._driver = driver 
        
        
    def _utils_insert_from_file(self, path_to_file : str = "/Users/hnolte/Desktop/maintenance.txt", *args, **kwargs) -> None:
        ""    
        maintenance_file : pd.DataFrame = pd.read_csv(path_to_file, *args, **kwargs)
        
        if not all(column_name in maintenance_file.columns for column_name in REQUIRED_COLUMNS):
            raise ValueError(f"The file does not contain one of the following column names: {REQUIRED_COLUMNS}")
        
        records = [MaintenanceInsertModel(**r) for r in maintenance_file.to_dict(orient="records")]
        
        query = (
            "UNWIND $ms as m_prop " 
            "MERGE (m:Maintenance {tag : m_prop.tag}) "
            "SET m.description = m_prop.description, m.text = m_prop.text, m.s = m_prop.s, "
            "m.priority = m_prop.priority, m.created_at = timestamp() "
            "RETURN count(m)"
            ) 
        
        r = self._driver.execute_query(query, routing_="w", ms = [maintenance.model_dump(exclude_none=True) for maintenance in records])
        
    # def insert_maintenance_event(self, 
    #                        tags : List[str], 
    #                        instrument_tag : str, 
    #                        user_tag : str, 
    #                        spare_part_tags : List[str],
    #                        costs : float = 0, 
    #                        description : str = ""):
        
    #     query = (
    #         "MATCH (m:Maintenance {tag : $tag}) "
    #         "MATCH (av:AttributeValue {tag : $instrument_tag}) "
    #         "CREATE (m)<-[r:REQUIRED]-(av) " 
    #         "SET r.created_at = timestamp(), r.user_tag = $user_tag, r.costs = $costs, r.description = $description "
    #         "UNWIND $spare_part_tags as sp_tag "
    #         "MATCH (sp:SparePart {tag : sp_tag}) "
    #         "CREATE"
    #     )
    #     r = self._driver.execute_query(query, 
    #                                    routing_="w",
    #                                    user_tag = user_tag, 
    #                                    instrument_tag = instrument_tag, 
    #                                    spare_part_tags = spare_part_tags,
    #                                    tags = tags, 
    #                                    costs = costs, 
    #                                    description = description)
        
        
    def count(self) -> int:
        ""
        query = "MATCH (m:Maintenance) RETURN count(m)"
        
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value)
        if len(r) == 0: return 0 #should not happen.
        return r[0]
    
    
    def costs(self, instrument_tag  : str = None) -> float:
        "Sum of costs in total or by instrument"
        query = "MATCH (m:Maintenance)<-[r:REQUIRED]-(:AttributeValue) "
        
        if instrument_tag  is None:
            query += "WHERE av.tag = $instrument_tag  "
        
        query += "RETURN sum(r.costs)"
        
        r = self._driver.execute_query(query, instrument_tag  = instrument_tag , routing_= "r", result_transformer_ = Result.value)
        return r[0]
    
    def exists(self, tag : str) -> bool:
        query = (
            "WITH EXISTS {(m:Maintenance {tag : $tag})} as maintenance_exists "
            "RETURN maintenance_exists "
        )    
        r = self._driver.execute_query(query, tag = tag, result_transformer_=Result.value)
        return r[0]
    
    def history(self, instrument_tag : str = None, limit : int = 50, sort_by : Literal["costs", "created_at"] = None, descending : bool = True) -> List:
        ""
        query = "MATCH (m:Maintenance)<-[r:REQUIRED]-(av:AttributeValue) "
        
        if instrument_tag is not None:
            "WHERE av.tag = $instrument_tag "
            
        query += ("RETURN {maintenance_tag : m.tag, instrument_tag : av.tag, user_tag : r.user_tag, "
                "created_at : r.created_at, costs : r.costs, description : r.description}  "
                )
        if sort_by is not None:
            if sort_by not in ["costs", "created_at"]: 
                raise ValueError("sort_by is not defined correctly.")
            
            query += f"ORDER BY r.{sort_by} {'DESC' if descending else ''}"
            
        query += " LIMIT $limit"
        
        r = self._driver.execute_query(query, routing_="r", instrument_tag = instrument_tag, limit = limit, result_transformer_=Result.value)
        
        return r
                
    
    def insert(self, maintenance : MaintenanceInsertModel):
    
        query = (
            "MERGE (m:Maintenance {tag : $maintenance.tag}) "
            "SET m.description = $maintenance.description, m.text = $maintenance.text, "
            "m.priority = $maintenance.priority, m.timestamp = timestamp() "
            )
        
        self._driver.execute_query(query, routing_="w", maintenace = maintenance)

    
    def get(self, tags : List[str] = None) -> List[MaintenanceBaseModel]:
        
        query = "MATCH (m:Maintenance) "
        
        if tags is not None: 
            query += "WHERE m.tag in $tags "
            
        query += "RETURN {text : m.text, description : m.description, tag : m.tag} "
        
        r = self._driver.execute_query(query, routing_="r", tags = tags, result_transformer_=Result.value)
        
        return [MaintenanceBaseModel(**ri) for ri in r]
    
    def find(self, query : str, limit : int = 50) -> List[MaintenanceBaseModel]:
        
        query_string = query.lower()
        query = (
            "MATCH (m:Maintenance) "
            "WHERE m.s CONTAINS $query_string "
            "RETURN {text : m.text, description : m.description, tag : m.tag} ORDER BY m.priority LIMIT $limit "
            )
        
    
        r = self._driver.execute_query(
            query,
            query_string = query_string, 
            limit = limit, 
            routing_ = "r",
            result_transformer_ = Result.value)
        
        return [MaintenanceBaseModel(**ri) for ri in r]