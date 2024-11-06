from typing import List, Dict, Tuple 
from neo4j import Driver, Result
import pandas as pd 

from lib.data.database.abstract.Meta import MetaABC

from lib.data.database.abstract.Attributes import AttributesABC
from config.settings.metatexts import MetaTexts
from config.models.submissions.submissions import MinimalMetadataModel, DatasetSubmissionModel
from config.models.user import UserModel 
from collections import OrderedDict

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
        
    def get_metatext(self, tags : List[str]) -> pd.DataFrame:
        ""
        query = (
            "MATCH (submission:Submission) "
            "WHERE submission.tag in $tags "
            "MATCH (submission)<-[:DESCRIBES]-(m:Metatext)-[:HAS_CONTENT]->(c:Content) "
            "WHERE c.submission_tag = submission.tag and c.content IS NOT null and c.content <> '' "
            "RETURN submission.tag as submission_tag, m.tag as tag, m.title as title, c.content as content ORDER BY m.priority DESC "
        )
        
        meta_text = self._driver.execute_query(query,tags=tags,result_transformer_=Result.to_df)
        return meta_text
    
    def add_metatext(self, tag : str, user_tag : str, meta_texts : Dict[str,str]):
        "" 
        metatext_settings = MetaTexts()
        meta_texts = [{"tag" : tag, "content" : content, "title" : metatext_settings.names[tag], "priority" : metatext_settings.priorities[tag]} for tag,content in meta_texts.items() if content != "" and tag in metatext_settings.names] 
        
        print(meta_texts)
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
    
    def add_samples_attributes(self, meta_data : DatasetSubmissionModel):
        """_summary_

        Parameters
        ----------
        meta_data : DatasetSubmissionModel, optional
            _description_, by default meta
        """
        sample_attributes_data = []
        attributes_to_connect = []
        
        for n, (attribute_tag, attribute_value) in enumerate(meta_data.samples_attributes.items()):
            attributes_to_connect.append({"attribute_tag" : attribute_tag, "values" : [], "inputs" : []})
            for attribute_value_tag, sample_idx in attribute_value.items():
                attr_value_tag = attribute_value_tag.split(":")[-1]
                attributes_to_connect[n]["values"].append(attr_value_tag)
                
                if meta_data.samples_attributes_input is not None and attribute_tag in meta_data.samples_attributes_input:
                    user_inputs  = meta_data.samples_attributes_input[attribute_tag]
                    attributes_to_connect[n]["inputs"] = [u.model_dump() for u in user_inputs]
    
                for idx in sample_idx:
                    sample_name = meta_data.sample_names[idx]
                    sample_attributes_data.append(
                        {
                            "attribute_tag" : attribute_tag,
                            "index" : n,
                            "sample_name" : sample_name, 
                            "attribute_value_tag" :  attr_value_tag##matching proteins by tag.
                        }
                    )
        print(attributes_to_connect,"ATTRS TO CONNECT")
        # print(sample_attributes_data)
        # print(attributes_to_connect)

        query = (
            "UNWIND $sample_attributes_data as sample_attr "
            "MATCH (s:Sample {tag : sample_attr.sample_name}) "
            "MATCH (av:AttributeValue {tag : sample_attr.attribute_value_tag}) "
            "MERGE (s)-[r_s:HAS_SAMPLE_ATTRIBUTE_VALUE]-(av) "
            "SET r_s += {index : sample_attr.index, attribute_tag : sample_attr.attribute_tag, created_at : timestamp()} "
            "WITH $dataset_tag as dataset_tag, $attributes as attributes "
            "MATCH (submission:Submission) "
            "WHERE submission.tag = dataset_tag "
            "UNWIND attributes as attr "
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
            "WITH attr, submission "
            "UNWIND attr.inputs as user_input "
            "MATCH (av_u:AttributeValue) "
            "WHERE av_u.tag = user_input.attribute_value_tag "
            "MATCH (submission)-[:HAS_SAMPLE]->(s:Sample {index : user_input.sample_index}) " #match the sample of the dataset 
            "MATCH (s)-[r_u_i:HAS_SAMPLE_ATTRIBUTE_VALUE]->(av_u) " #create a relationship
            "UNWIND user_input.input as i " #add the user input to the relationship
            "SET r_u_i += i "
            "RETURN r_u_i"
        )
                
        r,_,_ = self._driver.execute_query(query,
                                           dataset_tag=meta_data.tag, 
                                attributes = attributes_to_connect,
                                sample_attributes_data = sample_attributes_data,
                                database_="neo4j", 
                                routing_="w", 
                                   )
        print(r)
        #print(B)
        
    
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
        
        query = (
            "MATCH (submission:Submission {tag : $tag})-[:HAS_ATTRIBUTE_VALUE]->(av:AttributeValue)<-[:HAS_VALUE]-(a:Attribute) "
            "WHERE NOT EXISTS {(av)<-[:HAS_SAMPLE_ATTRIBUTE_VALUE]-(sample:Sample)<-[:HAS_SAMPLE]-(submission)} "
            "WITH a, av ORDER BY a.min_state ASC, a.priority DESC " 
            "RETURN a.tag, collect(av.tag) "
        )
        r = self._driver.execute_query(query_=query,tag=tag,result_transformer_=Result.values)
        return dict(r) 
        
    def get_sample_attributes_and_genotypes(self, tag:str, as_sample_map : bool = True) -> Tuple[Dict,pd.DataFrame]|Dict:
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
            "MATCH (d:Dataset {tag : $tag}) "
            "MATCH (d)-[:HAS_SAMPLE]->(s:Sample)-[r:HAS_SAMPLE_ATTRIBUTE_VALUE]->(av:AttributeValue|Protein)<-[:HAS_VALUE]-(a:Attribute) "
            "RETURN s.index as sample_index, s.text as sample_text, av.tag as attribute_value_tag, r.index as index, a.tag as attribute_tag, 'Protein' in labels(av) as is_feature "
            "ORDER BY r.index, s.index"
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


    def update_dataset_attributes(self, tag : str, dataset_attributes : Dict[str,List[str]]) -> bool:
        ""
        attributes_and_values = [{'tag' : attribute_tag, 'value' : av_tag} for attribute_tag, av_tags in dataset_attributes.items() for av_tag in av_tags]
        query = (
            "MATCH (submission:Submission {tag: $tag}) "
            #"// Find and delete existing relationships with attributes and values "
            "OPTIONAL MATCH (submission)-[rvfa:HAS_VALUES_FOR_ATTRIBUTE]->(a:Attribute) "       
            "OPTIONAL MATCH (submission)-[rav:HAS_ATTRIBUTE_VALUE]->(av:AttributeValue) "
            "DELETE rvfa, rav "
            #// Handle new attributes and their values
            "WITH submission "
            "UNWIND $attributes AS a_with_value "
            #// Find matching Attribute and AttributeValue nodes
            "MATCH (a:Attribute {tag: a_with_value.tag}) "      
            "MATCH (av:AttributeValue {tag: a_with_value.value}) "
            #// Create new relationships between submission and attributes/values
            "MERGE (submission)-[r_hvfa:HAS_VALUES_FOR_ATTRIBUTE]->(a) "
            "MERGE (submission)-[r_hav:HAS_ATTRIBUTE_VALUE]->(av) "
            #// Set property on the relationship
            "SET r_hav.attribute_tag = a.tag "
            "RETURN r_hav, count(r_hav) "
        )
        r = self._driver.execute_query(query, tag = tag, attributes = attributes_and_values, routing_="w", result_transformer_=Result.values)
        return True
        


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
