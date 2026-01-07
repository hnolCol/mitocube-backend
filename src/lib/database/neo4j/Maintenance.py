from neo4j import Driver, Result 
from typing import List, Literal
import pandas as pd 

from lib.database.abstract.Maintenance import MaintenanceProcedureABC, MaintenanceEventABC, ExternalServicesABC
from config.models.maintenance import  MaintenanceInsertModel, MaintenanceEventInsertModel, MaintenanceEventModel, MaintenanceProcedureResponseModel, MaintenanceStateResponseModel, MiantenanceProcedureInsertModel, ExternalServiceInsertModel, ExternalServiceModel #,InstrumentMaintenanceModel

REQUIRED_COLUMNS = ["tag","text","description"]


class Neo4JMaintenanceEvent(MaintenanceEventABC):
    def __init__(self, driver : Driver):
        self._driver = driver 
    
    def _utils_insert_maintenance_state_from_file(self, file_path : str = "/Users/hnolte/Documents/GitHub/mitocube-backend/resources/maintenance/maintenancestates.txt", *args, **kwargs) -> None:
        """
        Creates the maintenance state in the database if it does not exist. 
        Args and kwargs are passed to pandas.read_csv to read the file.
        """
        
        df = pd.read_csv(file_path, *args, **kwargs)
        print(df)
        #check if the required columns are present
        if not all([col in df.columns for col in REQUIRED_COLUMNS]):
            raise ValueError(f"The file {file_path} does not contain all required columns: {REQUIRED_COLUMNS}")
        
        
        query = (
            "UNWIND $rows as row  "
            "MERGE (ms:MaintenanceState {tag : row.tag}) "
            "ON CREATE "
            "SET ms.text = row.text, ms.description = row.description, ms.color = row.color, ms.created_at = timestamp() "
            "ON MATCH "
            "SET ms.text = row.text, ms.description = row.description, ms.color = row.color, ms.modified_at = timestamp() "
        )
        
        self._driver.execute_query(query, 
                                   rows = df.to_dict(orient="records"), 
                                   routing_="w", 
                                   result_transformer_=Result.value)
        
        
    
    def __build_filter_query(self, instrument_tag : str = None, user_tag : str = None, timestamp_min : float = None, timestamp_max : float = None) -> str:
        ""
        query = "MATCH (me:MaintenanceEvent) "
        
        if user_tag is not None:
            query += "-[:CREATED]->(u:User) "
            query += "WHERE u.tag = $user_tag "
        
        if instrument_tag is not None and user_tag is not None:
            query += "AND EXISTS{(t:Trait {tag : $instrument_tag})-[:HAS_EVENT]->(me)} "
        elif instrument_tag is not None and user_tag is None:
            query += "WHERE EXISTS{(t:Trait {tag : $instrument_tag})-[:HAS_EVENT]->(me)} "
        elif timestamp_max is not None and timestamp_min is not None:
            query += "WHERE " ## add where eif is not yot added .
            
        if timestamp_min is not None or timestamp_max is not None :
            #now add the actual query 
            if timestamp_min is not None:
                if any([instrument_tag is not None, user_tag is not None]):
                    query += "AND "
                query += "me.created_at >= $timestamp_min " 
            if timestamp_max is not None:
                if any([timestamp_min is not None, instrument_tag is not None, user_tag is not None]):
                    query += "AND "
                query += "me.created_at <= $timestamp_max "
            
        return query 
        
    
    def count(self, instrument_tag : str = None, user_tag : str = None, timestamp_min : float = None, timestamp_max : float = None) -> int:
        """Count the number of maintenance events given by the range (instrument, timestamp, user)

        Parameters
        ----------
        instrument_tag : str, optional
            _description_, by default None
        user_tag : str, optional
            _description_, by default None
        timestamp_min : float, optional
            _description_, by default None
        timestamp_max : float, optional
            _description_, by default None

        Returns
        -------
        int
            _description_
        """
        query = self.__build_filter_query(instrument_tag=instrument_tag, user_tag=user_tag, timestamp_max= timestamp_max, timestamp_min=timestamp_min)
        query += "RETURN count(me) "
        
        r = self._driver.execute_query(query, routing_="r", instrument_tag = instrument_tag, user_tag = user_tag, result_transformer_=Result.value)
        
        if len(r) == 1: return r[0]
        return 0
    
    
    def exists(self, tag : str) ->  bool:
        ""
        
        query = "WITH EXISTS {(me:MaintenanceEvent) WHERE me.tag = $tag} as me_exists RETURN me_exists"
        r = self._driver.execute_query(query, tag = tag, result_transformer_=Result.value)
        return r[0]
        
    def find(self, instrument_tag : str = None, user_tag : str = None, timestamp_min : float = None, timestamp_max : float = None, limit : int = 50, order_by_time : bool = True) -> List[str]:
        """
        Finds maintenance events by instrument_tag and user_tag.
        
        Parameters
        ----------
        instrument_tag : str, optional
            The tag of the instrument, by default None
        user_tag : str, optional
            The tag of the user, by default None
        timestamp_min : float, optional
            The minimum timestamp to filter the events, by default None 
        timestamp_max : float, optional     
            The maximum timestamp to filter the events, by default None
        limit : int, optional
            The maximum number of results to return, by default 50
        order_by_time : bool, optional      
            If True, the results are ordered by time, by default True
        
        Returns
        -------
        List[str]
            A list of maintenance events tags.
        """
        
        query = self.__build_filter_query(instrument_tag=instrument_tag, user_tag=user_tag, timestamp_max= timestamp_max, timestamp_min=timestamp_min)
        
        query += "RETURN me.tag "
        if order_by_time:
            query += "ORDER BY me.created_at DESC "
                    
        if limit is not None:
            query += "LIMIT $limit"
        
        r = self._driver.execute_query(query, routing_="r", instrument_tag = instrument_tag, user_tag = user_tag, limit = limit, result_transformer_=Result.value)
        print(r)
        return r
        
        
    def get(self, tag : str = None) -> MaintenanceEventModel|List[MaintenanceEventModel]|None:
        """Returns a maintenance event by its tag or all maintenance events if no tag is provided.

        Parameters
        ----------
        tag : str, optional
            The maintenance event models tag, by default None

        Returns
        -------
        MaintenanceEventModel|List[MaintenanceEventModel]|None
            _The maintenance event model if a tag is provided, a list of maintenance event models if no tag is provided, or None if no results are found.
        """
        query = "MATCH (AttributeGroup {tag : 'instrument'})<-[:PART_OF]-(a:Attribute)-[:HAS_TRAIT]->(t:Trait)-[:HAS_EVENT]->(me:MaintenanceEvent)<-[:CREATED]-(u:User) " 
        
        if tag is not None:
            query += "WHERE me.tag = $tag "
            
        query += "MATCH (t)-[r:IN_STATE]->(is:InstrumentState) WHERE r.maintenance_event_tag = me.tag "
        query += ("OPTIONAL MATCH (me)-[:PERFORMED]->(m:MaintenanceProcedure) "
                  "WITH  collect(m.tag) as maintenance_tags, me, u, t, is.tag as instrument_state_tag ")
        
        query += ("OPTIONAL MATCH (me)-[:HAS_SYMPTOM]->(s:Symptom) "
                  "WITH collect(s.tag) as symptom_tags, me, u, t, maintenance_tags, instrument_state_tag ")
    
        query += ("OPTIONAL MATCH (me)-[:UTILIZED]->(sp:SparePart) "
                  "WITH collect(sp.tag) as sparepart_tags, symptom_tags, me, u, t, maintenance_tags, instrument_state_tag ")
        
        query += ("OPTIONAL MATCH (me)-[:HAS_EXTERNAL_SERVICE]->(es:ExternalService) "
                  "WITH collect(es.tag) as external_service_tag, sparepart_tags, symptom_tags, me, u, t, maintenance_tags, instrument_state_tag ")

        query += ("RETURN {tag : me.tag, created_at : me.created_at, user_tag : u.tag, instrument_tag : t.tag, description : me.description, sparepart_tags : sparepart_tags, "
                "costs : me.costs, maintenance_procedure_tags : maintenance_tags, symptom_tags : symptom_tags, instrument_state_tag : instrument_state_tag, external_service_tag : external_service_tag} ORDER BY me.created_at DESC ")
        
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value, tag = tag) 
        print(r)
        if len(r) == 0:
            # If we have no results, we return None
            return None
        elif len(r) == 1:
            # If we have a single result, we can return it as a MaintenanceEventModel
            return MaintenanceEventModel(**r[0]) 
        else:
            # If we have multiple results, we return a list of MaintenanceEventModel
            return [MaintenanceEventModel(**ri) for ri in r]
        
    
    def costs(self, tag : str = None ) -> float:
        """Returns sum costs of a specific maintenance event"""
        
        
        query = "MATCH (me:MaintenanceEvent {tag : $maintenance_event_tag}) RETURN me.costs "
        
        r = self._driver.execute_query(query, routing_="r", maintenance_event_tag = tag, result_transformer_=Result.value)
        if len(r) == 0: return None # No maintenance event found for tag.
        return r[0]

        
    def delete(self, tag : str) -> None:
        """
        Deletes a maintenance event by its tag.
        
        Parameters
        ----------
        tag : str
            The tag of the maintenance event to delete.
        """
        
        query = "MATCH (me:MaintenanceEvent {tag : $tag}) DETACH DELETE me"
        
        self._driver.execute_query(query, routing_="w", tag = tag)
        
    def insert(self, maintenance_event : MaintenanceEventInsertModel):
        "Inserts a maintenance event"
        print(maintenance_event)
        print(maintenance_event.model_dump(exclude_none=True))
        query = (
            "MERGE (me:MaintenanceEvent {tag : $maintenance_event.tag}) "
            "SET me.created_at = timestamp(), me.costs = $maintenance_event.costs,  "
            "me.description = $maintenance_event.description "
            "WITH me "
            "MATCH (t:Trait {tag : $maintenance_event.instrument_tag})<-[:HAS_TRAIT]-(:Attribute)-[:PART_OF]->(ag:AttributeGroup {tag :'instrument'}) "
            "MATCH (u:User {tag : $maintenance_event.user_tag}) "
            "MATCH (is:InstrumentState {tag : $maintenance_event.instrument_state_tag}) "
            "MATCH (ms:MaintenanceState {tag : $maintenance_event.state_tag}) "
            "CREATE (me)-[:IN_STATE {created_at : timestamp(), maintenance_event_tag : $maintenance_event.tag, user_tag : u.tag}]->(ms) "
            "MERGE (u)-[:CREATED]->(me) "
            "MERGE (t)-[:HAS_EVENT]->(me) "
            "MERGE (t)-[r:IN_STATE]->(is) "
            "SET r.created_at = timestamp(), r.maintenance_event_tag = $maintenance_event.tag "
            "WITH me "
            "UNWIND $maintenance_event.symptom_tags as symptom_tag "
            "MATCH (s:Symptom {tag : symptom_tag}) "
            "MERGE (me)-[rs:HAS_SYMPTOM]->(s) "
            "SET rs.created_at = timestamp(), rs.maintenance_event_tag = $maintenance_event.tag "
            "WITH me "
            "UNWIND $maintenance_event.maintenance_tags as m_tag "
            "MATCH (m:MaintenanceProcedure {tag : m_tag}) "
            "MERGE (me)-[:PERFORMED]->(m) "
        )
        
        self._driver.execute_query(query, maintenance_event = maintenance_event.model_dump(exclude_none=True))
        

    def add_maintenance_procedure(self, tag : str, maintenance_procedure_tag : str, user_tag : str) -> List:
        """
        Adds a maintenance procedure to a maintenance event. If the maintenance procedure is already associated with the maintenance event, it will do nothing.
        
        Parameters
        ----------
        tag : str
            The tag of the maintenance event.
        maintenance_procedure_tag : str
            The tag of the maintenance procedure.
        user_tag : str 
            The user that added the maintenance procedure
        Returns
        -------
        List[str]
            A list of maintenance procedure tags that match the maintenance event.
        """
        
        query = (
            "MATCH (me:MaintenanceEvent {tag : $maintenance_event_tag}) "
            "MATCH (m:MaintenanceProcedure {tag : $maintenance_procedure_tag}) "
            "MERGE (me)-[r:PERFORMED]->(m) "
            "SET r.created_at = timestamp(), r.user_tag = $user_tag "
            "WITH me "
            "MATCH (me)-[:PERFORMED]->(m) "
            "RETURN m.tag " 
        )
        
        r = self._driver.execute_query(query, routing_="w", 
                                   maintenance_event_tag = tag, 
                                   maintenance_procedure_tag = maintenance_procedure_tag, 
                                   user_tag = user_tag,
                                   result_transformer_=Result.value)
        return r 

    def add_symptom(self, tag : str, symptom_tag : str) -> List[str]:
        """
        Adds a symptom to a maintenance event. If the symptom is already associated with the maintenance event, it will do nothing.
        
        Parameters
        ----------
        tag : str
            The tag of the maintenance event.
        symptom_tag : str
            The tag of the symptom.
            
        Returns
        -------        
        List[str]
            A updated list of symptom tags that match the maintenance event.
        """
        
        query = (
            "MATCH (me:MaintenanceEvent {tag : $maintenance_event_tag}) "
            "MATCH (s:Symptom {tag : $symptom_tag}) "
            "MERGE (me)-[:HAS_SYMPTOM]->(s) "
            "SET me.modified_at = timestamp() "
            "WITH me "
            "MATCH (me)-[:HAS_SYMPTOM]->(s:Symptom) "
            "RETURN s.tag "
        )
        
        r = self._driver.execute_query(query, routing_="w", 
                                   maintenance_event_tag = tag, 
                                   symptom_tag = symptom_tag)

    def remove_symptom(self, tag : str, symptom_tag : str = None) -> None:
        """
        Removes a symptom from a maintenance event. If symptom_tag is None, all symptom relationships of type HAS_SYMPTOM are removed.
        
        Parameters
        ----------
        tag : str
            The tag of the maintenance event.
        symptom_tag : str
            The tag of the symptom.
        """
        
        query = (
            "MATCH (me:MaintenanceEvent {tag : $maintenance_event_tag}) " ) 
        if symptom_tag is not None:
            query += "MATCH (s:Symptom {tag : $symptom_tag}) "
        else:
            query += "MATCH (s:Symptom) "
        query += (
            "MATCH (me)-[r:HAS_SYMPTOM]->(s) "
            "SET s.modified_at = timestamp() "
            "DELETE r "
            "WITH me "
            "MATCH (me)-[:HAS_SYMPTOM]->(s:Symptom) "
            "RETURN s.tag "
        )
        
        self._driver.execute_query(query, routing_="w", 
                                   maintenance_event_tag = tag, 
                                   symptom_tag = symptom_tag)


    def remove_maintenance_procedure(self, tag : str, maintenance_procedure_tag : str = None) -> List[str]:
        """
        Removes a maintenance procedure from a maintenance event. If maintenance_procedure_tag is None, all maintenance procedures are removed.
        
        Parameters
        ----------
        tag : str
            The tag of the maintenance event.
        maintenance_procedure_tag : str
            The tag of the maintenance procedure.
        """
        query = (
            "MATCH (me:MaintenanceEvent {tag : $maintenance_event_tag}) " ) 
        if maintenance_procedure_tag is not None:
            query += "MATCH (m:MaintenanceProcedure {tag : $maintenance_procedure_tag}) "
        else:
            query += "MATCH (m:MaintenanceProcedure) "
            
        query += (
            "MATCH (me)-[r:PERFORMED]->(m) "
            "SET me.modified_at = timestamp() "
            "DELETE r "
            "WITH me "
            "MATCH (me)-[:PERFORMED]->(m:MaintenanceProcedure) "
            "RETURN m.tag "
            # "MATCH (me)-[r:PERFORMED]->(m) "
            # # "SET m.modified_at = timestamp() "
            # # "CASE WHEN r.count > 1 THEN "
            # # "SET r.count = r.count - 1 "
            # # "ELSE "     
            # "DELETE r RETURN true "
            # "WITH me "
            # "MATCH (me)-[:PERFORMED]->(m:MaintenanceProcedure) "
            # "RETURN m.tag "
        )
        
        r = self._driver.execute_query(query, 
                                routing_="w", 
                                maintenance_event_tag = tag, 
                                maintenance_procedure_tag = maintenance_procedure_tag,
                                result_transformer_=Result.value)
        return r 
    

   
    #     query = (
    #         "MATCH (me:MaintenanceEvent {tag : $maintenance_event_tag}) "
    #         "MATCH (me)-[r:UTILIZED]->(sp:SparePart) "
    #         "WITH me, collect(r.count * sp.price) as total_sparepart_costs "
    #         "MATCH (me)-[:HAS_EXTERNAL_SERVICE]->(es:ExternalService) "
    #         "WITH me, total_sparepart_costs, sum(es.costs) as total_external_service_costs "
    #         "SET me.costs = total_sparepart_costs + total_external_service_costs, "
    #         "me.modified_at = timestamp() "
    #         "RETURN me.costs "
    #         )
        


    def update_costs(self, tag: str) -> float:
        """
        Updates the costs of a maintenance event.
        """

        query = (
            "MATCH (me:MaintenanceEvent {tag : $maintenance_event_tag}) "
            "MATCH (me)-[r:UTILIZED]->(sp:SparePart) "
            "WITH me, collect(r.count * sp.price) as sparepart_costs "
            "WITH me, reduce(total = 0.0, x IN sparepart_costs | total + x) AS total_sparepart_costs "
            "MATCH (me)-[:HAS_EXTERNAL_SERVICE]->(es:ExternalService) "
            "WITH total_sparepart_costs, sum(es.costs) as total_external_service_costs, me "
            "SET me.costs = total_sparepart_costs + total_external_service_costs, me.modified_at = timestamp() "
            "RETURN me.costs "
            )
        

        r = self._driver.execute_query(
            query,
            maintenance_event_tag=tag,
            routing_="w",
            result_transformer_=Result.value
        )

        return r[0] if r else 0.0


    def add_sparepart(self, tag : str, sparepart_tag : str = None) -> List[str]:
        """
        Removes a spare part from a maintenance event. 
        
        Parameters
        ----------
        maintenance_event_tag : str
            The tag of the maintenance event.
        sparepart_tag : str
            The tag of the spare part.
        """
        
        query = (
            "MATCH (me:MaintenanceEvent {tag: $maintenance_event_tag}) "
            "MATCH (sp:SparePart {tag : $sparepart_tag}) ")
    
        query += (
            "MERGE (me)-[r:UTILIZED]->(sp) "
            "ON CREATE "
            "SET r.created_at = timestamp(), r.count = 1 "
            "ON MATCH "
            "SET r.count = r.count + 1, r.modified_at = timestamp() "
            "WITH me "
            "MATCH (me)-[:UTILIZED]->(sp:SparePart) "
            "SET me.modified_at = timestamp() "
            "RETURN sp.tag "
        )
        
        r = self._driver.execute_query(query, 
                                routing_="w", 
                                maintenance_event_tag = tag, 
                                sparepart_tag = sparepart_tag,
                                result_transformer_=Result.value)
        return r    
    
    
    def get_sparepart_count(self, tag : str, sparepart_tag : str) -> int: 
        """
        Returns the count of a spare part in a maintenance event.
        
        Parameters
        ----------
        tag : str
            The tag of the maintenance event.
        sparepart_tag : str
            The tag of the spare part.
        
        Returns
        -------
        int
            The count of the spare part in the maintenance event.
        """
        
        query = (
            "MATCH (me:MaintenanceEvent {tag : $maintenance_event_tag}) "
            "MATCH (sp:SparePart {tag : $sparepart_tag}) "
            "MATCH (me)-[r:UTILIZED]->(sp) "
            "RETURN r.count "
        )
        
        r = self._driver.execute_query(query, 
                                routing_="r", 
                                maintenance_event_tag = tag, 
                                sparepart_tag = sparepart_tag,
                                result_transformer_=Result.value)
        
        if len(r) == 0:
            return 0
        return r[0] if isinstance(r[0], int) else 0  #
    
    def remove_sparepart(self, tag : str, sparepart_tag : str = None) -> List[str]:
        """
        Removes a spare part from a maintenance event. 
        
        Parameters
        ----------
        maintenance_event_tag : str
            The tag of the maintenance event.
        sparepart_tag : str
            The tag of the spare part.
        """
        
        N = self.get_sparepart_count(tag = tag, sparepart_tag = sparepart_tag)  #check if spare part exists
        if N == 0:
            raise ValueError(f"Spare part with tag {sparepart_tag} not found in maintenance event with tag {tag}.")
        
        query = (
            "MATCH (me:MaintenanceEvent {tag : $maintenance_event_tag}) ")
        if sparepart_tag is not None:
            query += "MATCH (sp:SparePart {tag : $sparepart_tag}) "
        else:
            query += "MATCH (sp:SparePart) "
            
        query += (
            "MATCH (me)-[r:UTILIZED]->(sp) "
            "SET me.modified_at = timestamp() "
        )
        if N > 1:
            query += (
                "SET r.count = r.count - 1, r.modified_at = timestamp() "
                "RETURN true"
            )
        elif N == 1:
            query += (
                "DELETE r "
                "RETURN true "
        )   
        
        r = self._driver.execute_query(query, 
                                routing_="w", 
                                maintenance_event_tag = tag, 
                                sparepart_tag = sparepart_tag,
                                result_transformer_=Result.value)
        return r    

    def get_states(self) -> List[MaintenanceStateResponseModel]:
        """
        Returns a list of all maintenance states.
        
        Returns
        -------
        List[str]
            A list of maintenance state tags.
        """
        
        query = "MATCH (ms:MaintenanceState) RETURN {tag : ms.tag, description : ms.description, text : ms.text, color : ms.color}"
        
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value)
        
        return [MaintenanceStateResponseModel(**ri) for ri in r] if isinstance(r, list) else []  # Return an empty list if no states are found.

    def get_event_state(self, tag : str) -> str:
        """
        Returns the state of a maintenance event.
        
        Parameters
        ----------
        tag : str
            The tag of the maintenance event.
        
        Returns
        -------
        str
            The tag of the state of the maintenance event.
            
        Raises
        ------
        ValueError
            If the maintenance event does not exist or has no state.
        """
        
        query = (
            "MATCH (me:MaintenanceEvent {tag : $maintenance_event_tag}) "
            "MATCH (me)-[r:IN_STATE]->(ms:MaintenanceState) "
            "WITH ms, r "
            "ORDER BY r.created_at DESC "
            "RETURN ms.tag LIMIT 1"
        )
        
        r = self._driver.execute_query(query, routing_="r", maintenance_event_tag = tag, result_transformer_=Result.value)
        
        if len(r) == 0:
            raise ValueError(f"No maintenance event found with tag {tag} or no state associated with it.")
        
        return r[0] if isinstance(r[0], str) else None

    def set_state(self, tag : str, state_tag : str, user_tag : str, description : str = "") -> str|None:
        """
        Sets the state of a maintenance event.
        
        Parameters
        ----------
        tag : str
            The tag of the maintenance event.
        state_tag : str
            The tag of the state to set.
            
        Returns
        -------
        str
            The tag of the state that was set.
            
        Raises
        ------
        ValueError
            If the maintenance event or the state does not exist.
        """
        
        query = (
            "MATCH (me:MaintenanceEvent {tag: $maintenance_event_tag}) "
            "MATCH (ms:MaintenanceState {tag: $state_tag}) "
            "CREATE (me)-[r:IN_STATE]->(ms) "
            "SET r.tag = randomUUID(), r.created_at = timestamp(), r.maintenance_event_tag = $maintenance_event_tag, r.user_tag = $user_tag, "
            "r.description = $description "
            "RETURN ms.tag "
        )
        
        r = self._driver.execute_query(query, 
                                    routing_="w", 
                                    maintenance_event_tag = tag, 
                                    state_tag = state_tag,
                                    user_tag = user_tag,
                                    description = description,
                                    result_transformer_=Result.value)
        if len(r) == 0:
            raise ValueError(f"No maintenance event found with tag {tag} or no maintenance state found with tag {state_tag}.")  
        return r[0] if isinstance(r[0], str) else None  # Return the tag of the state that was set.

    def add_external_service(self, tag : str, external_service_tag : str, user_tag : str = None) -> List[str]:
        """
        Adds an external service to a maintenance event.
        
        Parameters
        ----------
        maintenance_event_tag : str
            The tag of the maintenance event.
        external_service_tag : str
            The tag of the external service.
        user_tag : str
            The tag of the user adding the external service.
        
        Returns
        -------
        List[str]
            A list of external service tags associated with the maintenance event.
        """
        
        query = (
            "MATCH (me:MaintenanceEvent {tag: $maintenance_event_tag}) "
            "MATCH (es:ExternalService {tag: $external_service_tag}) "
            "MERGE (me)-[r:HAS_EXTERNAL_SERVICE]->(es) "
            "SET r.created_at = timestamp(), r.user_tag = $user_tag "
            "WITH me "
            "MATCH (me)-[:HAS_EXTERNAL_SERVICE]->(es:ExternalService) "
            "RETURN es.tag "
        )
        
        r = self._driver.execute_query(query, 
                                   routing_="w", 
                                   maintenance_event_tag = tag, 
                                   external_service_tag = external_service_tag,
                                   user_tag = user_tag,
                                   result_transformer_=Result.value)
        return r
    
    def remove_external_service(self, tag, external_service_tag, user_tag):
        """
        Removes an external service from a maintenance event.
        
        Parameters
        ----------
        maintenance_event_tag : str
            The tag of the maintenance event.
        external_service_tag : str
            The tag of the external service.
        user_tag : str
            The tag of the user removing the external service.
        """
        
        query = (
            "MATCH (me:MaintenanceEvent {tag: $maintenance_event_tag}) "
            "MATCH (es:ExternalService {tag: $external_service_tag}) "
            "MATCH (me)-[r:HAS_EXTERNAL_SERVICE]->(es) "
            "DELETE r "
        )
        
        self._driver.execute_query(query, 
                                   routing_="w", 
                                   maintenance_event_tag = tag, 
                                   external_service_tag = external_service_tag,
                                   user_tag = user_tag)

class Neo4JMaintenanceProcedure(MaintenanceProcedureABC):
    ""
    def __init__(self, driver : Driver) -> None:
        
        self._driver = driver 
        
        
    def _utils_insert_from_file(self, path_to_file : str = "/Users/hnolte/Documents/GitHub/mitocube-backend/resources/maintenance/procedures.txt", *args, **kwargs) -> None:
        ""    
        maintenance_file : pd.DataFrame = pd.read_csv(path_to_file, *args, **kwargs)
        
        if not all(column_name in maintenance_file.columns for column_name in REQUIRED_COLUMNS):
            raise ValueError(f"The file does not contain one of the following column names: {REQUIRED_COLUMNS}")
        print(maintenance_file)
        records = [MaintenanceInsertModel(**r) for r in maintenance_file.to_dict(orient="records")]
        
        query = (
            "UNWIND $ms as m_prop " 
            "MERGE (m:MaintenanceProcedure {tag : m_prop.tag}) "
            "ON CREATE " 
            "SET m.description = m_prop.description, m.text = m_prop.text, m.s = m_prop.s, "
            "m.priority = m_prop.priority, m.created_at = timestamp(), m.is_active = true "
            "ON MATCH "
            "SET m.description = m_prop.description, m.text = m_prop.text, m.s = m_prop.s, "
            "m.priority = m_prop.priority, m.modified_at = timestamp(), m.is_active = true "
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
        query = "MATCH (m:MaintenanceProcedure) RETURN count(m)"
        
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value)
        if len(r) == 0: return 0 #should not happen.
        return r[0]
    
    
    
    def exists(self, tag : str) -> bool:
        query = (
            "WITH EXISTS {(m:MaintenanceProcedure {tag : $tag})} as maintenance_exists "
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

    def insert(self, procedure: MiantenanceProcedureInsertModel, user_tag: str, is_active: bool = True):
        """Inserts a proccedure in the database. 

        Parameters
        ----------
        proccedure : proccedureModel
            The proccedure to insert.

        Returns
        -------
        bool
            Indicates if the insertion was successful.
        """

        query = (
            "MATCH (u:User {tag: $user_tag}) "
            "MERGE (m:MaintenanceProcedure {tag: $tag}) "
            "ON CREATE SET m.is_active = $is_active, "
            "              m.created_at = timestamp(), "
            "              m.description = $description, "
            "              m.priority = $priority, "
            "              m.s = toLower($text)+' '+toLower($description), "
            "              m.text = $text "
            "ON MATCH SET  m.modified_at = timestamp(), "
            "              m.description = $description, "
            "              m.priority = $priority, "
            "              m.s = toLower($text)+' '+toLower($description), "
            "              m.text = $text "
            "WITH u, m "
            "CREATE (u)-[:CREATED {created_at: timestamp()}]->(m) "
            "CREATE (u)-[:MODIFIED {modified_at: timestamp()}]->(m) "
            "RETURN true as ok"
)
        
        ok = self._driver.execute_query(query, 
                                        tag = procedure.tag,
                                        is_active = is_active,
                                        description = procedure.description,
                                        priority = procedure.priority,
                                        text = procedure.text,
                                        user_tag = user_tag,
                                        routing_="w",
                                        result_transformer_= Result.value)
        
        return ok[0]
    

    
    def get(self, tag : str = None) -> MaintenanceProcedureResponseModel|None:
        
        query = "MATCH (m:MaintenanceProcedure) "
        
        if tag is not None: 
            query += "WHERE m.tag = $tag "
            
        query += "RETURN {text : m.text, description : m.description, tag : m.tag, priority : m.priority} "
        
        r = self._driver.execute_query(query, routing_="r", tag = tag, result_transformer_=Result.value)
        
        return MaintenanceProcedureResponseModel(**r[0]) if len(r) > 0 else None
    
    def get_text(self, tag: str) -> str | None:
        """Return the text of a maintenance procedure."""
        query = (
            "MATCH (m:MaintenanceProcedure {tag: $tag}) "
            "RETURN m.text"
        )
        r = self._driver.execute_query(
            query, tag=tag, routing_="r", result_transformer_=Result.value
        )
        return r[0] if r else None


    def get_description(self, tag: str) -> str | None:
        """Return the description of a maintenance procedure."""
        query = (
            "MATCH (m:MaintenanceProcedure {tag: $tag}) "
            "RETURN m.description"
        )
        r = self._driver.execute_query(
            query, tag=tag, routing_="r", result_transformer_=Result.value
        )
        return r[0] if r else None


    def get_priority(self, tag: str) -> int | None:
        """Return the priority of a maintenance procedure."""
        query = (
            "MATCH (m:MaintenanceProcedure {tag: $tag}) "
            "RETURN m.priority"
        )
        r = self._driver.execute_query(
            query, tag=tag, routing_="r", result_transformer_=Result.value
        )
        return r[0] if r else None


    def find(self, search_string: str = "", limit: int = 20, is_active: bool = True, sort: bool = True) -> List[str]:
        query = (
            "MATCH (m:MaintenanceProcedure) "
            "WHERE m.is_active = $is_active "
        )

        # Only filter if non-empty search
        search_string = search_string.lower().strip()
        if search_string:
            query += "AND m.s CONTAINS $search_string "

        query += "RETURN m.tag "

        if sort:
            query += "ORDER BY m.priority "

        if limit is not None:
            query += "LIMIT $limit"

        procedures = self._driver.execute_query(
            query,
            search_string=search_string,
            limit=limit,
            is_active=is_active,
            routing_="r",
            result_transformer_=Result.value,
        )

        return procedures

    def update(self, procedure: MaintenanceProcedureResponseModel, user_tag: str) -> bool:
        """Edits a maintenance procedure in the database.

        Parameters
        ----------
        procedure : MiantenanceProcedureInsertModel
            The procedure to edit.

        Returns
        -------
        bool
            Indicates if the edit was successful.
        """
        print("Updating procedure:", procedure)
        query = (
            "MATCH (m:MaintenanceProcedure {tag: $tag}) "
            "SET "
            "    m.modified_at = timestamp(), "
            "    m.description = $description, "
            "    m.priority = $priority, "
            "    m.s = toLower($text)+' '+toLower($description), "
            "    m.text = $text "
            "WITH m "
            "MATCH (u:User {tag: $user_tag}) "
            "CREATE (u)-[:MODIFIED {modified_at: timestamp()}]->(m) "
            "RETURN true as ok "
        )

        ok = self._driver.execute_query(
            query,
            tag=procedure.tag,
            description=procedure.description,
            priority=procedure.priority,
            text=procedure.text,
            user_tag=user_tag,
            routing_="w",
            result_transformer_=Result.value,
        )

        return ok[0]
    
    def delete(self, tag: str, is_active: bool = False) -> bool:
        """
        Deletes a maintenance procedure by tag.
        """

        query = (
            "MATCH (m:MaintenanceProcedure {tag: $tag}) "
            "SET m.is_active = $is_active "
            "RETURN true as ok "
        )

        result = self._driver.execute_query(
            query,
            tag=tag,
            is_active=is_active,
            routing_="w",
            result_transformer_=Result.value
        )

        return True if result is not None else False



class Neo4JExternalServices(ExternalServicesABC):

    def __init__(self, driver : Driver) -> None:
        
        self._driver = driver 

    def exists(self, tag: str) -> bool:
        """
        Checks if a mainteance service with the given tag exists.
        """

        query = (
            "WITH EXISTS {(es:ExternalService {tag: $tag})} as es_exists "
            "RETURN es_exists "
        )

        exists = self._driver.execute_query(query, tag = tag, routing_ = "r")    
        return exists[0]
    
    def find(self, search_string: str = "", limit: int = 20, is_active: bool = True, sort: bool = True) -> List[str]:
        """
        Find external services by a search string.
        """

        query = (
            "MATCH (es:ExternalService) "
            "WHERE es.is_active = $is_active "
        )

        # Only filter if non-empty search
        search_string = search_string.lower().strip()
        if search_string:
            query += "AND es.s CONTAINS $search_string "

        query += "RETURN es.tag "

        if sort:
            query += "ORDER BY es.name "

        if limit is not None:
            query += "LIMIT $limit"

        services = self._driver.execute_query(
            query,
            search_string=search_string,
            limit=limit,
            is_active=is_active,
            routing_="r",
            result_transformer_=Result.value,
        )

        return services

    def get(self, tag: str) -> ExternalServiceModel:
        "Get the complete external service model."

        if not self.exists(tag):
            raise ValueError("Tag not associated with an external service.")
        
        query = (
            "MATCH (es:ExternalService {tag: $tag}) "
            "RETURN properties(es) "
        )

        service = self._driver.execute_query(query, tag=tag, routing= "r", result_transformer_= Result.value)

        if len(service) == 0:
            raise ValueError("Tag exists, but database returns None.")
        
        return ExternalServiceModel(**service[0])

    def insert(self, service: ExternalServiceInsertModel, user_tag : str, is_active : bool = True) -> bool:
        """
        Inserts a new external service in the database. 
        """

        query = (
            "MATCH (u:User {tag: $user_tag}) "
            "MERGE (es:ExternalService {tag: $tag}) "
            "ON CREATE SET es.is_active = $is_active, "
            "              es.created_at = timestamp(), "
            "              es.description = $description, "
            "              es.name = $name, "
            "              es.company = $company, "
            "              es.email = $email, "
            "              es.costs  = $costs, "
            "              es.billing_number = $billing_number, "
            "              es.s = toLower($description), "
            "              es.internal_id = $internal_id "
            "WITH u, es "
            "CREATE (u)-[:CREATED {created_at: timestamp()}]->(es) "
            "RETURN true AS ok "
        )

        ok = self._driver.execute_query(query,
                                        tag=service.tag,
                                        user_tag=user_tag,
                                        is_active=is_active,
                                        description=service.description,
                                        name=service.name,
                                        company=service.company, 
                                        email=service.email,
                                        costs=service.costs,
                                        billing_number=service.billing_number,
                                        internal_id=service.internal_id,
                                        routing_="w",
                                        result_transformer_=Result.value
        )

        return ok[0]
    
   
    def delete(self, tag : str, is_active : bool = False) -> bool:
        "Delete a service event from the database."

        query = (
            "MATCH (es:ExternalService {tag: $tag}) "
            "SET es.is_active = $is_active "
            "RETURN true as OK "
        )

        result = self._driver.execute_query(query,
                                            tag=tag,
                                            is_active=is_active,
                                            routing_="w",
                                            result_transformer_=Result.value
        )

        return True if result is not None else False


    def update(self, service: ExternalServiceModel, user_tag: str = None) -> bool:
        "Update an existing service."

        if not self.exists(service.tag):
            raise ValueError("External Service does not exist.")
        
        query = (
                "MATCH (es:ExternalService {tag: $tag}) "
                "SET "
                "   es.description = $description, "
                "   es.name = $name, "
                "   es.company = $company, "
                "   es.email = $email, "
                "   es.costs = $costs, "
                "   es.billing_number = $billing_number, "
                "   es.internal_id = $internal_id, "
                "   es.modified_at = timestamp() "
                "WITH es "
                "MATCH (u:User {tag: $user_tag}) "
                "CREATE (u)-[:MODIFIED {modified_at: timestamp()}]->(es) "
                "RETURN true as ok "

        )

        ok = self._driver.execute_query(query,
                                        tag=service.tag,
                                        user_tag=user_tag,
                                        description=service.description,
                                        name=service.name,
                                        company=service.company, 
                                        email=service.email,
                                        costs=service.costs,
                                        billing_number=service.billing_number,
                                        internal_id=service.internal_id,
                                        routing_="w",
                                        result_transformer_=Result.value
        )

        return ok[0]
    
    def get_description(self, tag: str) -> str:
        """
        Get the description of the external service by its tag. 
        """

        query = (
            "MATCH (es:ExternalService {tag: $tag}) "
            "RETURN es.description as description "
        )

        r = self._driver.execute_query(
            query, tag=tag, routing_="r", result_transformer_=Result.value
        )
        return r[0]
    
    def get_name(self, tag: str) -> str:
        """
        Get the name of the person that provided the service by its tag.
        """

        query = (
            "MATCH (es:ExternalService {tag: $tag}) "
            "RETURN es.name as name "
        )

        r = self._driver.execute_query(
            query, tag=tag, routing_="r", result_transformer_=Result.value
        )
        return r[0]
    
    def get_company(self, tag: str) -> str:
        """
        Get the company name providing the service.
        """

        query = (
            "MATCH (es:ExternalService {tag: $tag}) "
            "RETURN es.company as company "
        )

        r = self._driver.execute_query(
            query, tag=tag, routing_="r", result_transformer_=Result.value
        )
        return r[0]

    def get_email(self, tag: str) -> str:
        """
        Get the contact person's email address. 
        """

        query = (
            "MATCH (es:ExternalService {tag: $tag}) "
            "RETURN es.email as email "
        )

        r = self._driver.execute_query(
            query, tag=tag, routing_="r", result_transformer_=Result.value
        )
        return r[0]

    def get_costs(self, tag: str) -> float | int:
        """
        Get costs of the service
        """

        query = (
            "MATCH (es:ExternalService {tag: $tag}) "
            "RETURN es.costs as costs "
        )

        r = self._driver.execute_query(
            query, tag=tag, routing_="r", result_transformer_=Result.value
        )
        return r[0]
    


    def get_billing_number(self, tag: str) -> str:
        """
        Get the billing or invoice number. 
        """
        query = (
            "MATCH (es:ExternalService {tag: $tag}) "
            "RETURN es.billing_number as billing_number "
        )

        r = self._driver.execute_query(
            query, tag=tag, routing_="r", result_transformer_=Result.value
        )
        return r[0]


    def get_internal_id(self, tag: str) -> str:
        """
        Get Internal ID for the service. 
        """

        query = (
            "MATCH (es:ExternalService {tag: $tag}) "
            "RETURN es.internal_id as internal_id "
        )

        r = self._driver.execute_query(
            query, tag=tag, routing_="r", result_transformer_=Result.value
        )
        return r[0]