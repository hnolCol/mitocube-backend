from typing import List, Tuple, Literal, Dict
from collections import OrderedDict
from neo4j import Driver, Result
import pandas as pd 
import numpy as np 
from lib.database.abstract.Attributes import AttributesABC

from config.enums.states import SubmissionStatesEnums

from config.models.attributes import AttributeModel, AttributeValueModel, AttributeValuesBySubmissionModel, AttributeUnitResponseModel,  AttributeResponseModel, TraitModel, AttributeTraitTagResponseModel
from config.models.annotations.feature import FeatureModel 
from config.models.feature import FeatureNeoModel
from config.models.attributes import AttributeTreeNode

from services.json import read_json


class Neo4JAttributes(AttributesABC):

    def __init__(self, driver : Driver) -> None:
        
        self._driver = driver
        
        
    def _utils_insert_from_file(self, path_to_file : str = "/Users/hnolte/Documents/GitHub/mitocube-backend/resources/attributes/attributes.json", *args, **kwargs) -> None:
        """"""

        attributes = read_json(path_to_file)
        
        if "attributes" not in attributes: raise ValueError("The loaded file has to have an 'attributes' key.")
        if "traits" not in attributes: raise ValueError("The loaded file has to have a 'traits' key.")

        attribute_df = pd.DataFrame().from_dict(attributes["attributes"])
        attribute_models = [AttributeModel(**k, s = [k["text"],k["tag"],k["group_tag"]]) for k in attributes["attributes"]]
        
        trait_models = [TraitModel(**k, s = [str(k["text"]),k["description"]]) for k in attributes["traits"]]
        
        min_state_attributes = attribute_df.loc[:,["tag","min_state"]].to_dict(orient="records")
        
        
        children = [{"tag" : a.tag, "children" : a.children} for a in attribute_models if isinstance(a.children,list) and len(a.children) > 0]
        #add attribute groups 

        requirements = [{"tag" : tag, "r" : rs.split("|")} for tag, rs in attribute_df.loc[:,["tag","requires"]].dropna(subset=["requires"]).values]

        unique_attribute_groups = np.unique([attribute_group for attribute_group in attribute_df.loc[:,"attribute_group"].dropna().str.split("|", expand = True).values.flatten() if isinstance(attribute_group,str)])
        attribute_tag_group  = [{'tag' : tag, 'group_tag' : group_tag} for tag, group in attribute_df.loc[:,["tag","attribute_group"]].values if isinstance(group,str) and len(group) > 0 for group_tag in group.split("|")]

        query = (
            "UNWIND $attr_group_tags as ag_tag "
            "MERGE (attribute_group:AttributeGroup {tag : ag_tag}) "
            "ON CREATE "
            "SET attribute_group.created_at = timestamp() "
            #since it is just the tag, there should not be a case where the tag is modified since
            #the tag is unique index
        )
        self._driver.execute_query(query, attr_group_tags = unique_attribute_groups, routing_="w")
        
        #add multilabel attributes 
        query = (
            "UNWIND $single_label_attributes as a "
            "MERGE (attribute:Attribute {tag : a.tag}) "
            "ON CREATE "
            "SET attribute.text = a.text, attribute.priority = a.priority, "
            "attribute.group_tag = a.group_tag, attribute.s = a.s, attribute.created_at = timestamp(), "
            "attribute.allow_input = a.allow_input "
            "ON MATCH "
            "SET attribute.text = a.text, attribute.priority = a.priority, "
            "attribute.group_tag = a.group_tag, attribute.s = a.s, attribute.modified_at = timestamp(), "
            "attribute.allow_input = a.allow_input "
        )
        
        self._driver.execute_query(query, single_label_attributes = [a.model_dump(exclude_none=True) for a  in attribute_models])
    
        
        
        #add attributes to attributes_group 
        query = (
            "UNWIND $attr_group as attribute_group "
            "MATCH (a:Attribute {tag : attribute_group.tag}) "
            "MATCH (ag:AttributeGroup {tag: attribute_group.group_tag})"
            "MERGE (a)-[:PART_OF]->(ag) "
        )
        
        self._driver.execute_query(query, attr_group = attribute_tag_group)
        
        #add min state for attributes
        query = (
            "UNWIND $state_props as prop "
            "MATCH (a:Attribute {tag : prop.tag}) "
            "MATCH (s:State {tag : prop.min_state}) " 
            "MERGE (a)-[:REQUIRES_STATE]->(s) "
        )
        self._driver.execute_query(query, state_props = min_state_attributes)
        
        
        ## add children/hierarchy to the attributes
        query = (
            "UNWIND $children as h "
            "MATCH (parent:Attribute {tag: h.tag}) "
            "UNWIND h.children as child_tag "
            "MATCH (child:Attribute {tag: child_tag}) "
            "MERGE (parent)-[:IS_CHILD]->(child) "
        )
        self._driver.execute_query(query, children = children, routing_="w")
        
        #add traits 
        query = (
            "UNWIND $traits as trait "
            "MATCH (a:Attribute) WHERE a.tag = trait.attribute_tag "
            "MERGE (t:Trait {tag : trait.tag}) "
            "ON CREATE "
            "SET t.text = trait.text, t.description = trait.description, t.priority = trait.priority, t.created_at = timestamp(), t.s = trait.s "
            "ON MATCH "
            "SET t.text = trait.text, t.description = trait.description, t.priority = trait.priority, t.modified_at = timestamp(), t.s = trait.s "
            "MERGE (a)-[r:HAS_TRAIT]->(t) "
            "RETURN count(r) as count "
        )
        
        r = self._driver.execute_query(query, children = children, routing_="w", traits = [trait.model_dump(exclude_none=True) for trait in trait_models], result_transformer_=Result.value)
        
        print(f"Added {r} traits.")
        
        if requirements is not None and len(requirements) > 0:
            query = (
                "UNWIND $props as prop "
                "MATCH (a:Attribute {tag : prop.tag}) "
                "UNWIND prop.r as req_tag "
                "MATCH (t:Trait {tag : req_tag}) "
                "MERGE (a)-[r:REQUIRES_TRAIT]->(t) "
                "RETURN count(r) as count "
            )
            r = self._driver.execute_query(query, props = requirements, routing_="w", result_transformer_=Result.value)
            print(r,"requirements added.")
        
    def __read_attributes_values_from_tuple_results(self,ri):
            attribute = AttributeModel(**ri[0])
            if attribute.has_features_value:
                values = [FeatureNeoModel(**av) for av in ri[1]]
            else:
                values = [AttributeValueModel(**av) for av in ri[1]]
            return (attribute,values)
        
    def attribute(self, tag : str) -> AttributeResponseModel:
        """Returns an attribute by tag."""
        
        if not self.exists(tag=tag):
            raise ValueError(f"Attribute with tag {tag} does not exist.")
           
        
        query = ("MATCH (a:Attribute) WHERE a.tag = $tag RETURN properties(a) ")
        
        r = self._driver.execute_query(query, routing_="r", tag = tag, result_transformer_=Result.value)
        
        return AttributeModel(**r[0])
    
    
    def find_attribute(self, search_string : str = None, 
                       attribute_groups : str|List[Literal['dataset', 'filter', 'genotype', 'mandatory', 'qc', 'sample', 'user']] = None,
                       min_state : SubmissionStatesEnums = None, 
                       limit : int = 20,
                       group_by : Literal["attribute_group"] = None) -> List[str]|Dict[str, List[str]]:
        if all(a is None for a in [search_string, attribute_groups]): raise ValueError("Either 'search_string', 'attribute_groups' or 'min_state' must be provided.")

        query = "MATCH (a:Attribute) WHERE "
            
        if search_string is not None:
            query += "a.s CONTAINS $search_string "
        
        if attribute_groups is not None:

            if isinstance(attribute_groups, str):
                attribute_groups = [attribute_groups]

            if search_string is not None:
                query += "AND "

            query += "EXISTS {(ag:AttributeGroup )<-[:PART_OF]-(a) WHERE ag.tag IN $attribute_groups} "
            
            
        if min_state is not None:
            if search_string is not None or (attribute_groups is not None and len(attribute_groups) > 0):
                query += "AND "
            query += " EXISTS {(s:State)<-[:REQUIRES_STATE]-(a) WHERE toInteger(s.tag) <= $min_state} "
            
        
        if group_by is not None:
            if group_by == "attribute_group":
                query += "MATCH (groupByNode:AttributeGroup)<-[:PART_OF]-(a) "
            elif group_by == "min_state":
                query += "MATCH (groupByNode:State)<-[:REQUIRES_STATE]-(a) "

            query += "WITH groupByNode.tag as group_by_node, a.tag as tag, a.priority as priority "
            query += "ORDER BY priority DESC, a.text ASC "
            query += "RETURN group_by_node, collect(tag) as tags "
        else:
            query += "RETURN a.tag ORDER BY a.priority DESC, a.text ASC "


        if limit is not None:
            query += "LIMIT $limit"
            
        if group_by is not None:
            grouped_attribute_tags = self._driver.execute_query(query_=query,
                        routing_="r",
                        attribute_groups = attribute_groups,
                        result_transformer_=Result.values, #requires this to make the correct grouping
                        min_state = min_state,
                        search_string = search_string.lower() if isinstance(search_string,str) else "",
                        limit = limit)
            
            return OrderedDict(grouped_attribute_tags) 
        
        else:   
            attribute_tags = self._driver.execute_query(
                        query_=query,
                        routing_="r",
                        attribute_groups = attribute_groups,
                        result_transformer_=Result.value,
                        min_state = min_state,
                        search_string = search_string.lower() if isinstance(search_string,str) else "",
                        limit = limit)
        
        
            return attribute_tags 
        
        
    def get_required_traits(self, tag: str) -> List[str]:
        ""
        query = (
            "MATCH (a:Attribute {tag : $tag})-[:REQUIRES_TRAIT]->(t:Trait) "
            "RETURN t.tag as tag ORDER BY t.priority "
        )
        
        r = self._driver.execute_query(query, routing_="r", tag = tag, result_transformer_=Result.value)
        return r
        
    def count(self) -> int:
        
        query = (
            "MATCH (a:Attribute) "
            "RETURN count(a) "
        )
        
        r = self._driver.execute_query(query_=query, routing_="r", result_transformer_=Result.value)
        return r[0]
    
    def delete(self, tag: str) -> bool:
        query = (
            "MATCH (a:Attribute {tag :$tag})-[:HAS_TRAIT]->t:Trait) "
            "DETACH DELETE a, t "
        )
        self._driver.execute_query(query = query, routing_="w", tag = tag)
        
    def delete_value(self, tag: str) -> bool:
        
        query = (
            "MATCH (av:AttributeValue {tag : $tag}) "
            "DETACH DELETE av "
        )
        
        self._driver.execute_query(query, routing_="w", tag = tag)
        return True
                
    def exists(self, tag: str = None, trait: str = None) -> bool:
        if tag is None and trait is None:
            raise ValueError("Either tag or value must be not None and a string")
    
        if tag is not None and trait is None:
            query = (
                "WITH EXISTS {(a:Attribute {tag : $tag})} as exists "
            )
        if tag is not None and trait is not None:
            query = (
                "WITH EXISTS {(a:Attribute {tag :$tag})-[:HAS_TRAIT]-(t:Trait {tag : $trait_tag})} as exists "
                     )
        if trait is not None and tag is None:
            query = (
                "WITH EXISTS {(t:Trait {tag : $trait_tag})} as exists "
                )
        query += "RETURN exists"     
        
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value, tag = tag, trait_tag = trait)
        return r[0]
        
    def find_trait(self, search_string : str, attribute_tag : str = None, limit : int = None) -> List[TraitModel]:
        "" 
        if not isinstance(search_string, str): raise TypeError("search_string must be an instance of a string.")
        
        if search_string == "": return self.get_attribute_values_by_attribute_tag()
        
        query = (
            "MATCH (a:Attribute)-[:HAS_TRAIT]->(t:Trait) "
            "WHERE "
        )
        
        if attribute_tag is not None:
            
            query += "a.tag = $attribute_tag AND "
            
        query += ("t.s CONTAINS $search_string "
                  "RETURN t.tag ORDER BY t.priority ")
        
        if limit is not None:
            query += "LIMIT $limit"
        
        trait_tags = self._driver.execute_query(query_=query,
                                       routing_="r",
                                       result_transformer_=Result.value,
                                       attribute_tag = attribute_tag,
                                       search_string = search_string.lower(),
                                       limit = limit)
        
        return trait_tags
        
        
            
    # def find_attribute(self, search_string : str = None, 
    #                    attribute_groups : str|List[Literal['dataset', 'filter', 'genotype', 'mandatory', 'qc', 'sample', 'user']] = None,
    #                    min_state : SubmissionStatesEnums = None, 
    #                    limit : int = 20) -> List[str]:
    #     if all(a is None for a in [search_string, attribute_groups]): raise ValueError("Either 'search_string', 'attribute_groups' or 'min_state' must be provided.")

    #     query = "MATCH (a:Attribute) WHERE "
            
    #     if search_string is not None:
    #         query += "a.s CONTAINS $search_string "
        
    #     if attribute_groups is not None:

    #         if isinstance(attribute_groups, str):
    #             attribute_groups = [attribute_groups]

    #         if search_string is not None:
    #             query += "AND "

    #         query += "EXISTS {(ag:AttributeGroup )<-[:PART_OF]-(a) WHERE ag.tag IN $attribute_groups} "
    
    def get(self, 
            tags : List[str] = None,
            attribute_groups : str|List[Literal['dataset', 'filter', 'genotype', 'mandatory', 'qc', 'sample', 'user']] = None,
            min_state : SubmissionStatesEnums = None, 
            limit : int = None,
            group_by : Literal["attribute_group","min_state"] = None) -> List[str]|Dict[str, List[str]]:
        ""
        
        query = (
            "MATCH (a:Attribute) "
        )
        if tags is not None:
            query = (
                "MATCH (a:Attribute) "
                "WHERE a.tag in $tags "
            )
        
        if attribute_groups is not None:
            if isinstance(attribute_groups,str):
                attribute_groups = [attribute_groups]
                
            if tags is None:
                query += "WHERE EXISTS {(ag:AttributeGroup )<-[:PART_OF]-(a) WHERE ag.tag IN $attribute_groups}"
            else:
                query += "AND EXISTS {(ag:AttributeGroup )<-[:PART_OF]-(a) WHERE ag.tag IN $attribute_groups} "
            
        if min_state is not None:
            if tags is None and attribute_groups is None:
                query += "WHERE EXISTS {(s:State)<-[:REQUIRES_STATE]-(a) WHERE toInteger(s.tag) <= $min_state} "
            else:
                query += "AND EXISTS {(s:State)<-[:REQUIRES_STATE]-(a) WHERE toInteger(s.tag) <= $min_state} "
            
        if group_by is not None:
            if group_by == "attribute_group":
                query += "MATCH (groupByNode:AttributeGroup)<-[:PART_OF]-(a) "
            elif group_by == "min_state":
                query += "MATCH (groupByNode:State)<-[:REQUIRES_STATE]-(a) "

            query += "WITH groupByNode.tag as group_by_node, a.tag as tag, a.priority as priority "
            query += "ORDER BY priority DESC "
            query += "RETURN group_by_node, collect(tag) as tags "
        else:
            query += "RETURN a.tag ORDER BY a.priority DESC "

        if limit is not None:
            query += "LIMIT $limit"

        if group_by is not None:
            grouped_attribute_tags = self._driver.execute_query(query_=query, 
                                                    routing_="r",
                                                    result_transformer_ = Result.values, 
                                                    tags = tags, 
                                                    attribute_groups = attribute_groups, 
                                                    min_state = min_state,
                                                    limit = limit)

            return OrderedDict(grouped_attribute_tags) 
        else:   
            attribute_tags = self._driver.execute_query(query_=query, 
                                                    routing_="r",
                                                    result_transformer_ = Result.value, 
                                                    tags = tags, 
                                                    attribute_groups = attribute_groups, 
                                                    min_state = min_state,
                                                    limit = limit)
            return attribute_tags


    def values(self, tags : List[str]) -> List[AttributeValueModel|FeatureNeoModel]:
        """
        Returns the value of the given attribute tags. 
        CAUTION: for attributes that allow for features, only the previosuly selected features 
        are returned and not the complete proteome. 

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
            "MATCH (a:Attribute)-[:HAS_TRAIT]->(av:Trait) "
            "WHERE a.tag in $tags " #WHERE NOT 'Protein' in labels(av) AND 
            "RETURN properties(av)"
        )
        attribute_values = self._driver.execute_query(query_=query,routing_="r",result_transformer_ = Result.value, tags = tags )
        return [FeatureNeoModel(**av) if "gene_name" in av else AttributeValueModel(**av)  for av in attribute_values]
        
        
    def trait(self, trait_tag : str) -> TraitModel:
        
        if self.exists(trait=trait_tag): 
            query = "MATCH (t:Trait {tag : $trait_tag}) RETURN properties(t) "
            r = self._driver.execute_query(query, routing_= "r", result_transformer_= Result.value, trait_tag = trait_tag)
            return TraitModel(**r[0])
        
        raise ValueError("The trait tag is not known.")


    def get_attribute_group_tags(self, limit : int = None) -> List[str]:
        """Returns the attribute group tags."""
        query = (
            "MATCH (ag:AttributeGroup) "
            "RETURN ag.tag "
        )
        if limit is not None:
            query += "LIMIT $limit "
        attribute_group_tags = self._driver.execute_query(query_=query, routing_="r", result_transformer_=Result.value, limit = limit)
        return attribute_group_tags

    def get_children(self, tag : str, limit  : int = None) -> List[str]:
        "Returns the attribute's children tags."
        query = (
            "MATCH (a:Attribute)-[:IS_CHILD]->(child:Attribute) "
            "WHERE a.tag = $tag "
            "RETURN child.tag ORDER by child.priority DESC "
        )
        if limit is not None:
            query += "LIMIT $limit"
            
        attribute_tags = self._driver.execute_query(query_=query, routing_="r", tag = tag, limit = limit, result_transformer_= Result.value)
        if not isinstance(attribute_tags,list): return []
        
        return attribute_tags
    
    
    def get_trait_tags(self, tag : str = None, limit : int = None) ->  List[str]:
        """Returns the trait_tags for a single attribute tag, if you want to get 
        traits for more than one attribute use '"""
        if tag is not None:
            query = (
                "MATCH (a:Attribute)-[:HAS_TRAIT]->(trait:Trait) "
                "WHERE a.tag = $tag "
            )
        else:
            query = (
                "MATCH (trait:Trait) "
            )
        
        query += "RETURN trait.tag ORDER BY trait.priority DESC "
        if limit is not None:
            query += "LIMIT $limit "
    

        r = self._driver.execute_query(query_=query, routing_="r", result_transformer_=Result.value, tag = tag, limit = limit)
        return r 

        
    def get_trait_text(self, tag : str) -> str:
        "Returns the text associated with a trait tag. If not found, an empty string is returned."

        query = "MATCH (t:Trait {tag : $tag}) RETURN t.text "
        r = self._driver.execute_query(query, routing_="r", tag = tag, result_transformer_=Result.value)
        
        return r[0] if len(r) > 0 else ""
        

    def count_traits(self, tag : str) -> int:
        """Returns the number of traits for a single attribute tag"""
        query = (
            "MATCH (a:Attribute)-[:HAS_TRAIT]->(trait:Trait) "
            "WHERE a.tag = $tag "
        )
        
        query += "RETURN count(trait) "
        
        r = self._driver.execute_query(query_=query, routing_="r", result_transformer_=Result.value, tag = tag)
        return r[0]
    
    def get_values(self, tags : List[str]) -> List[AttributeValueModel|FeatureNeoModel]:
        """Returns the attribute values by a list of attribute value tags.

        Parameters
        ----------
        tags : List[str]
            _description_

        Returns
        -------
        List[AttributeValueModel|FeatureNeoModel]
            _description_
        """
        query = (
            "MATCH (av:AttributeValue) "
            "WHERE av.tag in $tags " #WHERE NOT 'Protein' in labels(av) AND 
            "RETURN properties(av)"
        )
        attribute_values = self._driver.execute_query(
            query_=query,
            routing_="r",
            result_transformer_ = Result.value, 
            tags = tags )
        
        return [FeatureNeoModel(**av) if "gene_name" in av else AttributeValueModel(**av)  for av in attribute_values]
        
    
    def get_values_by_submission_tag(self, submission_tag : str, tags : List[str] = None, include_input : bool = False) -> List[AttributeValueModel]:
        "Returns the props of the attributes and its values."
        
        if tags is not None:
            
            if include_input:
                
                query = (
                    "MATCH (submission:Submission)-[r:HAS_ATTRIBUTE_VALUE]->(av:AttributeValue)"
                    "WHERE submission.tag = $submission_tag AND  av.tag in $tags "
                    "OPTIONAL MATCH (av)-[r_input:HAS_VALUE_OF_UNIT]->(u:Unit)<-[:HAS_UNIT]-(unittype:UnitType) "
                    "WHERE r_input.submission_tag = $submission_tag "
                    "RETURN av.tag as trait_tag, properties(av) as trait, collect({unittype_tag: r_input.unittype_tag, unit_tag : u.tag, value : r_input.value, unit_text: u.text, priority : unittype.priority}) as user_input"
                )
            
            else:
            
                query = (
                    "MATCH (submission:Submission)-[r:HAS_ATTRIBUTE_VALUE]->(av:AttributeValue) "
                    "WHERE submission.tag = $submission_tag AND  av.tag in $tags "
                    "RETURN properties(av) "
                )
            
        
        
        else:
            query = (
                "MATCH (a:Attribute)-[:HAS_TRAIT]->(av:Trait)<-[r:HAS_ATTRIBUTE_VALUE]-(submission:Submission) "
                "WHERE submission.tag = $submission_tag "
                "WITH {attribute_tag : a.tag} as attr_tag, av " #add the attribute tag 
                "RETURN apoc.map.merge(properties(av), attr_tag)"
            )
        
        if include_input:
            r = self._driver.execute_query(query, tags = tags, routing_="r", result_transformer_=Result.data, submission_tag = submission_tag)
            if not isinstance(r,list): raise TypeError("Trait tags did not match any node. Checks the tags or submission_tag")
            return [AttributeValueModel(**ri["trait"], 
                                        user_input=OrderedDict([(user_input["unittype_tag"], {"value" : user_input["value"], "unit_tag" : user_input["unit_tag"], "unit_text" : user_input["unit_text"]}) 
                                                                for user_input in sorted(ri["user_input"], key = lambda x : 0 if x["priority"] is None else -x["priority"])]))
                    for ri in r if "trait" in ri]
        
        attribute_values  = self._driver.execute_query(query, tags = tags, routing_="r", result_transformer_=Result.value, submission_tag = submission_tag)
       # attribute_values_props = [av.value() for av in attribute_values]
        return [AttributeValueModel(**av) for av in attribute_values]
    
    # def get_attributes_and_values_for_submission(self, submission_tag : str) -> AttributeResponseModel:
        
    #     query = (
    #         "MATCH (submission:Submission {tag : $submission_tag}) "
    #         "MATCH (a:Attribute)<-[:HAS_VALUES_FOR_ATTRIBUTE]-(submission)-[:HAS_ATTRIBUTE_VALUE]->(av:AttributeValue) "
    #         "WITH a, av "
    #         "ORDER BY a.priority DESC, a.min_state ASC " 
    #         "WITH {attributes : collect(DISTINCT properties(a)), attribute_values : collect(DISTINCT properties(av))} as output "
    #         "RETURN output"
    #     )
        
    #     r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value, submission_tag=submission_tag)
    
    #     return AttributeResponseModel(**r[0])
    
    
    def get_attribute_values_by_dataset_tags(self, dataset_tags : List[str], attribute_tags : list[str] = None, attribute_value_tags : List[str] = None) -> List[AttributeValuesBySubmissionModel]:
        """Finds all the attribute values that are assigned to the submissions and returns the number of submissions
        that match each attribute value. This is a convenient function to get the submission tags that have 
        an attribute value and how many are used, as used in a filtering approach to indicate the fraction of datasets.

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
        return [AttributeValuesBySubmissionModel(**ri.data()) for ri in r]
        
        
    def get_mandatory_attributes(self, state : SubmissionStatesEnums = None) -> List[AttributeModel]:
        
        
        query = (
            "MATCH (a:Attribute) "
            "WHERE a[$mandatory_name] "
        )
        
        if state is not None:
            
            query += "AND EXISTS {(a)-[:REQUIRES_STATE]->(s:State) WHERE s.tag = $state} "
        
        query += "RETURN properties(a) ORDER BY a.priority DESC "
            
        r = self._driver.execute_query(query,routing_="r",result_transformer_=Result.value, state=state, mandatory_name="mandatory_for_active")
        return [AttributeModel(**ri) for ri in r]
    
    
    def get_min_state(self, tag : str) -> SubmissionStatesEnums:
        """Returns the minimum state for the given attribute tag."""
        
        query = (
            "MATCH (a:Attribute)-[:REQUIRES_STATE]->(s:State) "
            "WHERE a.tag = $tag "
            "RETURN s.tag  "
        )
        
        r = self._driver.execute_query(query, routing_="r", tag = tag, result_transformer_=Result.value)

        if len(r) == 0:
            raise ValueError(f"Attribute with tag {tag} does not have a minimum state defined.")
        return SubmissionStatesEnums(int(r[0]))


    def get_priority(self, tag : str) -> int:
        """Returns the priority of the attribute with the given tag."""
        
        query = (
            "MATCH (a:Attribute) "
            "WHERE a.tag = $tag "
            "RETURN a.priority "
        )
        
        r = self._driver.execute_query(query, routing_="r", tag = tag, result_transformer_=Result.value)
        
        if len(r) == 0:
            raise ValueError(f"Attribute with tag {tag} does not exist.")
        
        return r[0] 
    
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
            "MATCH (a)-[:HAS_TRAIT]->(av:Trait) "
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
            "RETURN properties(a) as attribute "
        )
        
        r, _ , _ = self._driver.execute_query(query, state_tag = state)
        
        return [AttributeModel(**ri[0]) for ri in r]
    
    def get_attributes_for_user(self) -> List[AttributeModel]:
        
        return self._get_attributes_by_boolean_param(param_name="allow_for_user")
    
    def get_attributes(self):
        ""
        
        query = (
            "MATCH (a:Attribute) "
            "MATCH (a)-[:HAS_TRAIT]->(av:Trait) "
            "RETURN properties(a), collect(properties(av)) as values "
        )
        
        return self._driver.execute_query(query)
        
    def get_attributes_by_search_string(self, 
                                        search_string : str, 
                                        min_state : SubmissionStatesEnums = SubmissionStatesEnums.SUBMITTED, 
                                        param_name : str = None, 
                                        limit : int = None):
        """Returns attributes by search query.

        Parameters
        ----------
        search_string : str
            _description_
        min_state : SubmissionStatesEnums, optional
            _description_, by default SubmissionStatesEnums.SUBMITTED
        param_name : str, optional
            _description_, by default None
        """
        query = "MATCH (a:Attribute) "
        
        if min_state is not None:
            query += "WHERE EXISTS {(s:State)<-[:REQUIRES_STATE]-(a) WHERE toInteger(s.tag) <= $min_state} "
        
        if param_name is not None:
            if min_state is None:
                query += "WHERE a[$param_name] "
            else:
                query += "AND a[$param_name] "
        if param_name is None and min_state is None:
            query += "WHERE a.s CONTAINS $search_string "
        else:
            query += "AND a.s CONTAINS $search_string "
        query += (
            "RETURN properties(a) as attribute, [] as traits ORDER BY a.priority DESC "
        )
        
        if limit is not None:
            query += "LIMIT $limit"
        
        r  = self._driver.execute_query(
            query,
            search_string=search_string.lower(),
            min_state = min_state, 
            param_name = param_name, 
            result_transformer_= Result.data,
            limit = limit,
            routing_="r", 
            )
        return r
        
    def find_attributes_and_traits(self, 
                                    search_string : str = None, 
                                    min_state : SubmissionStatesEnums = SubmissionStatesEnums.SUBMITTED, 
                                    limit : int = None, 
                                    attribute_groups : List[Literal['dataset', 'filter', 'genotype', 'mandatory', 'qc', 'sample', 'user'] ]= None) -> List[AttributeTraitTagResponseModel]:
        """Finds the attribute and the corresponding attribute values. 
        Please note that if a search matches the attribute, then all attribute value are returned.
        The result is ordered by the attribute priority and trait priority.
        If the search string is None, then all attributes are returned.
        
        Parameters
        ----------
        search_string : str
            _description_
        min_state : SubmissionStatesEnums, optional
            _description_, by default SubmissionStatesEnums.SUBMITTED
        limit : int, optional
            Maximum number of attributes to be returned. Does not account for the traits. 
        Returns
        -------
        List[AttributeTraitTagResponseModel]
            List of attribute_tag and corresponding trait_tags
        """
        query = "MATCH (a:Attribute)-[:HAS_TRAIT]->(t:Trait) "
        
        where_clauses = []
        params = {}

        if search_string is not None:
            params["search_string"] = search_string.lower()
        if min_state is not None:
            params["min_state"] = min_state
        if attribute_groups is not None:
            params["attribute_groups"] = attribute_groups


        if min_state is not None:
            where_clauses.append("EXISTS {(a)-[:REQUIRES_STATE]->(s:State) WHERE s.tag <= $min_state}")
        if attribute_groups is not None:
            where_clauses.append("EXISTS {(ag:AttributeGroup)<-[:PART_OF]-(a)} WHERE ag.tag IN $attribute_groups")

        if where_clauses:
            query += "WHERE " + " AND ".join(where_clauses) + " "
            
            
        if search_string is not None:
            query += " AND (a.s CONTAINS $search_string OR t.s CONTAINS $search_string) "

            
        query += (
            "WITH a, t ORDER BY a.priority DESC, t.priority DESC "
            "RETURN a.tag as attribute_tag, collect(DISTINCT t.tag) as trait_tags "
        )

        if limit is not None:
            query += "LIMIT $limit "
        
        r  = self._driver.execute_query(
            query,
            search_string=search_string.lower() if search_string is not None else "",
            limit = limit,
            min_state = min_state, 
            attribute_groups = attribute_groups,
            result_transformer_= Result.data,
            routing_="r", 
            database_="neo4j")
        
        
        return [AttributeTraitTagResponseModel(**ri) for ri in r]


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
            "MATCH (a:Attribute)-[:HAS_UNIT_TYPE]-(ut:UnitType) "
            "WHERE a.tag IN $tags "
            "WITH a, ut "
            "ORDER BY a.priority, ut.priority DESC "
            "RETURN a.tag AS attribute_tag, "
            "       ut.tag AS unit_type_tag, "
            "       ut.text AS unit_type_text "
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
    
    
    def get_unittype(self, tags: List[str]) -> Dict[str,List[str]]:
        
        query = (
            "MATCH (a:Attribute) "
            "WHERE a.tag in $tags "
            "MATCH (a)-[:HAS_UNIT_TYPE]-(unittype:UnitType) "
            "WITH a, unittype ORDER BY unittype.priority DESC "
            "RETURN a.tag, collect(unittype.tag) "
        )
        
        
        r = self._driver.execute_query(query,routing_="r",result_transformer_=Result.values, tags = tags)
        return OrderedDict([(attribute_tag, unit_type_tags) for attribute_tag, unit_type_tags in r])
    
    
    def get_attribute_hierarchy(self, tags : List[str], submission_tag : str) -> List[AttributeTreeNode]:
        """_summary_

        Parameters
        ----------
        tags : List[str]
            _description_
        
        submission_tag: str 
            The submission tag- 

        Returns
        -------
        List[AttributeTreeNode]
            _description_

        Yields
        ------
        Iterator[List[AttributeTreeNode]]
            AttributeTreeNode that has the following keys:
                - tag : The attribute tag at that level.
                - IS_PARENT_OF: List of tags that are children of the 
                    attribue given by tag.  

        Raises
        ------
        TypeError
            _description_
        """
        
        query = (
            
            #get the attributes that have no hierarchy 
            "UNWIND $tags AS tag "
            "MATCH path = (root:Attribute)-[:IS_PARENT_OF*]->(leaf:Attribute) "
            "WHERE ANY(node IN nodes(path) WHERE node.tag = tag) "
            "  AND EXISTS {(submission:Submission {tag : $submission_tag})-[:HAS_VALUES_FOR_ATTRIBUTE]->(leaf)} "
            "  AND EXISTS {(submission:Submission {tag : $submission_tag})-[:HAS_VALUES_FOR_ATTRIBUTE]->(root)} "
            "WITH collect(path) AS all_paths " #, root_attr, root_tags
            
            "MATCH (root:Attribute) "
            "WHERE root.tag IN $tags AND NOT ANY(path in all_paths WHERE apoc.coll.contains(nodes(path), root)) " #filter out any node that is already in the all_path
            "  AND EXISTS {(submission:Submission {tag : $submission_tag})-[:HAS_VALUES_FOR_ATTRIBUTE]->(root)} "
            "  AND EXISTS {(root)-[:IS_PARENT_OF]->(:Attribute)} "
            "  AND NOT EXISTS {(root)<-[:IS_PARENT_OF]-(:Attribute)} "
            "WITH collect({tag: root.tag, priority: root.priority, min_state: root.min_state, root : true}) AS root_attr, collect(root.tag) as root_tags, all_paths "
            
            #match attributes that are parents but no child is in the tag list. 
            "UNWIND $tags AS tag "
            "MATCH (standalone:Attribute {tag: tag}) "
            "WHERE NOT EXISTS {(standalone)-[:IS_PARENT_OF]-(:Attribute)} "
            "  AND EXISTS {(submission:Submission {tag : $submission_tag})-[:HAS_VALUES_FOR_ATTRIBUTE]->(standalone)} "
            "WITH all_paths, {tag: standalone.tag, priority: standalone.priority, min_state: standalone.min_state, standalone:true} AS no_parent_attr, root_attr, root_tags "
            

            "CALL apoc.convert.toTree(all_paths, false, { "
            "    nodes: {Attribute: ['tag', 'priority', 'min_state']}, "
            "    sortPaths: false "
            "}) YIELD value AS tree "
            "RETURN tree, collect(no_parent_attr) as standalones , root_attr"
        )

        r = self._driver.execute_query(query, routing_="r", tags=tags, submission_tag = submission_tag, result_transformer_=Result.data)
        
        if len(r) == 0: raise TypeError("The response did match a list of length > 0")
        attributes_tree = [ri["tree"] for ri in r if len(ri["tree"]) > 0] + r[0]["standalones"] + r[0]["root_attr"]#standlones are always the same in each item of the array, just take the first one. 
        #maybe bettter to separate the DB queries? 
        attribute_tres_sorted = sorted(attributes_tree, key = lambda x : (-x["min_state"], x["priority"]), reverse=True)
    
        return [AttributeTreeNode(**attributes_tree) for attributes_tree in attribute_tres_sorted]
        