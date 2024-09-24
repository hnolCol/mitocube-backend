from typing import List, Tuple, Literal
from neo4j import Driver, Result

from lib.data.database.abstract.Attributes import AttributesABC

from config.enums.states import SubmissionStatesEnums

from config.models.attributes import AttributeModel, AttributeValueModel, AttributeValuesBySubmissionModel, AttributeUnitModel, AttributeUnitResponseModel
from config.models.annotations.feature import FeatureModel 
from config.models.feature import FeatureNeoModel


class Neo4JAttributes(AttributesABC):

    def __init__(self, driver : Driver) -> None:
        
        self._driver = driver
    
    def __read_attributes_values_from_tuple_results(self,ri):
            attribute = AttributeModel(**ri[0])
            if attribute.has_features_value:
                values = [FeatureNeoModel(**av) for av in ri[1]]
            else:
                values = [AttributeValueModel(**av) for av in ri[1]]
            return (attribute,values)
        
    def count(self) -> int:
        
        query = (
            "MATCH (a:Attribute) "
            "RETURN count(a) "
        )
        
        r = self._driver.execute_query(query_=query, routing_="r", result_transformer_=Result.value)
        return r[0]
        
    def count_values(self, attribute_tag: str = None) -> int:
        """Returns the number of attribute value by attribute_tag.

        Parameters
        ----------
        attribute_tag : str, optional
            The attribute tag to get the values count from., by default None

        Returns
        -------
        int
            _description_
        """
        if attribute_tag is None:
            query = (
                "MATCH (av:AttributeValue) "
                "WHERE NOT 'Protein' in labels(av) "
                "RETURN count(av) "
            )
        else:
            query = (
                "MATCH (av:AttributeValue) "
                "WHERE NOT 'Protein' in labels(av) AND av.tag = attribute_tag "
                "RETURN count(av) "
            )
 
        r = self._driver.execute_query(query_=query,routing_="r", attribute_tag = attribute_tag, result_transformer_=Result.value)
        return r[0]
    
    def delete(self, tag: str) -> bool:
        query = (
            "MATCH (a:Attribute {tag :$tag})-[:HAS_VALUE]->(av:AttributeValue) "
            "DETACH DELETE a, av "
        )
        self._driver.execute_query(query = query, routing_="w", tag = tag)
        
    def delete_value(self, tag: str) -> bool:
        
        query = (
            "MATCH (av:AttributeValue {tag : $tag}) "
            "DETACH DELETE av "
        )
        
        self._driver.execute_query(query, routing_="w", tag = tag)
        return True
                
    def exists(self, tag: str = None, value: str = None) -> bool:
        if tag is None and value is None:
            raise ValueError("Either tag or value must be not None and a string")
    
        if tag is not None and value is None:
            query = (
                "WITH EXISTS {(a:Attribute {tag : $tag})} as attribute_exists "
            )
        if tag is not None and value is not None:
            query = (
                "WITH EXISTS {(a:Attribute {tag :$tag})-[:HAS_VALUE]-(av:AttributeValue {tag : $value})} as exists "
                     )
        if value is not None and tag is None:
            query = (
                "WITH EXISTS {(av:AttributeValue {tag : $value})} as exists "
                )
        query += "RETURN exists"     
        
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value, tag = tag, value = value)
        return r[0]
        
    def get(self, tags : List[str] = None,
            param_name : Literal["allow_for_dataset","allow_as_filter",
                                "allow_for_genotype","allow_for_measurement","allow_for_qc",
                                "mandatory_for_submission","mandatory_for_active"] = None,
            min_state : SubmissionStatesEnums = None) -> List[AttributeModel]:
        ""
        
        query = (
            "MATCH (a:Attribute) "
        )
        if tags is not None:
            query = (
                "MATCH (a:Attribute) "
                "WHERE a.tag in $tags "
            )
        
        if param_name is not None:
            if tags is None:
                query += "WHERE a[$param_name] "
            else:
                query += "AND a[$param_name] "
            
        if min_state is not None:
            if tags is None and param_name is None:
                query += "WHERE a.min_state = $min_state "
            else:
                query += "AND a.min_state <= $min_state "
            
        query += "RETURN properties(a) ORDER BY a.priority"

        attributes = self._driver.execute_query(query_=query, 
                                                routing_="r",
                                                result_transformer_ = Result.value, 
                                                tags = tags, 
                                                param_name = param_name, 
                                                min_state = min_state)
        return [AttributeModel(**k) for k in attributes]


    def values(self, tags : List[str]) -> List[AttributeValueModel]:
        """
        Does not return features as attribute values.

        Parameters
        ----------
        tags : List[str]
            _description_

        Returns
        -------
        List[AttributeValueModel]
            _description_
        """
        query = (
            "MATCH (a:Attribute)-[:HAS_VALUE]->(av:AttributeValue) "
            "WHERE NOT 'Protein' in labels(av) AND a.tag in $tags "
            "RETURN properties(av)"
        )
        attribute_values = self._driver.execute_query(query_=query,routing_="r",result_transformer_=Result.value, tags = tags )
        return [AttributeValueModel(**av) for av in attribute_values]
        
        
    
    def get_values(self, submission_tag : str, tags : List[str] = None) -> List[AttributeValueModel|FeatureNeoModel]:
        "Returns the props of the attributes its values. Note that it will return dataset and sample attribute values"
        
        if tags is not None:
            query = (
                "MATCH (av:AttributeValue) "
                "WHERE NOT 'Protein' in labels(av) AND av.tag in $tags "
                "RETURN properties(av) as props "
                "UNION "
                "MATCH (av:AttributeValue:Protein) "
                "WHERE av.tag in $tags "
                "MATCH (submission:Submission)-[r:HAS_ATTRIBUTE_VALUE]->(av) "
                "WHERE submission.tag = $submission_tag "
                "WITH {attribute_tag : r.attribute_tag} as attr_tag, av "
                "WITH apoc.map.merge(properties(av), attr_tag) as props "
                "RETURN props"
            )
        
        else:
            query = (
                "MATCH (a:Attribute)-[:HAS_VALUE]->(av:AttributeValue)<-[r:HAS_ATTRIBUTE_VALUE]-(submission:Submission) "
                "WHERE submission.tag = $submission_tag "
                "WITH {attribute_tag : a.tag} as attr_tag, av " #add the attribute tag 
                "RETURN apoc.map.merge(properties(av), attr_tag)"
                ""
            )
        
        attribute_values  = self._driver.execute_query(query, tags = tags, routing_="r", result_transformer_=Result.value, submission_tag = submission_tag)
       # attribute_values_props = [av.value() for av in attribute_values]
        return [FeatureNeoModel(**av) if "gene_name" in av else AttributeValueModel(**av) for av in attribute_values]
    
    def get_attribute_values_by_dataset_tags(self, dataset_tags : List[str], attribute_tags : list[str] = None, attribute_value_tags : List[str] = None) -> List[AttributeValuesBySubmissionModel]:
        """Finds all the attribute values that are assigned to a dataset and returns the number of dataset
        that match each attribute value. This is a convenient function to get the datasets tags that have 
        an attribute value and how many are used, as used in a filtering approach. 

        Parameters
        ----------
        dataset_tags : List[str]
            The list of dataset tags to consider. 
        attribute_tags : list[str], optional
            Subset of attribute tags to consider, if None all the attribute available are considered, by default None
        attribute_value_tags : List[str], optional
            Subset of attribute value tags, by default None

        Returns
        -------
        List[AttributeValuesBySubmissionModel]
            The result of the query given by a list of AttributeValuesBySubmissionModel with the following 
            properties:
                - attribute_value (AttributeValueModel|FeatureModel) : The attribute Value
                - tags (List[str]) : List of submission tags that have the attribute value
                - counts (int) : The number of submission tags, equals len(tags)
        """
        
        
        if attribute_tags is None and attribute_value_tags is None:
            #returns all attribute values for the given dataset tags 
            query = (
                "MATCH (submission:Submission) "
                "WHERE submission.tag in $tags "
                "MATCH (submission)-[:HAS_ATTRIBUTE_VALUE]-(av:AttributeValue) "
                "RETURN properties(av) as attribute_value, collect(submission.tag) as tags, count(submission) as count "
            )
            r, _ , _ = self._driver.execute_query(query, tags=dataset_tags)
            
        elif attribute_tags is None and attribute_value_tags is not None:
            #filtered for set of attribute value tags 
            query = (
                "MATCH (submission:Submission) "
                "WHERE submission.tag in $tags "
                "MATCH (submission)-[:HAS_ATTRIBUTE_VALUE]-(av:AttributeValue) "
                "WHERE av.tag in $attribute_value_tags"
                "RETURN properties(av) as attribute_value, collect(submission.tag) as tags, count(submission) as count "
            )
            r, _ , _ = self._driver.execute_query(query, tags=dataset_tags, attribute_value_tags = attribute_value_tags)
        
        elif attribute_tags is not None and attribute_value_tags is not None:
            #filtered for attribute_tags and attribute_value_tags 
            query = (
                "MATCH (submission:Submission) "
                "WHERE submission.tag in $tags AND EXISTS {(submission)-[:HAS_VALUES_FOR_ATTRIBUTE]->(a:Attribute) WHERE a.tag in $attribute_tags} "
                "MATCH (submission)-[:HAS_ATTRIBUTE_VALUE]-(av:AttributeValue)<-[:HAS_VALUE]-(a:Attribute) "
                "WHERE av.tag in $attribute_value_tags AND a.tag in $attribute_tags "
                "RETURN properties(av) as attribute_value, collect(submission.tag) as tags, count(submission) as count "
            )
            r, _ , _ = self._driver.execute_query(query, tags=dataset_tags, attribute_value_tags = attribute_value_tags, attribute_tags = attribute_tags)
        
        elif attribute_tags is not None and attribute_value_tags is None:
            #filtered for attribute_tags and attribute_value_tags 
            query = (
                "MATCH (submission:Submission) "
                "WHERE submission.tag in $tags AND EXISTS {(submission)-[:HAS_VALUES_FOR_ATTRIBUTE]->(a:Attribute) WHERE a.tag in $attribute_tags} "
                "MATCH (submission)-[:HAS_ATTRIBUTE_VALUE]-(av:AttributeValue)<-[:HAS_VALUE]-(a:Attribute) "
                "WHERE a.tag in $attribute_tags "
                "RETURN properties(av) as attribute_value, collect(submission.tag) as tags, count(submission) as count "
            )
            r, _ , _ = self._driver.execute_query(query, 
                                                  tags=dataset_tags, 
                                                  attribute_tags = attribute_tags,
                                                  database_="neo4j", 
                                            routing_="r")
        print(r)
        return [AttributeValuesBySubmissionModel(**ri.data()) for ri in r]
        
        
    def get_mandatory_attributes(self) -> List[AttributeModel]:
        
        return self._get_attributes_by_boolean_param()
    
    def get_dataset_attributes(self, min_state : SubmissionStatesEnums = None):
        """Returns attribute that can be used to define a dataset.

        Parameters
        ----------
        min_state : SubmissionStatesEnums, optional
            _description_, by default None

        Returns
        -------
        _type_
            _description_
        """
        if min_state is None:
            return self._get_attributes_by_boolean_param(param_name="allow_for_dataset")
        else:
            return self._get_attributes_by_boolean_param_and_state(param_name="allow_for_dataset", min_state=min_state)
    
    def _get_attributes_by_boolean_param(self, 
                                         param_name : str = "mandatory_for_submission", 
                                         order_param : str = "priority", 
                                         order_direction : Literal["ASC","DESC"] = "DESC",
                                         ) -> List[AttributeModel]:
        ""
        
        query = (
            "MATCH (a:Attribute) "
            "WHERE a[$param_name] "
            "RETURN properties(a) ORDER BY a[$order_param]" + f" {order_direction} "
        )

        r, _, _ = self._driver.execute_query(query,param_name = param_name, order_param = order_param)    
        return [AttributeModel(**ri.value()) for ri in r]
    
    def _get_attributes_by_boolean_param_and_state(self, 
                                         param_name : str = "mandatory_for_submission", 
                                         order_param : str = "priority", 
                                         order_direction : Literal["ASC","DESC"] = "DESC",
                                         min_state : SubmissionStatesEnums = SubmissionStatesEnums.SUBMITTED,
                                         ) -> List[AttributeModel]:
        ""
        
        query = (
            "MATCH (s:State)<-[:REQUIRES_STATE]-(a:Attribute) "
            "WHERE s.tag = $min_state AND a[$param_name] "
            "RETURN properties(a) ORDER BY a[$order_param]" + f" {order_direction} "
        )

        r, _, _ = self._driver.execute_query(query,param_name = param_name, order_param = order_param, min_state = min_state)

        return [AttributeModel(**ri.value()) for ri in r]
        
    
    def get_attribute_values_by_attribute_tag(self, tags :  List[str] = ["att_compound"]) -> List[Tuple[AttributeModel,List[AttributeValueModel]]]:
        """Returns the attribute values for the given attribute_tags 
        

        Parameters
        ----------
        tags : List[str], optional
            _description_, by default ["att_compound"]

        Returns
        -------
        List[Tuple[AttributeModel,List[AttributeValueModel]]]
            _description_
        """
        

        
        query = (
            "MATCH (a:Attribute) "
            "WHERE a.tag in $tags "
            "MATCH (a)-[:HAS_VALUE]->(av:AttributeValue) "
            "RETURN properties(a) as attribute, collect(properties(av)) as values "
        )
        
        r, _ , _ = self._driver.execute_query(query, 
                                            tags = tags,
                                            database_="neo4j", 
                                            routing_="r")
        return [self.__read_attributes_values_from_tuple_results(ri.values()) for ri in r]
    
    def get_attributes_by_state(self, state : SubmissionStatesEnums = SubmissionStatesEnums.SUBMITTED) -> List[AttributeModel]:
        
        query = (
            "MATCH (s:State)<-[:REQUIRES_STATE]-(a:Attribute) "
            "WHERE s.tag = $state_tag "
            "RETURN properties(a) as attribute"
        )
        
        r, _ , _ = self._driver.execute_query(query, state_tag = state)
        
        return [AttributeModel(**ri[0]) for ri in r]
    
    def get_attributes_for_user(self) -> List[AttributeModel]:
        
        return self._get_attributes_by_boolean_param(param_name="allow_for_user")
    
    def get_attributes(self):
        ""
        
        query = (
            "MATCH (a:Attribute) "
            "MATCH (a)-[:HAS_VALUE]->(av:AttributeValue) "
            "RETURN properties(a), collect(properties(av)) as values "
        )
        
        return self._driver.execute_query(query)
        
        
    def get_attributes_and_values_by_search_string(self, search_string : str, min_state : SubmissionStatesEnums = SubmissionStatesEnums.SUBMITTED, param_name : str = None) -> List[Tuple[AttributeModel,List[AttributeValueModel]]]:
        """Finds the attirbute and the corresponding attribute values. 
        Please note that if a search matches the attribute, then all attribute value are returned.

        Parameters
        ----------
        search_string : str
            _description_
        min_state : SubmissionStatesEnums, optional
            _description_, by default SubmissionStatesEnums.SUBMITTED

        Returns
        -------
        List[Tuple[AttributeModel,List[AttributeValueModel]]]
            _description_
        """
        query = "MATCH (a:Attribute) "
        
        if min_state is not None:
            query += "WHERE a.min_state <= $min_state "
        
        if param_name is not None:
            if min_state is None:
                query += "WHERE a[$param_name] "
            else:
                query += "AND a[$param_name] "
            
        query += (
            "MATCH (a)-[:HAS_VALUE]->(av:AttributeValue) "
            "WHERE a.s CONTAINS $search_string OR av.s CONTAINS $search_string "
            "WITH a, av ORDER BY a.priority DESC "
            "RETURN properties(a), collect(DISTINCT properties(av))"
        )
        
        r  = self._driver.execute_query(
            query,
            search_string=search_string.lower(),
            min_state = min_state, 
            param_name = param_name, 
            result_transformer_= Result.values,
            routing_="r", 
            database_="neo4j")
    
        return r


    def insert(self, attribute: AttributeModel, attribute_values: List[AttributeValueModel] = None) -> bool:
        "Insert attributes TODO : IMPLEMENT! " 
    
          

    def insert_value(self, tag : str, attribute_value : AttributeValueModel) -> bool:
        ""
    
        query = (
            "MATCH (a:Attribute {tag : $tag}) "
            "MERGE (av:AttributeValue {tag : $attribute_value_tag}) "
            "SET av += $attribute_value_props "
            "MERGE (a)-[:HAS_VALUE]->(av) "
            "RETURN count(av)"
        )
        
        r = self._driver.execute_query(query, tag = tag, 
                                   attribute_value_tag = attribute_value.tag, 
                                   attribute_value_props = attribute_value.model_dump(exclude_none=True),
                                   result_transformer_= Result.value,
                                   routing_= "w")

        return r 
        
        
        
    def unit(self, tags : List[str]) -> List[AttributeUnitResponseModel]:
        """Returns the unit by attribute tag

        Parameters
        ----------
        tag : str
            Attribute tag for which the unit should be returned. 

        Returns
        -------
         List[AttributeUnitResponseModel]
            The list of attribute units. Please note that if the attribute 
            tag is not associated with an Attribute it will be simply
            ignored. Therefore the length of the response list 
            might be different from the provided tag's list. 
        """
        
        query = (
            "MATCH (a:Attribute) "
            "WHERE a.tag in $tags AND a.has_unit "
            "MATCH (u:Unit) "
            "WHERE u.tag in a.unit "
            "RETURN a as attribute, collect(properties(u)) as units "
        )
        
        r = self._driver.execute_query(query, tags = tags, result_transformer_=Result.data)
        
        return [AttributeUnitResponseModel(**ri) for ri in r ]


    def update(self, attribute: AttributeModel, attribute_values: List[AttributeValueModel] = None) -> bool:
        return super().update(attribute, attribute_values)

    def update_values(self, attribute: AttributeModel, attribute_values: List[AttributeValueModel], join: bool = True) -> Tuple[AttributeModel,List[AttributeValueModel]]:
        #return super().update_values(attribute, attribute_values, join)
    
        query = (
                "MATCH (a:Attribute {tag : attribute.tag}) " )
    
        if not join:
            query += (
                "MATCH (a)-[:HAS_VALUES]->(av:AttributeValue) "
                "DELETE av "
                "WITH a ")
                
        query += (
                "UNWIND $attribute_values as attribute_value "
                "MERGE (av:AttributeValue {tag : attribute_value.tag}) "
                "SET av += attribute_value "
                "SET av.s = toLower(av.text)+' '+toLower(av.description)), av.created_at = timestamp() "
                "RETURN a as attribute, collect(av) as attribute_values"
                )
            

        r = self._driver.execute_query(query,
                                   routing_="w",
                                   attribute = attribute.model_dump(exclude_none=True),
                                   attribute_values = [av.model_dump(exclude_none=True) for av in attribute_values],
                                   result_transformer_=Result.value)
        print(r)
        return r 
        
    
    def update_value(self, tag, attribute_value_props : dict) -> bool:
        """Updates a single attribute value. 

        Parameters
        ----------
        tag : attribute value (!) tag. 
            The attribute value tag (not the attribute tag!)
        attribute_value_props : dict
            The props you want to update for the given attribute value. 

        Returns
        -------
        bool
            _description_
        """

        query = (
            "MATCH (av:AttributeValue) "
            "WHERE av.tag = $tag "
            "SET av += $attribute_value_props "
            "SET av.s = toLower(av.text)+' '+toLower(av.description)), av.modified_at = timestamp() " #update the search string 
            "RETURN av "
        )

        r = self._driver.execute_query(query, attribute_value_props = attribute_value_props, tag = tag, result_transformer_= Result.value, routing_="w")
        
        return True 