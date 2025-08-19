from typing import List, Dict, Tuple 
from neo4j import Driver, Result
import pandas as pd 

from lib.database.abstract.Meta import MetaABC

from lib.database.abstract.Attributes import AttributesABC
from config.settings.metatexts import MetaTexts
from config.models.submissions.submissions import MinimalMetadataModel, DatasetSubmissionModel
from config.models.user import UserModel 
from config.models.unit import UnitTypeInputModel 
from config.enums.units import UnitsEnum
from collections import OrderedDict
from services.units import extract_user_input
class Neo4JMetaHandler(MetaABC):

    def __init__(self, driver : Driver, attributes : AttributesABC) -> None:
        
        self._driver = driver
        self._attributes = attributes
        self.create_title_search_index() ##put in creator!! TODO 
        
        
    def exists(self, tag: str) -> bool:
        "Checks if the submission exists."
        query = (
            "WITH EXISTS {(submission:Submission {tag : $tag})} as submission_exists "
            "RETURN submission_exists "
        )    
        r = self._driver.execute_query(query, tag = tag, result_transformer_=Result.value)
        return r[0]
        
    def get(self, tags : List[str]) -> List[MinimalMetadataModel]:
        """Returns the minimal meta information of a dataset node (e.g. properties)
        from Neo4J database. 
        
        Parameters
        ----------
        tags : List[str]
            The list of tags that the minimal metadata should be returned. 
        """
        query = (
            "MATCH (submission:Submission) "
            "WHERE submission.tag in $tags "
            "OPTIONAL MATCH (submission)<-[:OWNS]-(u:User) "
            "MATCH (submission)-[:HAS_ATTRIBUTE_VALUE]->(av:AttributeValue)<-[:HAS_VALUE]-(a:Attribute {tag:'att_proteome'}) " #THIS excludes datasets from being found if the prteooem does not exist.
            "WITH collect(av.tag) as proteome_tags, submission, EXISTS {(submission)<-[:QUANTIFIED_IN]-(:Protein)} as has_datatable, u "
            "WITH {user_tag : u.tag, proteome_tags : proteome_tags, has_datatable : has_datatable} as add_meta, submission "
            "RETURN apoc.map.merge(properties(submission), add_meta)"
        )
        ""
        metadata = self._driver.execute_query(query,result_transformer_=Result.value, tags = tags)
        return [MinimalMetadataModel(**x) for x  in metadata]
        
    def get_metatext(self, tags : List[str], metatext_tag :str = None) -> pd.DataFrame:
        ""
        query = (
            "MATCH (submission:Submission) "
            "WHERE submission.tag in $tags "
            "MATCH (submission)<-[:DESCRIBES]-(m:Metatext)-[r:HAS_CONTENT]->(c:Content) "
            "WHERE r.submission_tag = submission.tag and c.content IS NOT null and c.content <> '' "
            )
        if metatext_tag is not None:
            query += "AND m.tag = $metatext_tag "
        
        query += "RETURN submission.tag as submission_tag, m.tag as tag, m.title as title, c.content as content ORDER BY m.priority DESC "
        meta_text = self._driver.execute_query(query,tags=tags,result_transformer_=Result.to_df, metatext_tag = metatext_tag)
        return meta_text
    
    def add_metatext(self, tag : str, user_tag : str, meta_texts : Dict[str,str]):
        "" 
        metatext_settings = MetaTexts()
        meta_texts = [{"tag" : tag, "content" : content, "title" : metatext_settings.names[tag], "priority" : metatext_settings.priorities[tag]} for tag,content in meta_texts.items() if content != "" and tag in metatext_settings.names] 
        
        query = (
            "UNWIND $meta_texts as metatext "
            "MATCH (submission:Submission {tag : $tag}) "
            "MERGE (m:Metatext {tag : metatext.tag }) "
            "SET m.title = metatext.title, m.priority = metatext.priority "
            "WITH submission, m, metatext "
            "MERGE (submission)<-[r_d:DESCRIBES]-(m) "
            "SET r_d.created_at = timestamp(), r_d.user_tag = $user_tag "
            "WITH submission, m, metatext "
            "MERGE (m)-[r_has_content:HAS_CONTENT {submission_tag : $tag}]-(c:Content) "
            "SET c.content = metatext.content"
        )
        
        self._driver.execute_query(query, tag = tag, meta_texts = meta_texts, user_tag = user_tag, routing_="w")
        
    def add_samples_genotypes(self, meta_data : DatasetSubmissionModel):
        """Adds the sample genotypes

        Parameters
        ----------
        meta_data : DatasetSubmissionModel, optional
            The dataset submission model. 
        """
        
        samples_genotypes = meta_data.samples_genotypes
        if len(samples_genotypes) == 0: raise ValueError("Sample genotypes are not found in the DatasetSubmissionModel.")
        
        sample_names = meta_data.sample_names
        sample_genotypes_props = [
            {"tag" : genotype_tag, 
             "sample_name" : sample_names[sample_index]} for genotype_tag, sample_indices in samples_genotypes.items() for sample_index in sample_indices]
        
        query = ( 
                "MATCH (submission:Submission {tag : $tag}) "
                "UNWIND $props as prop "
                "MATCH (g:Genotype {tag : prop.tag}) "
                "MATCH (s:Sample {tag : prop.sample_name}) "
                "MERGE (submission)-[:HAS_GENOTYPE]-(g) "
                "MERGE (g)<-[r:HAS_GENOTYPE]-(s) "
                "SET r.created_at = timestamp(), r.attribute_tag = 'att_genotype'"
                )

        self._driver.execute_query(query, props = sample_genotypes_props, tag = meta_data.tag)
    
    def add_samples_attributes(self, meta_data : DatasetSubmissionModel) -> Tuple[int,int]:
        """_summary_

        Parameters
        ----------
        meta_data : DatasetSubmissionModel, optional
            _description_, by default meta
            
        Returns
        --------
        Tuple[int,int]
            Number of deleted trait connections 
            Number of added trait connections 
        """
        sample_attributes_data = []
        attributes_to_connect = []
        for n, (attribute_tag, attribute_value) in enumerate(meta_data.samples_attributes.items()):
            attributes_to_connect.append({"attribute_tag" : attribute_tag, "values" : []})
            for trait_tag, sample_idx in attribute_value.items():
                attributes_to_connect[n]["values"].append(trait_tag)
                
                # if meta_data.samples_attributes_input is not None and attribute_tag in meta_data.samples_attributes_input:
                #     user_inputs  = meta_data.samples_attributes_input[attribute_tag]
                #     attributes_to_connect[n]["inputs"] = [u.model_dump() for u in user_inputs]
    
                for idx in sample_idx:
                    sample_name = meta_data.sample_names[idx]
                    sample_attributes_data.append(
                        {
                            "attribute_tag" : attribute_tag,
                            "index" : n,
                            "sample_name" : sample_name, 
                            "sample_index" : idx,
                            "trait_tag" : trait_tag##matching proteins by tag.
                        }
                    )
                    
        query = ()
                    

        query = (
            "UNWIND $sample_attributes_data as sample_attr "
            "MATCH (s:Sample {tag : sample_attr.sample_name}) "
            "MATCH (av:AttributeValue {tag : sample_attr.trait_tag}) "
            "MERGE (s)-[r_s:HAS_SAMPLE_ATTRIBUTE_VALUE]-(av) "
            "SET r_s += {index : sample_attr.index, attribute_tag : sample_attr.attribute_tag, created_at : timestamp()} "
            "WITH av, s "
            "MATCH (submission:Submission) "
            "WHERE submission.tag = $submission_tag "
            "UNWIND $attributes as attr "
            "MATCH (a:Attribute) "
            "WHERE a.tag = attr.attribute_tag "
            "MERGE (submission)-[:HAS_VALUES_FOR_ATTRIBUTE]->(a) "
            "WITH submission, a, attr "
            "MATCH (av: AttributeValue) "
            "WHERE av.tag in attr.values "
            "MERGE (submission)-[r:HAS_ATTRIBUTE_VALUE]-(av) "
            "SET r.attribute_tag = a.tag "
            "WITH a, av, attr, submission "
            "MERGE (a)-[:HAS_VALUE]->(av) "
            # "WITH attr, submission "
            # "MATCH (submission)-[:HAS_SAMPLE]->(s:Sample {index : user_input.sample_index}) " #match the sample of the dataset 
            # "MATCH (s)-[r_u_i:HAS_SAMPLE_ATTRIBUTE_VALUE]->(av_u) " #create a relationship
        )
                
        r = self._driver.execute_query(query,
                                       result_transformer_=Result.data,
                                        submission_tag=meta_data.tag, 
                                attributes = attributes_to_connect,
                                sample_attributes_data = sample_attributes_data,
                                database_="neo4j", 
                                routing_="w", 
                                   )
        
    
    
    # def _add_process_node(self, node, condition_procedure_tag : str = None):
        
    #     if node["type"] == "Attribute"
    
    def handle_children(self, sample_tag, trait_node, parent_tag):
        
        for attribute_node in trait_node["children"]:
            attribute_tag = attribute_node["tag"]
            trait_nodes = attribute_node["children"]
            if len(trait_nodes) > 0:
                for trait_node in trait_nodes:
                    parent_tag_2 = self.add_condition_value(sample_tag, attribute_tag=attribute_tag, value = trait_node.get("value"), trait_tag= trait_node["tag"], parent_tag=parent_tag)
                    if len(trait_node.get("children",[])) > 0:
                        for child in trait_node["children"]:
                            self.handle_children(sample_tag, trait_node=trait_node, parent_tag=parent_tag_2)
    
    def add_condition_value(self, sample_tag : str, parent_tag : str, attribute_tag : str, trait_tag : str, value : str|float|int = None ):
        
        cv_tag = f"{sample_tag}-cv-{parent_tag}-{trait_tag}"
        query = (
            "MATCH (ca:ConditionApplication|ConditionValue {tag : $parent_tag}) "
            "MERGE (cv:ConditionValue {tag : $cv_tag}) "
        )
        if value is not None:
            query += "SET cv.value = $value "
            
        query += (
                "WITH ca,cv "
                "MERGE (a:Attribute {tag : $attribute_tag}) "
                "MERGE (t:Trait {tag : $trait_tag}) "
                "WITH ca,cv,a,t "
                "MERGE (cv)-[:OF_ATTRIBUTE]-(a) "
                "MERGE (cv)-[:HAS_TRAIT]-(t) "
                "MERGE (ca)-[:HAS_VALUE]->(cv) "
            )
        
        self._driver.execute_query(query, value = value, trait_tag = trait_tag, cv_tag = cv_tag, attribute_tag = attribute_tag, parent_tag = parent_tag)
        return cv_tag 
    
    def add_condition_procedure(self, sample_tag : str, sample_data : List):
        "" 
        
        # sample_data = [
        #         {
        #             "type": "Attribute",
        #             "tag": "compound",
        #             "children": [
        #                 {
        #                     "type": "Trait",
        #                     "tag": "DMSO",
        #                     "children": [
        #                         {
        #                             "type": "Attribute",
        #                             "tag": "Concentration",
        #                             "children": [
        #                                 {"type": "Trait", "tag": "mM", "value": 2, 
        #                                  "children": [
        #                                      {"type" : "Attribute", "tag" : "temperature", "children" : [
        #                                          {"type" : "Trait", "tag" : "high"}
        #                                      ]}
        #                                  ]}
        #                             ]
        #                         },
        #                         {
        #                             "type": "Attribute",
        #                             "tag": "Time",
        #                             "children": [
        #                                 {"type": "Trait", "tag": "h", "value": 5, "children": []}
        #                             ]
        #                         }
        #                     ]
        #                 }
        #             ]
        #         }
        #         ]
        
        
        for condition_application in sample_data:
            attribute_tag = condition_application["tag"]
            for trait_node in condition_application["children"]:
                trait_tag = trait_node["tag"]
                ca_tag = f"{sample_tag}-{trait_tag}"
                query = (
                    "MERGE (s:Sample {tag : $sample_tag}) "
                    "MERGE (ca:ConditionApplication {tag : $ca_tag}) "
                    "WITH ca, s "
                    "MERGE (a:Attribute {tag : $attribute_tag}) "
                    "MERGE (t:Trait {tag : $trait_tag}) "
                    #connect to sample 
                    "MERGE (s)-[:HAS_APPLICATION]->(ca) "
                    "MERGE (ca)-[:OF_ATTRIBUTE]->(a) "
                    "MERGE (ca)-[:INSTANCE_OF]-(t) "
                )
                
                self._driver.execute_query(query, routing_= "w", ca_tag = ca_tag, sample_tag = sample_tag, trait_tag = trait_tag, attribute_tag = attribute_tag)        
                
                if len(trait_node.get("children",[])) > 0:
                    for child in trait_node["children"]:
                        self.handle_children(sample_tag, trait_node=trait_node, parent_tag=ca_tag)
                
    
    
    
    
    @staticmethod
    def _add_sample_attrs(tx, sample_attributes_data, relation_label : str = "HAS_SAMPLE_ATTRIBUTE_VALUE"):
        query = (
            f"UNWIND $props as prop "
            "MATCH (s:Sample {tag : prop.sample_name}) "
            "MATCH (a:AttributeValue {tag : prop.attribute_value_tag}) "
            "WITH s,a, prop "
            f"MERGE (s)-[r:{relation_label} {{index : prop.index, attribute_tag : prop.attribute_tag}}]->(a) "
            "RETURN count(r) as count"
        )
        
        r = tx.run(query,props = sample_attributes_data, relation_label = relation_label)
        #print("sample attributes!!")
        
        
    def _sample_attribute_to_dict(self, sample_attributes : pd.DataFrame)-> Dict[str,Dict[str,List[int]]]:
        ""
        if any(column_name not in sample_attributes.columns for column_name in ["attribute_index","attribute_tag","tag","sample_index"]): 
            raise ValueError("sample attribute must have the required column names. ['attribute_index','attribute_tag','tag','sample_index']")
        sample_attributes_dict = OrderedDict()
        for _, groupData in sample_attributes.groupby("attribute_index", sort = True):
            attribute_tag = groupData["attribute_tag"].values[0]
            if attribute_tag not in sample_attributes_dict:
                sample_attributes_dict[attribute_tag] = {}
            for tag, tagData in groupData.groupby("tag"):
                sample_attributes_dict[attribute_tag][tag] = tagData["sample_index"].to_list()
        
        return sample_attributes_dict
    
    def get_dataset_attributes(self, tag : str) -> Dict[str,List[str]]:
        "" 
        #WITH UNITS
        # query = (
        #     "MATCH (submission:Submission {tag : $tag})-[:HAS_ATTRIBUTE_VALUE]->(av:AttributeValue)<-[:HAS_VALUE]-(a:Attribute) "
        #     "WHERE NOT EXISTS {(av)<-[:HAS_SAMPLE_ATTRIBUTE_VALUE]-(sample:Sample)<-[:HAS_SAMPLE]-(submission)} "
        #     "OPTIONAL MATCH path=(av)-[r:HAS_VALUE_OF_UNIT]->(unit:Unit) "
        #     "WHERE r.submission_tag = $tag "
        #     "WITH a, av, collect({ "
        #         "attribute_value_tag: av.tag, "
        #         "unit_tag: unit.tag, "
        #         "value: r.value "
        #         "}) AS user_unit_input ORDER BY a.min_state ASC, a.priority DESC " 
        #     "RETURN a.tag, collect(av.tag) as trait_tags, user_unit_input as user_unit_input "
        # )
        
        query = (
            "MATCH (submission:Submission {tag : $tag})-[:HAS_ATTRIBUTE_VALUE]->(av:AttributeValue)<-[:HAS_VALUE]-(a:Attribute) "
            "WHERE NOT EXISTS {(av)<-[:HAS_SAMPLE_ATTRIBUTE_VALUE]-(sample:Sample)<-[:HAS_SAMPLE]-(submission)} "
            "WITH a, av ORDER BY a.min_state ASC, a.priority DESC " 
            "RETURN a.tag, collect(av.tag) "
        )
        r = self._driver.execute_query(query_=query,tag=tag,result_transformer_=Result.values)
        return dict(r) 
        
    def get_sample_attributes_and_genotypes(self, tag : str, as_sample_map : bool = True) -> Tuple[Dict,pd.DataFrame]|Dict:
        ""
        query = (
            "MATCH (submission:Submission {tag : $tag})-[:HAS_SAMPLE]->(s:Sample)  "
            "MATCH (g:Genotype)<-[:HAS_GENOTYPE]->(s) "
            "RETURN s.index as sample_index, s.text as sample_text, g.tag as tag, -1 as attribute_index, 'att_genotype' as attribute_tag, g.text as text, false as is_feature  "
            "ORDER BY attribute_index, sample_index "
            "UNION ALL "
            "MATCH (submission:Submission {tag : $tag}) "
            "MATCH (submission)-[:HAS_SAMPLE]->(s:Sample) "
            "MATCH (s)-[r:HAS_SAMPLE_ATTRIBUTE_VALUE]->(av:AttributeValue|Protein)<-[:HAS_VALUE]-(a:Attribute) "
            "RETURN s.index as sample_index, s.text as sample_text, av.tag as tag, r.index as attribute_index, a.tag as attribute_tag, av.text as text, 'Protein' in labels(av) as is_feature  " #g.tag as ag, g.tex as text, 
            "ORDER BY attribute_index, sample_index"
        )
        r = self._driver.execute_query(query, tag = tag, result_transformer_=Result.to_df) 
        
        if as_sample_map:
            sample_map = r.pivot_table(index="sample_index",columns="attribute_tag",values="tag", aggfunc=lambda x: " ".join(x)) 
            #add sample index
            sample_name_to_index_mapper = dict([(sample_index,sample_text) for sample_text, sample_index in r[["sample_text","sample_index"]].drop_duplicates(subset=["sample_index"]).values])
            sample_index = sample_map.index.map(sample_name_to_index_mapper)
            sample_map.loc[:,"sample_text"] = sample_index.values
            
            return self._sample_attribute_to_dict(r), sample_map
        
        return self._sample_attribute_to_dict(r) 
        
    def get_sample_genotypes(self, tag : str):
        "" 
        #(g)<-[r:HAS_GENOTYPE]-(s)
        query = (
            "MATCH (d:Dataset {tag : $tag}) "
            "MATCH (d)-[:HAS_SAMPLE]->(s:Sample)-[r:HAS_GENOTYPE]->(g:Genotype) "# <-[:HAS_VALUE]-(a:Attribute)
            "RETURN s.index as sample_index, s.text as sample_text, g.tag as tag, g.text as text, 'att_genotype' as attribute_tag "
            "ORDER BY sample_index "
        )
        r = self._driver.execute_query(query, tag = tag, result_transformer_=Result.to_df)
        return r

        
    def get_sample_attributes(self, tag : str, as_sample_map : bool = True) -> Tuple[Dict,pd.DataFrame]|Dict:
        
        query = (
            "MATCH (submission:Submission {tag : $tag}) "
            "MATCH (submission)-[:HAS_SAMPLE]->(s:Sample) "
            "MATCH (s)-[r:HAS_SAMPLE_ATTRIBUTE_VALUE]->(av:AttributeValue|Protein)<-[:HAS_VALUE]-(a:Attribute) "
            "RETURN s.index as sample_index, s.text as sample_text, av.tag as tag, r.index as attribute_index, a.tag as attribute_tag, av.text as text, 'Protein' in labels(av) as is_feature  " #g.tag as ag, g.tex as text, 
            "ORDER BY attribute_index, sample_index"
        )
        r = self._driver.execute_query(query, tag = tag, result_transformer_=Result.to_df)
        if as_sample_map:
            sample_map = r.pivot_table(index="sample_index",columns="attribute_tag",values="tag", aggfunc=lambda x: " ".join(x)) 
            #add sample index
            sample_name_to_index_mapper = dict([(sample_index,sample_text) for sample_text, sample_index in r[["sample_text","sample_index"]].drop_duplicates(subset=["sample_index"]).values])
            sample_index = sample_map.index.map(sample_name_to_index_mapper)
            sample_map.loc[:,"sample_text"] = sample_index.values
            
            return self._sample_attribute_to_dict(r), sample_map
       
        return self._sample_attribute_to_dict(r) 


    def create_title_search_index(self):
        query = (
            f"CREATE FULLTEXT INDEX  titleSearch IF NOT EXISTS FOR (d:Dataset) ON EACH [d.title] "
            "OPTIONS {"
            "indexConfig: {"
            "    `fulltext.analyzer`: 'english', "
            "    `fulltext.eventually_consistent`: true "
            "}"
            "}"    
        )
        
        with self._driver.session() as session:
            r = session.run(query) 
            
            
    def add_owner(self, tag : str, user_tag : str):
        ""
        query = (
            "MATCH (u:User) "
            "WHERE u.tag = $user_tag "
            "MATCH (submission:Submission) "
            "WHERE submission.tag = $tag "
            "MERGE (u)-[r:OWNS]-(submission) "
            "SET r.created_at = timestamp() "
        )
        
        self._driver.execute_query(query, user_tag = user_tag, tag = tag, routing_ = "w", database_ = "neo4j")


            
    def add_collaborators(self, tag : str, user_tags : List[str]):
        ""
        query = (
            "MATCH (u:User) "
            "WHERE u.tag in $user_tags "
            "MATCH (submission:Submission) "
            "WHERE submission.tag = $tag "
            "MERGE (u)-[r:IS_PART]-(submission) "
            "SET r.created_at = timestamp() "
            "WITH u,submission "
            "MATCH (owner:User)-[:OWNS]->(submission) "
            "MERGE (owner)-[:COLLABORATES_WITH]-(u) "
            "RETURN submission.tag"
        )
        
        r,_,_ = self._driver.execute_query(query, user_tags = user_tags, tag = tag, routing_ = "w", database_ = "neo4j")

    def get_owner(self, tag : str) -> UserModel:
        """Returns the owner (user) for a given dataset tag. 

        Parameters
        ----------
        tag : str
            _description_

        Returns
        -------
        UserModel
            The owner
            
        Raises
        ------
        ValueError if the user does not exists. 
        
        """
        query = (
            "MATCH (submission:Submission) "
            "WHERE submission.tag = $submission_tag "
            "MATCH (u:User)-[:OWNS]->(submission) "
            "RETURN properties(u)"
        )
        r = self._driver.execute_query(query, submission_tag = tag, routing_="r", result_transformer_=Result.value)
        if len(r) == 0: raise ValueError("User not found")
        return UserModel(**r[0])

    def get_users(self, tag : str) -> List[UserModel]:
        "Returns owners and collaborators."
        
        query = (
            "MATCH (submission:Submission) "
            "WHERE submission.tag = $submission_tag "
            "MATCH (u:User)-[:OWNS]->(submission) "
            "RETURN properties(u) "
            "UNION "
            "MATCH (u:User)-[:IS_PART]->(submission) "
            "RETURN properties(u) "
        )
        r = self._driver.execute_query(query, submission_tag = tag, routing_="r", result_transformer_=Result.value)
        return [UserModel(**u) for u in r]


    def update_dataset_attributes(self, tag : str, dataset_attributes : Dict[str,List[str]], dataset_attribute_input :  Dict[str,Dict[str,Dict[UnitsEnum,UnitTypeInputModel]]] = None) -> Dict:
        """_summary_

        Parameters
        ----------
        tag : str
            _description_
        dataset_attributes : Dict[str,List[str]]
            _description_
        dataset_attribute_input : Dict[str,Dict[str,Dict[UnitsEnum,UnitTypeInputModel]]], optional
            _description_, by default None

        Returns
        -------
        Dict[] key, 
            number_deleted_traits: int 
            deleted_trait_tags : List[str] trait_tag 
            number_added_traits: int 
            added_trait_tags: List[str] trait_tag 
        """
        attributes_and_values = [{'tag' : attribute_tag, 'value' : av_tag} for attribute_tag, av_tags in dataset_attributes.items() for av_tag in av_tags]
        trait_tags = [trait_tag for _, traits in dataset_attributes.items() for trait_tag in traits]
        #delete attributes that are not anymore part of the dataset attributes (e.g. deleted)
        query = (
             "MATCH (submission:Submission {tag: $tag}) "
             "OPTIONAL MATCH (submission)-[rvfa:HAS_VALUES_FOR_ATTRIBUTE]->(a:Attribute) "
             "WHERE NOT a.tag in $attribute_tags "
             "OPTIONAL MATCH (submission)-[rav:HAS_ATTRIBUTE_VALUE]->(av:AttributeValue) "
             "WHERE NOT av.tag in $trait_tags "
             "WITH rvfa, rav, count(rav) as number_deleted_traits, collect(av.tag) as deleted_trait_tags "
             "DELETE rvfa, rav "
             "RETURN number_deleted_traits, deleted_trait_tags"
        )
        
        r_deleted = self._driver.execute_query(query, tag = tag, attribute_tags = list(dataset_attributes.keys()), trait_tags = trait_tags, result_transformer_=Result.data)
        
        
        
        query = (
            "MATCH (submission:Submission {tag: $tag}) "
            "WITH submission, timestamp() as ts "
            #// Handle new attributes and their values
            "UNWIND $attributes AS a_with_value "
            #// Find matching Attribute and AttributeValue nodes
            "MATCH (a:Attribute {tag: a_with_value.tag}) "      
            "MATCH (av:AttributeValue {tag: a_with_value.value}) "
            #// Create new relationships between submission and attributes/values
            "MERGE (submission)-[r_hvfa:HAS_VALUES_FOR_ATTRIBUTE]->(a) "
            "MERGE (submission)-[r_hav:HAS_ATTRIBUTE_VALUE]->(av) "
            "ON CREATE SET r_hav.created_at = timestamp(), r_hav.attribute_tag = a.tag "
            #// Set property on the relationship
            "WITH ts, submission "
            "MATCH (submission)-[r:HAS_ATTRIBUTE_VALUE]->(av) "
            "WHERE r.created_at >= ts "  ##filter out the added traits 
            "RETURN count(DISTINCT r) as number_added_traits, collect(DISTINCT av.tag) as added_trait_tags, ts as timestamp "
        )
        r_created = self._driver.execute_query(query, tag = tag, attributes = attributes_and_values, routing_="w", result_transformer_=Result.data)
        
        
        if dataset_attribute_input is not None and len(dataset_attribute_input) > 0:
            dataset_attribute_values = [{"attribute_value_tag" : tag, #remove!! att_ is history 
                                     "attribute_tag" : attribute_tag, 
                                     "trait_value" : extract_user_input(dataset_attribute_input[attribute_tag][tag]) if attribute_tag in dataset_attribute_input and dataset_attribute_input[attribute_tag][tag] else []} 
                                    for attribute_tag, tags in dataset_attributes.items() for tag in tags]
        
            dataset_attributes_units = [x for x in dataset_attribute_values if isinstance(x["trait_value"],list) and len(x["trait_value"]) > 0]

            if len(dataset_attributes_units) > 0: 
                query = (
                    "MATCH (submission:Submission {tag : $submission_tag}) "
                    "UNWIND $dataset_attribute_values AS attribute_value "
                    "UNWIND attribute_value.trait_value AS trait "
                    "WITH attribute_value, trait "
                    "MATCH (av:AttributeValue {tag: attribute_value.attribute_value_tag}) "
                    "MATCH (unit:Unit {tag: trait.unit_tag}) "
                    "MERGE (av)-[r:HAS_VALUE_OF_UNIT]-(unit) "
                    "SET r.value = trait.value, r.submission_tag = $submission_tag, r.unittype_tag = trait.unittype_tag "
                    "RETURN av, unit, r "
                )
                r = self._driver.execute_query(query,routing_="w",submission_tag = tag, dataset_attribute_values = dataset_attributes_units, result_transformer_=Result.value)
                
        if len(r_created) == 0:
            r_created = [{"number_added_traits" : 0, "added_trait_tags" : []}]
            
        return {**r_created[0], **r_deleted[0]}        
         
        # query = (
        #     "MERGE (submission:Submission {tag : $submission_tag}) "
        #     "SET submission += $dataset_props "
        #     "WITH submission "
        #     "MATCH (state:State {tag : $state_tag}) "
        #     "MERGE (submission)-[r_in_state:IN_STATE]->(state) "
        #     "SET r_in_state.created_at = timestamp() "
        #     "WITH submission "
        #     "UNWIND $samples as sample_name "
        #     "MERGE (s:Sample {tag : sample_name.tag}) "
        #     "SET s += sample_name.props "
        #     "SET s.created_at = timestamp() "
        #     "WITH s, submission "
        #     "MERGE (s)<-[:HAS_SAMPLE]-(submission) "   
        #     "WITH submission "
        #     "UNWIND $dataset_attributes as attribute_tag "
        #     "MATCH (a:Attribute {tag : attribute_tag}) "
        #     "MERGE (submission)-[:HAS_VALUES_FOR_ATTRIBUTE]->(a) "
        #     "WITH submission "
        #     "UNWIND $dataset_attribute_values as attribute_value "
        #     "MATCH (av:AttributeValue {tag : attribute_value.attribute_value_tag}) "
        #     "MATCH (a:Attribute {tag : attribute_value.attribute_tag}) "
        #     "MERGE (submission)-[:HAS_ATTRIBUTE_VALUE]->(av) "
        #     "MERGE (av)-[:HAS_VALUE]-(a) "

        #     ""
        # )
    
        # self._driver.execute_query(query, routing_="w", 
        #                            samples = samples, 
        #                            submission_tag = submission_tag, 
        #                            dataset_attributes  = dataset_attributes, 
        #                            state_tag = submission.state, 
        #                            dataset_props = dataset_props, 
        #                            dataset_attribute_values = dataset_attribute_values)
        
        
        # #add units 
        # if len(dataset_attributes_units) > 0:
        


    def update_owner(self, tag: str, user_tag: str) -> bool:
       
        query = (
            "MATCH (submission:Submission {tag : $submission_tag}) "
            "MATCH (submission)<-[r:OWNS]-(u:User) "
            "DELETE r "
            "WITH submission "
            "MATCH (new_owner:User {tag : $user_tag}) "
            "MERGE (new_owner)-[r_new:OWNS]->(submission) "
            "SET r_new.created_at = timestamp() "
            "WITH new_owner, submission, r_new "
            "MATCH (submission)<-[:IS_PART]-(coll:User) "
            "MERGE (new_owner)-[:COLLABORATES_WITH]-(coll) "
            "RETURN count(r_new) as count"
        )
        
        r = self._driver.execute_query(query, submission_tag = tag, user_tag = user_tag, routing_="w", database_="neo4j", result_transformer_=Result.value)
        if r[0] == 1: return True
        return False 
