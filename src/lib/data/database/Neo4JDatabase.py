
from neo4j import GraphDatabase, Driver, Result
from neo4j.exceptions import ConstraintError
from lib.data.database.ABCDatabase import DatabaseABC, MetaABC, MCDatabase, MCAttributes
from typing import List, Tuple, Any, Dict, Literal, Optional
from collections import OrderedDict
from lib.data.database.neo4j.Users import Neo4JUser
from lib.data.database.neo4j.Meta import Neo4JMetaHandler
from lib.data.database.abstract.Features import FeaturesABC 

from config.enums.states import SubmissionStatesEnums
from config.enums.users.roles import UserRolesEnum
from config.settings.db import get_db_settings
from config.settings.proteomes.annotations import UniprotAnnotationSettings

from config.models.attributes import AttributeModel, AttributeValueModel
from config.models.feature import FeatureNeoModel
from config.models.submissions.submissions import DatasetSubmissionModel


from config.models.feature import FeatureNeoModel
from config.models.genotype import GenotypeModel, MinimalGenotypeModel
from config.models.searches import FulltextSearchResult
from config.models.filter import FilterModel


from lib.data.database.neo4j.Features import Neo4JFeatures

from services.json import read_json 
from services.annotations.uniprot import download_proteome_annotations
from services.encryption import create_password_hash
from pydantic import BaseModel, SecretStr, Field, field_serializer, field_validator, model_serializer
import inspect 
from enum import Enum
import time 
import pandas as pd 
import numpy as np 
from lib.user.UserHandling import UserDB
from random import randrange


from lib.data.utils.pearson import pearson
users_from_db = UserDB.get_users()
#print(users_from_db[0])


genotypes = []#[GenotypeModel(**x) for x  in read_json("/Users/hnolte/Documents/GitHub/mitocube-backend/resources/genotypes/genotypes.json")]
#print(genotypes)




class AttributeValuesBySubmissionModel(BaseModel):
    attribute_value : AttributeValueModel|FeatureNeoModel
    tags : List[str]
    count : int 

    
    
class UnitModel(BaseModel):
    tag : Literal["weight","concentration", "time","temperature","volume","masstocharge","voltage","flow","arbitrary"]
    unit : Literal["g","M","s","°C","L","m/z","V","L/min",""]
    text : str 
    
    
    
units = [UnitModel(tag = "weight", unit="g", text="Weight"),
         UnitModel(tag = "concentration", unit="M", text="Concentration"), 
         UnitModel(tag = "time", unit="s", text="Time"),
         UnitModel(tag = "temperature", unit="°C", text="Temperature"),
         UnitModel(tag = "masstocharge", unit="m/z", text="Mass to charge"),
         UnitModel(tag = "volume", unit="L", text="Volume"),
         UnitModel(tag = "voltage", unit="V", text="Volt"),
         UnitModel(tag = "flow", unit="L/min", text="Flow rate."),
         UnitModel(tag="arbitrary",unit="",text="Arbitrary")
         ]

class StateNode(BaseModel):
    ""
    tag : int # the name of the state 
    text : str # the enum state 

class UserRoleNode(BaseModel):
    tag : str 
    id : int 


class MatchIndexedNode(BaseModel):
    cypher_label : str = "n"
    label : str|List[str]
    index_value : str|int|float 
    index_prop : str 
    
    @field_validator("label", mode="before")
    def verify_node_label(value : str|List[str]):
        if isinstance(value,list):
            return f"{':'.join(value)}"
        else:
            return f"{value}"
    
    @model_serializer()
    def serialize_model(self):
        
        return f"MATCH ({self.cypher_label}:{self.label} {{{self.index_prop}:'{self.index_value}'}})"

class MergeIndexNode(MatchIndexedNode):
    
    @model_serializer()
    def serialize_model(self):
        
        return f"MERGE ({self.cypher_label}:{self.label} {{{self.index_prop}:'{self.index_value}'}})"




dataset_tag = "LOGtC9tNC13b" # "BuXOSlIl6G" # #   #"MpHCYf9mShVR" # #
m = read_json(f"/Users/hnolte/Documents/GitHub/mitocube-backend/resources/data/{dataset_tag}/params.json")
meta = DatasetSubmissionModel(**m, tag = m["label"])
d = pd.read_csv(f"/Users/hnolte/Documents/GitHub/mitocube-backend/resources/data/{dataset_tag}/data.txt", sep="\t").set_index("Key") #.sample(n=4000)
#print(meta)
#print(d)

def transform_query_result(result):
    "Transforms the result into a list of data."
    return result.data()[0]["query_result"]

class NodeLabelModel(BaseModel):
    cypher_label : str = "n"
    label : str|List[str]
    
    @field_validator("label", mode="before")
    def verify_node_label(value : str|List[str]):
        if isinstance(value,list):
            return ':'.join(value)
        else:
            return  value
        
    @model_serializer()
    def serialize_model(self):
        
        return f"{self.cypher_label}:{self.label}"
 
class RelationLabelModel(NodeLabelModel):
    ""

class ConstraintModel(BaseModel):
    constrain_label : str 
    node_label : NodeLabelModel 
    property_name : str|List[str]

constraints = [
    ConstraintModel(constrain_label  = "protein_tag", node_label = NodeLabelModel(label = "Protein"),property_name = ["tag","proteome_id"]),
    ConstraintModel(constrain_label  = "sample_tag", node_label = NodeLabelModel(label = "Sample"),property_name = "tag"),
    ConstraintModel(constrain_label  = "dataset_label",node_label = NodeLabelModel(label = "Dataset"),property_name ="tag"),
    ConstraintModel(constrain_label  = "submission_label",node_label = NodeLabelModel(label = "Submission"),property_name ="tag"),
    ConstraintModel(constrain_label  = "attribute_tag",node_label = NodeLabelModel(label = "Attribute"),property_name ="tag"),
    ConstraintModel(constrain_label  = "attribute_value_tag",node_label = NodeLabelModel(label = "AttributeValue"),property_name ="tag"),
    #ConstraintModel(constrain_label  = "attribute_proteome_value_tag",node_label = NodeLabelModel(label = ["AttributeValue","Proteome"]),property_name ="tag"),
    ConstraintModel(constrain_label  = "state_tag",node_label = NodeLabelModel(label = "State"),property_name ="tag"),
    ConstraintModel(constrain_label  = "user_tag",node_label = NodeLabelModel(label = "User"),property_name = ["tag","email"]),
    ConstraintModel(constrain_label  = "filter_tag",node_label = NodeLabelModel(label = "Filter"),property_name ="tag"),
    ConstraintModel(constrain_label  = "state_tag",node_label = NodeLabelModel(label = "State"),property_name ="tag"),
    ConstraintModel(constrain_label  = "user_role_tag",node_label = NodeLabelModel(label = "Role"),property_name ="tag"),
    ConstraintModel(constrain_label  = "query_tag",node_label = NodeLabelModel(label = "Query"),property_name ="tag"),
    ConstraintModel(constrain_label  = "metatext_tag",node_label = NodeLabelModel(label = "Metatext"),property_name ="tag"), #meta text? 
    ConstraintModel(constrain_label  = "unit_tag",node_label = NodeLabelModel(label = "Unit"),property_name ="tag")
]


#get log2 avg abundance ...
# MATCH (d:Dataset)-[r:QUANTIFIED_IN]-(p:Protei
# n)
# RETURN apoc.agg.percentiles(r.avg_log2_abundance,[0.5,0.75,1.0
# ])


DB_SETTINGS = get_db_settings()

attributes = read_json(DB_SETTINGS.attribute_file)


class DatasetNode(BaseModel):
    text : str = "sat123"
   #v label : str
    tag : str = "asr43342"
    #created_at : float = Field(...,default_factory=time.time)
    title : str = "The beatiful project I have"
    replicates : int = 5
    n_samples : int = 60 
    
    
class SampleNode(BaseModel):
    text : str
    tag : str = "asdadsasda"
    index : int 
    replicate : int 
    

    
    
    

attribute_models = [AttributeModel(**k, s = [k["text"],k["tag"],k["group_tag"]]) for k in attributes["attributes"]]
attribute_value_models = [AttributeValueModel(**k, s = [str(k["text"]),k["description"]]) for k in attributes["attribute_values"]]

#print(attribute_value_models)


#mitocarta3 = pd.read_csv("/Users/hnolte/Documents/GitHub/mitocube-backend/resources/filter/human_mitocarta/data.txt",sep="\t")
#print(mitocarta3)


def transform_model_to_cypher_string(baseModel : BaseModel) -> str:
    """Transforms a pydantic BaseModel into a Cypher property string"""
    node_props = baseModel.model_dump(exclude_none=True)
    stringFromDict = [f"{k} : '{v}'" for k,v in node_props.items() if isinstance(v,str)] + [f"{k} : '{v.get_secret_value()}'" for k,v in node_props.items() if isinstance(v,SecretStr)] +  [f"{k} : '{v.value}'" for k,v in node_props.items() if inspect.isclass(v) and issubclass(v,Enum)] +   [f"{k} : {v}" for k,v in node_props.items() if isinstance(v,int) or isinstance(v,float)] #[f"{k} : '{v.as_hex()}'" for k,v in node_props.items() if isinstance(v,Color)] +
    return "{" + f"{', '.join(stringFromDict)}"+"}"



class Neo4JConstructor:
    
    def __init__(self, driver : Driver) -> None:
        self._driver = driver 
        self.features = Neo4JFeatures(driver=driver)
        self.factory = Neo4JFactory(driver=driver)
        
        self._add_constraints()
        self._add_indices()
        self._add_states()
        self._add_unit(units=units)
        self._add_user_roles()   
        self._add_full_text_dataset_search()     
    
    def set_up_attributes(self):
        ""
        self._add_attributes_from_file()

        
    def _add_indices(self):
        
        self.factory.create_index("index_protein_proteome_id",NodeLabelModel(label="Protein"),["proteome_id"]) 
        self.factory.create_text_index("protein_s",NodeLabelModel(label = "Protein"),"s")
        self.factory.create_text_index("user_s",NodeLabelModel(label = "User"),"s")
        self.factory.create_text_index("genotype_s",NodeLabelModel(label = "Genotype"),"s")
        self.factory.create_text_index("protein_gene_search",NodeLabelModel(label = "Protein"),"gene_name")
        self.factory.create_text_index("protein_tag_search",NodeLabelModel(label = "Protein"),"tag")    
    
    def _add_constraints(self):
    
        for c in constraints:
            if isinstance(c.property_name,str):
                self.factory.create_unique_constraint(c.constrain_label,node_label=c.node_label,property_name=c.property_name)
                self.factory.create_index(f"index_{c.constrain_label}",c.node_label,[c.property_name])
            else:
                self.factory.create_unique_constraint(c.constrain_label,node_label=c.node_label,property_name=c.property_name[0])
                self.factory.create_index(f"index_{c.constrain_label}",c.node_label,c.property_name)
        
    def _add_attributes_from_file(self):
        
        attribute_df = pd.DataFrame().from_dict(attributes["attributes"])
        attribute_value_df = pd.DataFrame().from_dict([av.model_dump() for av in attribute_value_models])
        rels = []
        min_state_attributes = []
        for attribute_tag in attribute_df.loc[:,"tag"].unique():
            bool_match = attribute_value_df.loc[:,"attribute_tag"] == attribute_tag
            attribute_values = attribute_value_df.loc[bool_match,:]
            rels.extend([{"source": {"tag" : attribute_tag}, "target" : {"tag" : attr_value}} for attr_value in attribute_values.loc[:,"tag"]])
            min_state_attributes.append({"tag" : attribute_tag, "min_state" : attribute_df.loc[attribute_df.loc[:,"tag"] == attribute_tag]["min_state"].values[0]})

        self.factory.create_multiple_nodes(NodeLabelModel(label="AttributeValue"),nodes=attribute_value_models)
        self.factory.create_multiple_nodes(NodeLabelModel(label="Attribute"),nodes=attribute_models)
        self.factory.connect_two_nodes_by_tag(NodeLabelModel(label="Attribute",cypher_label="sn"), 
                                        NodeLabelModel(cypher_label="tn",label="AttributeValue"), relationship_label="HAS_VALUE", 
                                        properties=rels)
        
        
        ## connect states         
        query = (
            "UNWIND $props as prop "
            "MATCH (a:Attribute {tag : prop.tag}) "
            "MATCH (s:State {tag : prop.min_state}) " 
            "MERGE (a)-[:REQUIRES_STATE]->(s) "
        )
        print(min_state_attributes)
        self._driver.execute_query(query,props = min_state_attributes)
        
        
        ## add units 
        query = (
            "MATCH (a:Attribute) "
            "WHERE a.has_unit "
            "UNWIND a.unit as a_unit_tag "
            "MATCH (unit:Unit) "
            "WHERE unit.tag = a_unit_tag "
            "MERGE (a)-[:HAS_UNIT]->(unit) "
            "RETURN a, unit "
            )
        
        r,_,_ = self._driver.execute_query(query)
        print(r)
        
        
    def _add_full_text_dataset_search(self):
        
        query = (
            f"CREATE FULLTEXT INDEX datasetSearch IF NOT EXISTS FOR (q:Query) ON EACH [q.s, q.tag] "
            "OPTIONS {"
            "indexConfig: {"
            "    `fulltext.analyzer`: 'english'"
            "}"
            "}"    
        )
        
        self._driver.execute_query(query)
        
    # def _add_genotypes(self, genotypes : List[GenotypeModel], user_tag : str = None):
        
    #     def extract_genotype_attributes(genotype_attributes):
    #         ""
    #         gen_attrs = []
    #         n = 0
    #         for attribute in genotype_attributes:
    #             #there might be multiple protein mutations
    #             for idx in range(len(attribute["att_protein_mutation"])):
    #                 gen_attrs.append({})
    #                 mutation_tag = attribute["att_protein_mutation"][idx].tag
    #                 position_of_mutation = attribute["att_protein_position"][mutation_tag]
    #                 gen_attrs[n]["protein_tag"] = attribute["att_protein_coding_sequence"][0].key
    #                 gen_attrs[n]["engineering_tag"] = attribute["att_gene_engineering"][0].tag
    #                 gen_attrs[n]["method_tag"] = attribute["att_gene_editing_method"][0].tag
    #                 gen_attrs[n]["mutation_tag"] = mutation_tag
    #                 gen_attrs[n]["position_tag"] = position_of_mutation.attribute_value.tag
    #                 gen_attrs[n]["aa_position"] = position_of_mutation.aa_position
    #                 gen_attrs[n]["aa"] = position_of_mutation.aa
    #                 gen_attrs[n]["substitution"] = position_of_mutation.substitution
    #                 n += 1
    #         return gen_attrs
                
            
    #     genotype_props = [{"tag" : genotype.label, 
    #                        "proteome_id" : genotype.proteome_id, 
    #                        "text" : genotype.text, 
    #                        "attributes" : extract_genotype_attributes(genotype.attributes)} for genotype in genotypes if "att_protein_mutation" in genotype.attributes[0] and "att_protein_position" in genotype.attributes[0]]

    #     query = (
    #         "UNWIND $genotypes as genotype "
    #         "MERGE (g:Genotype {tag : genotype.tag}) "
    #         "ON CREATE "
    #         "SET g.created_at = timestamp(), g.text = genotype.text, g.proteome_id = genotype.proteome_id "
    #         "ON MATCH "
    #         "SET g.modified_at = timestamp(), g.text = genotype.text, g.proteome_id = genotype.proteome_id "
    #         "WITH g, genotype "
    #         "UNWIND genotype.attributes as attribute "
    #         "MATCH (p:Protein {tag : attribute.protein_tag}) "
    #         "SET g.s = toLower(genotype.text)+' '+p.s "
    #         "WITH g,p,genotype, attribute "
    #         "MERGE (g)-[effect_r:EFFECTS {tag : genotype.tag}]->(p) "
    #         "SET effect_r.created_at = timestamp() "
    #         "WITH attribute,p,genotype,g "
    #         "MATCH (engineer_attribute:AttributeValue {tag : attribute.engineering_tag}) "
    #         "MATCH (method_attribute:AttributeValue {tag : attribute.method_tag}) "
    #         "MATCH (prot_mutation_attribute:AttributeValue {tag : attribute.mutation_tag}) "
    #         "MATCH (position_attribute:AttributeValue {tag : attribute.position_tag}) "
    #         "MERGE (method_attribute)<-[:MEDIATED_BY {tag : genotype.tag}]-(engineer_attribute) "
    #         "MERGE (method_attribute)-[:MODIFYING {tag : genotype.tag}]-(p) "
    #         "MERGE (p)-[:INTRODUCING {tag : genotype.tag}]-(prot_mutation_attribute) "
    #         "MERGE (prot_mutation_attribute)-[at_r:AT {tag : genotype.tag}]->(position_attribute) "
    #         "SET at_r.position = attribute.aa_position, at_r.amino_acids = attribute.aa, at_r.substitution = attribute.substitution "
    #         )
        
    #     if user_tag is not None:
    #         query += ("WITH g "
    #                   "MATCH (u:User {tag : $user_tag}) "
    #                   "MERGE (u)-[r_defined:DEFINED {tag : g.tag}]->(g) "
    #                   "ON CREATE "
    #                   "SET r_defined.created_at = timestamp() "
    #         )
        
    #     self._driver.execute_query(query, genotypes = genotype_props, user_tag = user_tag, routing_="w",  database_="neo4j")
        
    def _add_states(self):
        ""
        self.factory.create_multiple_nodes(NodeLabelModel(label="State"),
                                           nodes=[StateNode(tag = state_data.value, text = state_data.name) for state_data in SubmissionStatesEnums])
    
    def _add_user_roles(self):
        "" 
        self.factory.create_multiple_nodes(NodeLabelModel(label="Role"),
                                           nodes=[UserRoleNode(tag = state_data.name, id = state_data.value) for state_data in UserRolesEnum])
        
        
    def _add_access_groups(self):
        "" 
        
        
        
    def _screen_pubmed_for_proteins(self):
        
        ## search for proteins 
        # find proteins that are mentioned together. 
        protein_list = ["Q9Y5T4","Q9Y4W6","Q9H3K2"]
        self.features.get_protein_by_tags(tags = protein_list) 
        
     #   "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=”OMA1”[Title/Abstract]%20AND%20depolarization[Title/Abstract]&sort=pub_date&retmode=JSON
    
        
    def _add_fulltext_dataset_search_nodes(self, dataset_tags : List[str] = None) -> int:
        """Combines information of a dataset into a combined string
        allowing for swift full text searches. 

        Returns
        -------
        int
            The number of created Query nodes.

        Raises
        ------
        ValueError
            _description_
        """
        if dataset_tags is not None and not isinstance(dataset_tags,list): raise ValueError("dataset_tags must a be a list of strings or None")
        if dataset_tags is not None:
            query = (
                "MATCH (d:Dataset)-[]->(a:Attribute) "
                "WHERE d.tag in $dataset_tags "
            )
        else:
            query = (
                "MATCH (d:Dataset)-[]->(a:Attribute) "
            )
        ## add the main query string to the start. 
        query += ("MATCH (d)-[]->(av:AttributeValue) "
            "WHERE NOT (av:Protein) "
            "MATCH (d)-[:HAS_ATTRIBUTE_VALUE]->(avp:Protein:AttributeValue) "
            "MATCH (d)-[]-(u:User) "
            "MATCH (d)<-[:DESCRIBES]-(:Metatext)-[:HAS_CONTENT]->(cont:Content) "
            "WITH apoc.text.join(collect(DISTINCT av.text),' ') as av_desc,  " #, apoc.text.join(collect(DISTINCT a.text),' ') as a_text
            "apoc.text.join(collect(cont.content),' ') as meta_text, "
            "apoc.text.join(apoc.coll.flatten(collect( DISTINCT [d.title, d.tag, u.research_group])),' ') as dataset_text, "
            "apoc.text.join(apoc.coll.flatten(collect( DISTINCT [u.firstname, u.lastname, u.research_group])),' ') as user_text, "
            "apoc.text.join(apoc.coll.flatten(collect( DISTINCT [avp.gene_names, avp.protein_name, avp.tag])),' ') as genes, d  "
            "MERGE (q:Query {tag : d.tag}) "
            "ON CREATE "
            "SET q.created_at = timestamp() "
            "ON MATCH "
            "SET q.modified_at = timestamp() "
            "SET q.s = apoc.text.join([dataset_text, meta_text, user_text, av_desc, genes], ' ') "
            "RETURN count(q) as count "
            )
        
        r,_,_ = self._driver.execute_query(query, dataset_tags = dataset_tags, routing_="w", database_="neo4j")
        
        
    def _add_unit(self, units : List[UnitModel]):
        
        query = (
            "UNWIND $units as unit_props "
            "MERGE (u:Unit {tag : unit_props.tag}) "
            "SET u.created_at = timestamp(), u.unit = unit_props.unit, u.text = unit_props.text "
            
        )
        
        self._driver.execute_query(query, units = [u.model_dump() for u in units])
        
class Neo4JConnection:
    """
    Handles the connection to the Neo4J database. 
    Never create multiple drivers for a database as it is very resource heavy. 
    Sessions on the other hand are very light. Please note that driver is thread-safe
    while session are not. 
    """
    
    def __init__(self):
       
        self.driver = GraphDatabase.driver(DB_SETTINGS.db_uri, 
                                           auth=(DB_SETTINGS.db_user, DB_SETTINGS.db_pw.get_secret_value() ), 
                                           max_connection_lifetime=400)
        self.driver.verify_connectivity()
        
    def close(self) -> None:
        """Closes the driver connection
        """
        self.driver.close()


class MCNeo4JDatabase(DatabaseABC):
    
    
    def __init__(self):
        
        self.connection = Neo4JConnection()
        self._driver = self.connection.driver
        self.factory = Neo4JFactory(driver=self.connection.driver)
        self.constructor = Neo4JConstructor(driver=self.connection.driver)
        self.attributes = Neo4JAttributes(driver=self.connection.driver)
        self.meta = Neo4JMetaHandler(driver=self.connection.driver, attributes=self.attributes)
        self.dataset_values = Neo4JDatasetHandler(driver=self.connection.driver, meta=self.meta)
        
        self.user = Neo4JUser(driver=self.connection.driver)
        self.features = Neo4JFeatures(driver=self.connection.driver)
        self.filters = Neo4JFilter(driver=self.connection.driver)
        self.calcs = Neo4JCalculations(driver=self.connection.driver, feature=self.features)
        self.submission_filter = Neo4JSubmissionFilter(driver=self.connection.driver)
        self.genotypes = Neo4JGenotype(driver=self.connection.driver)
        self.proteomes = Neo4JProteomes(driver = self.connection.driver)
        
        
        #checks if all is correctly defined 
        super(MCNeo4JDatabase, self).__init__()
        
        #self.proteomes.get()
        
        #self.constructor._add_states()
        #self.constructor._add_user_roles()
        self.constructor.set_up_attributes()
        
        print(self.attributes.unit(tags = ["att_compound"]))
       
        self.constructor._screen_pubmed_for_proteins()
        self.constructor._add_genotypes(genotypes=genotypes)
        self.constructor._add_fulltext_dataset_search_nodes()
        print(self.submission_filter.get_counts())
       # self.update_state('Q7JgoEYTqy',5,"123asd")
       # self.factory.create_text_index("dataset_searcg",NodeLabelModel(label = "Query"),"s")
        #rr = self.attributes.get_attribute_values_by_attribute_tag()
        self.user.add_users(users_from_db)
        self.insert_meta(meta)
        self.meta.get_metatext(tags=[meta.tag])
       # self.dataset_values.get_abundance_distribution()
       # self.dataset_values.get_abundance_distribution(filter_tag="MitoCarta 3.0")
        
        self.submission_filter.full_dataset_text_search("LOGtC9tNC13b DNAJC15 Timm Mitochondrial proteases GHITM TMBIM5")
        # self.submission_filter.get_submissions(protein_tag=APIParamString(param="Q86X40"))
        
        
       # self.attributes.get_attributes_and_values_by_search_string("DIA")
       
        #self.attributes.get_attribute_values_by_dataset_tags(["LOGtC9tNC13b", "MpHCYf9mShVR", "BuXOSlIl6G"])
        
        # self.filters.add_filter(protein_tags=mitocarta3.loc[:,"UniProt"].to_list(), 
        #                         proteome_id="UP000005640", 
        #                         filter_tag="MitoCarta 3.0 (H)", 
        #                         description="Collection of mitochondrial proteins based on the results of APEX based proximity labeling in 14 mouse tissues.")
        
        #print("====")
       # print(B)
        #print(self.attributes.get_attributes_by_state(2))
        #print(rr, "AV !!")
        #print(self.dataset_values.get_dataset_node(tag="LOGtC9tNC13b"))
        #print("dataset node")
       # print(self.filters.get_filters("UP000005640"))

        # The above code snippet is calling a method `create_text_index` on an object `factory` to
        # create a text index. The actual implementation of the `create_text_index` method and the
        # `factory` object is not shown in the provided code snippet.

        #self.factory.create_text_index("protein_proteome_id_search",NodeLabelModel(label = "Protein"),"proteome_id")
        #self.features.get_protein_sequence(tags = ["Q12849","Q8TCS8"])
        #s = self.calcs.correlate_features()
        #print(B)
        
        
        
        # us = self.user.get_users()
        # u = self.user.get_user_by_email("nolte@instantclue.de")
        # self.user.block_user_by_tag(tag = "nqVQzDvn")
        # print(u,"USER BY MAIL")
        ##self.count(node_label="User")
        #self.count(node_label="Dataset")
        
        # self.factory.get_counts_by_tag(source_node_label=NodeLabelModel(cypher_label="sn",label="Dataset"), 
        #                                target_node_label=NodeLabelModel(cypher_label="tn", label = "AttributeValue"))
        #quant = self.dataset_values.is_quantified(tag=dataset_tag,feature_node_label=NodeLabelModel(cypher_label="p",label="Protein"),keys=["P15924","Q15014"])
 
        

    
    #FIND PROTEINS QUANTIFIED IN ALL TAGS
    # MATCH (p:Protein)
    # WHERE
    # ALL(tag IN ["BuXOSlIl6G","LOGtC9tNC13b"] WHERE EXISTS {
    # (p)-[:QUANTIFIED_IN]->(d:Dataset {tag : tag})}
    # ) 
    # return count(p) as count
        
        
        self.get_protein_data(tag = 'Q86YN6',dataset_tags=[dataset_tag])
        
        print("====")
        print(self.meta.get_users(dataset_tag=meta.label))
        print("USERS")
        #print(B)
        #self.insert_meta()
        #self.insert_dataset(data_table=d, tag=dataset_tag)
       #ta(tag=dataset_tag)
        #print(B)
       # self.get_datatable()
        # self.connection.close()
        
        
        
        #self.factory.insert_nodes_from_csv("https://raw.githubusercontent.com/hnolCol/mitocube/master/neotetst.csv")

    def get_dataset_table(self, tag : str, filter_tag : str = None) -> pd.DataFrame:
        ""
        values = self.dataset_values.get_datatable(tag,filter_tag)
        return values 
        
    def get_dataset_tags(self) -> List[str]:
        """Returns all dataset tags in the database.

        Returns
        -------
        List[str]
            List of dataset tags in the database. 
        """
        query = (
            "MATCH (d:Dataset) "
            "RETURN DISTINCT d.tag as tags "
        )
        
        r = self._driver.execute_query(query, routing_="r", database_="neo4j", result_transformer_=Result.value)
       # dataset_tags = self.factory.get_nodes_tag_by_label(node_label=NodeLabelModel(cypher_label="d", label = "Dataset"))
        return r
        
        
    def get_submission_count(self) -> int:
        ""
        r = self.factory.count_nodes_by_label(NodeLabelModel(label="Dataset"))
        return r 
        
        
    def count(self, node_label : str|List[str]) -> int:
        """Returns the number nodes of node_label. 

        Parameters
        ----------
        node_label : str | List[str]
            Node label in the graph database. If multiple labels are provided for a node, 
            then a list of strings should be provided.

        Returns
        -------
        int
            _description_
        """
        
        r = self.factory.count_nodes_by_label(NodeLabelModel(label=node_label))
        #print(r,"COUNT")
        
    def get_protein_data(self, tag : str, dataset_tags : List[str] = None):

        query = ("MATCH (p:Protein {tag : $tag}) "
                 "SET p.viewed = 1 + p.viewed "
                 "WITH p "
                 "MATCH (p)-[quant:QUANTIFIED_IN]->(d:Dataset) ")
        if dataset_tags is not None:
            query += "WHERE d.tag in $dataset_tags "

        query += (
            "WITH apoc.coll.zip(quant.qs, quant.sample_index) as sample_quants "
            "UNWIND sample_quants as qidx "
            "MATCH (d)-[:HAS_SAMPLE]->(s:Sample)-[r:HAS_SAMPLE_ATTRIBUTE_VALUE|HAS_GENOTYPE]-(n:AttributeValue|Genotype)"
            "WHERE s.index = qidx[1] "
            "RETURN d.tag as dataset_tag , collect([r.attribute_tag, n.tag]) as sample_attributes, s.index as sample_index, "
            "s.text as sample_name, qidx[0] as value "
        )
       
        
        r = self._driver.execute_query(query,routing_="w",tag=tag, dataset_tags = dataset_tags, result_transformer_=Result.to_df)
        
        
        a = [{"index" : idx} for idx in r.index]
        for idx,sas in enumerate(r["sample_attributes"].values):
            sas.sort(key = lambda x : x[1])
            for attribute_tag, attribute_value_tag in sas:
                if attribute_tag not in a[idx]:
                    a[idx][attribute_tag] = attribute_value_tag
                else:
                    a[idx][attribute_tag] += " " + attribute_value_tag
        r = r.join(pd.DataFrame(a).set_index("index"))
        print(r)
        return r
       # rr = [{attribute_tag : attribute_value_tag for attribute_tag, attribute_value_tag in l} for l in r["sample_attributes"].values ]
        
       # print(pd.DataFrame().from_dict(rr)) 
        
    def get_meta_data(self, tag : str) -> DatasetSubmissionModel:
        
        
       # self.dataset_values.get
        #DatasetSubmissionModel(tag=tag)
        
        a = self.meta.get_sample_attributes(tag)
        self.meta.get_sample_genotypes(tag)
        self.meta.get_sample_attributes_and_genotypes(tag)
        
        
    def insert_meta(self, meta_data : DatasetSubmissionModel):
        ""
        dataset_tag = meta_data.tag
        sample_names = meta_data.sample_names
        #dataset_node_label = DatasetNode(label = dataset_tag, tag = dataset_tag, title=meta_data.title, n_samples=meta_data.n_samples, created_at=meta_data.created_on)
        #dataset_index_node = MatchIndexedNode(label="Dataset",index_prop="tag", index_value=dataset_tag, cypher_label="sn")
        #self.factory.create_multiple_nodes(NodeLabelModel(label="Dataset"),nodes=[dataset_node_label])
        dataset_props = {"title" : meta_data.title, "n_samples" : meta_data.n_samples, "created_at" : meta_data.created_on, "state" : meta_data.state, "n_replicates" : len(set(meta_data.replicates))}
        #get the state tag 
        #state_tag =  SubmissionStatesEnums(meta_data.state).name
        
        samples = [{"tag" : sample_name, "props" : {"index" : idx, "replicate" : meta_data.replicates[idx], "text" : sample_name}} for idx,sample_name in enumerate(sample_names)]
        dataset_attributes =  [tag for tag in meta_data.dataset_attributes.keys()]
        dataset_attribute_values = [{"attribute_value_tag" : tag.split(":")[-1], "attribute_tag" : attribute_tag} 
                                    for attribute_tag,tags in meta_data.dataset_attributes.items() for tag in tags]

        query = (
            "MERGE (d:Dataset {tag : $dataset_tag}) "
            "SET d += $dataset_props "
            "WITH d "
            "MATCH (state:State {tag : $state_tag}) "
            "MERGE (d)-[r_in_state:IN_STATE]->(state) "
            "SET r_in_state.created_at = timestamp() "
            "WITH d "
            "UNWIND $samples as sample_name "
            "MERGE (s:Sample {tag : sample_name.tag}) "
            "SET s += sample_name.props "
            "SET s.created_at = timestamp() "
            "WITH s, d "
            "MERGE (s)<-[:HAS_SAMPLE]-(d) "   
            "WITH d "
            "UNWIND $dataset_attributes as attribute_tag "
            "MATCH (a:Attribute {tag : attribute_tag}) "
            "MERGE (d)-[:HAS_VALUES_FOR_ATTRIBUTE]->(a) "
            "WITH d "
            "UNWIND $dataset_attribute_values as attribute_value "
            "MATCH (av:AttributeValue {tag : attribute_value.attribute_value_tag}) "
            "MATCH (a:Attribute {tag : attribute_value.attribute_tag}) "
            "MERGE (d)-[:HAS_ATTRIBUTE_VALUE]->(av) "
            "MERGE (av)-[:HAS_VALUE]-(a) "  
        )
        
        
        
        self._driver.execute_query(query, routing_="w", 
                                   samples = samples, 
                                   dataset_tag = dataset_tag, 
                                   dataset_attributes  = dataset_attributes, 
                                   state_tag = meta_data.state, 
                                   dataset_props = dataset_props, 
                                   dataset_attribute_values = dataset_attribute_values)
        
        ## add samples 
        # samples = [SampleNode(text=sample_name, tag = sample_name, index=idx, replicate = meta.replicates[idx]) for idx,sample_name in enumerate(sample_names)]
        # self.factory.create_multiple_nodes(NodeLabelModel(label="Sample"),nodes=samples)
        
        #metatext -> write in relationship: user, created_at, modified_at, mod
       # meta_texts = [meta_data.metatext]
    
        self.meta.add_metatext(dataset_tag=dataset_tag, user_tag = meta_data.user_tag, meta_texts=meta_data.metatext)
        ##connect samples to dataset
        
        self.meta.add_samples_attributes(meta_data=meta_data)
        self.meta.add_samples_genotypes(meta_data=meta_data)
        
        self.meta.add_owner(user_tag=meta_data.user_tag,dataset_tag=meta_data.label)
        self.meta.add_collaborators(user_tags=meta_data.collaborators, dataset_tag=meta_data.label)
        
        
        # for rr in r:
        #     print(rr.data())
        # rels = [{
        #     "source" : IndexedNode(cypher_label="sn",label="Dataset",index_prop="label",index_value="asd1324sdd"),
        #     "target" : IndexedNode(cypher_label="tn",label="Attribute",index_prop="tag",index_value="att_column_length"),
        #     "rel_label" : "HAS_ATTRIBUTE_VALUE"
        # }]
        
        # self.factory.connect_multiple_nodes(rels)
        dataset_attributes = []
        
    def insert_dataset(self, data_table : pd.DataFrame, tag : str):
        """Insert a database based on a pandas data frame. 
        """
        #self.dataset_values.add_datatable(data_table)
        
        self.dataset_values.add_datatable(data_table,tag)
        
    
    def dataset_exists(self, tag : str) -> bool:
        ""
        query = (
            "WITH EXISTS {(d:Dataset {tag : $tag})} as dataset_exists "
            "RETURN dataset_exists "
        )    
        r = self._driver.execute_query(query, tag = tag, result_transformer_=Result.value)
        return r[0]
    
    def dataset_has_data(self, tag: str) -> bool:
        
        query = (
            "WITH EXISTS {(d:Dataset {tag : $tag})} as dataset_exists "
            "WITH EXISTS {(d)<-[:QUANTIFIED_IN]-(:Protein)} as quant_values_exist, dataset_exists "
            "RETURN dataset_exists AND quant_values_exist "
        )
        r = self._driver.execute_query(query, tag = tag, result_transformer_=Result.value)
        return r[0]
    
    def update_state(self, dataset_tag : str, new_state : int, user_tag : str):
        ""
        if new_state not in set(SubmissionStatesEnums):
            raise ValueError("new_state not a valid state.")
        #state_tag =  SubmissionStatesEnums(new_state).name
        
        query = (
            "MATCH (d:Dataset {tag : $dataset_tag}) "
            "MATCH (d)-[r:IN_STATE]-(s:State) "
            "CREATE (d)-[r_old:HAD_STATE]->(s) "
            "DELETE r "
            "WITH d, r_old "
            "MATCH (new_state:State {tag : $state_tag}) "
            "CREATE (d)-[r_new:IN_STATE]->(new_state) "
            "SET r_old.created_at = timestamp(), r_old.user_tag = $user_tag "
            "SET r_new.created_at = timestamp(), r_new.user_tag = $user_tag "
        )
        
        r,_,_ = self._driver.execute_query(query,dataset_tag=dataset_tag, state_tag = new_state, user_tag = user_tag)


        
        
        
        
        

        



#  query : Annotated[str | None, Query(min_length=1)] = None,
#                             feature_key : str = None, 
#                             attribute_value_tag : str = None, 
#                             attribute_tag : str = None, 
#                             genotype_label : str = None, 
#                             user_label : str = None,
#                             max_submissions : int = 50, 


class Neo4JDatasetHandler:
    
    def __init__(self, driver : Driver, meta : Neo4JMetaHandler) -> None:
        
        self._driver = driver
        self.meta = meta 
        self.factory = Neo4JFactory(driver)
    
    def _get_variance_in_groups(self, tag : str, data_table : pd.DataFrame)-> Tuple[pd.DataFrame,pd.DataFrame]:
        ""
        total_variance = data_table.var(axis=1)
        sample_attributes = self.meta.get_sample_attributes_and_genotypes(tag)
        variances = pd.DataFrame(index = data_table.index)
        for group, group_data in sample_attributes.groupby(by=["attribute_tag","tag"]):
            sample_names = group_data["sample_text"].values
            print(sample_names)
            group_var = data_table.loc[:,sample_names].var(axis=1)
            variances.loc[:,"__".join(group)] = group_var
        scaled_variances = variances.divide(total_variance, axis = 0)
        scaled_max_var_group = scaled_variances.idxmax(axis=1)
        scaled_max_variance = scaled_variances.max(axis=1)
        return scaled_max_variance, scaled_max_var_group
    
    def add_datatable_test(self, data_table : pd.DataFrame, tag : str):
        ""
        scaled_variance, max_var_group = self._get_variance_in_groups(tag, data_table)
        data_table = data_table.dropna(how="all")
        data_table.columns = np.arange(data_table.columns.size) #TODO Change here to match the exact index (From meta?) 
        is_nan = np.isnan(data_table).values
        tags = data_table.index.values 
        values = data_table.values
        mean_values = data_table.mean(axis=1)
        data_table.columns = range(data_table.columns.size) 
        # data_table.loc[:,"mean"] = data_table.mean(axis=1)
        # data_table.loc[:,"var"] = scaled_variance.values 
        print(data_table)
        
        prop = [{"sample_index" : columnName, 
                 "protein_tags" : data_table.dropna(subset=columnName).index.values.tolist(),
                 "values" : data_table.dropna(subset=columnName).loc[:,columnName].values.tolist(),
                 } for columnName in data_table.columns]
        #print(prop)
       # melted = data_table.melt(var_name="sample_index",ignore_index=False).dropna(subset="value")
       # print(melted)
        #print(melted.reset_index())
       # print(B)
        # props = [{"tag" : tag, 
        #           "mean_q" : mean_values.loc[tag],
        #           "var" : scaled_variance.loc[tag],
        #           "var_attr" : max_var_group.loc[tag],
        #           "qs" : [v for m,v in enumerate(values [n,:]) if not is_nan[n,m]],
        #           "sample_index" : [data_table.columns[idx] for idx in range(data_table.columns.size) if not is_nan[n,idx]]
        #           } for n,tag in enumerate(tags)]
        
        
        # query = (
        #     "MATCH (d:Dataset {tag : $tag}) "
        #     "UNWIND $prop as prop "
        #     "MATCH (s:Sample {index : prop.sample_index}) "
        #     "UNWIND apoc.coll.zip(prop.protein_tags,prop.values) as protein_value "
        #     "MATCH (p:Protein {tag : protein_value[0]}) "
        #     "MERGE (s)-[r:QUANTIFIED]->(p) "
        #     "SET r.value = protein_value[1] "
        #     "RETURN protein_value"
        # )
        # print("adding dataset")
        # r, _, _ = self._driver.execute_query(query, routing_="w", tag = tag, prop = prop)
        # print(r)
        
        t1 = time.time()
        
        print("STARTING TO GET DATA")
        query = ("MATCH (p:Protein)<-[r:QUANTIFIED]-(s:Sample)-[:HAS_SAMPLE_ATTRIBUTE_VALUE|HAS_GENOTYPE]->(n:AttributeValue|Genotype) "
                "RETURN r.value")
        r, _, _ = self._driver.execute_query(query, routing_="r")
        
        t1 = time.time() 
        self.get_datatable(tag)
        print("took only", time.time()-t1)
        
    def add_datatable(self, data_table : pd.DataFrame, tag : str):
        ""
        scaled_variance, max_var_group = self._get_variance_in_groups(tag, data_table)
        with self._driver.session() as session:
            session.execute_write(self._add_dt, data_table, tag, scaled_variance, max_var_group)
            
    @staticmethod
    def _add_dt(tx, data_table: pd.DataFrame, tag  : str, scaled_variance : pd.DataFrame, max_var_group : pd.DataFrame):
        data_table = data_table.dropna(how="all")
        data_table.columns = np.arange(data_table.columns.size) #TODO Change here to match the exact index (From meta?) 
        is_nan = np.isnan(data_table).values
        tags = data_table.index.values 
        values = data_table.values
        mean_values = data_table.mean(axis=1)
        
        
        props = [{"tag" : tag, 
                  "mean_q" : mean_values.loc[tag],
                  "var" : scaled_variance.loc[tag],
                  "var_attr" : max_var_group.loc[tag],
                  "qs" : [v for m,v in enumerate(values [n,:]) if not is_nan[n,m]],
                  "sample_index" : [data_table.columns[idx] for idx in range(data_table.columns.size) if not is_nan[n,idx]]
                  } for n,tag in enumerate(tags)]
        
        
        query = (
            "MATCH (d:Dataset {tag : $tag}) "
            "UNWIND $props as prop "
            "MATCH (p:Protein {tag: prop.tag}) "
            "MERGE (p)-[r:QUANTIFIED_IN]->(d) "
            "SET r += {qs : prop.qs, sample_index : prop.sample_index, created_at : timestamp(), avg_log2_abundance : prop.mean_q, variance : prop.var, max_variance_attribute : prop.var_attr} "
            #"SET r.points = [p IN prop.points | point({x: p.x, y : p.y})] "
            "RETURN count(r) as count " 
        )
        
        r = tx.run(query, props = props, tag = tag)
        print("dataset added.")
    
    def add_datatable3(self, data_table : pd.DataFrame, main_chunk_size = 2000):
        ""
        data_table_melt = data_table.reset_index().melt(id_vars="Key").dropna(subset=["value"])
        #data_table_chunks = np.array_split(data_table_melt, data_table_melt.index.size / main_chunk_size)
        print("adding datatable with sample relations")
       
        with self._driver.session() as session:
            session.execute_write(self._add_q_values, data_table = data_table_melt)
       
    @staticmethod
    def _add_q_values(tx, data_table : pd.DataFrame, chunk_size : int = 10000, relation_label : str = "QUANTIFIED"):
        ""
        chunks = np.array_split(data_table, data_table.index.size / chunk_size)
        for c in chunks:
            if c.index.size == 0: continue
            query = (
                f"UNWIND $props AS prop "
                "MATCH (s:Sample {tag : prop.variable}) "
                "MATCH (p:Protein {tag: prop.Key}) " #this should be match instead of merge! -> if dataset created before.
                "WITH s, p, prop "
                f"MERGE (s)-[r:{relation_label}]->(p) "
                "SET r.value = prop.value, r.tag =  "
                "RETURN s, p"
            )
            r = tx.run(query, props = c.to_dict(orient="records"))
           
            
    def tag_exists(self, tag : str) -> bool:
        ""    
        node = self.factory.find_node(MatchIndexedNode(label="Dataset",index_prop="tag", index_value=tag))
        return len(node) > 0
    
    
    def get_abundance_distribution(self, tags : List[str] = None, filter_tag : str = None, quantiles : List[float] = [0.25,0.5,0.75]):
        ""
        if tags is None and filter_tag is None:
            query = (
                "MATCH (d:Dataset)-[r:QUANTIFIED_IN]-(p:Protein) "
            )
        elif tags is None and filter_tag is not None:
            ##filter tag exists 
            query = (
                "MATCH (d:Dataset)-[r:QUANTIFIED_IN]-(p:Protein)-[:PART_OF]->(f:Filter) "
                "WHERE f.tag = $filter_tag "
            )
        elif tags is not None and filter_tag is None:
            query = (
                "MATCH (d:Dataset)-[r:QUANTIFIED_IN]-(p:Protein) "
                "WHERE d.tag in $tags "
            )
        elif filter_tag is not None and tags is None:
            query = (
                "MATCH (d:Dataset)-[r:QUANTIFIED_IN]-(p:Protein)-[:PART_OF]->(f:Filter) "
                "WHERE f.tag = $filter_tag "
            )
        query += "RETURN apoc.agg.percentiles(r.avg_log2_abundance, $quantiles) as quantiles"
        r,_,_ = self._driver.execute_query(query, tags=tags, filter_tag = filter_tag, quantiles = quantiles)
        print(r,"ABUNDANCE")
        
    
    def get_dataset_node(self, tag: str) -> Dict:
        "Returns the dataset node properties by the tag." 
        query = (
            "MATCH (d:Dataset {tag : $tag}) "
            "RETURN properties(d) as query_result"
        )

        r = self._driver.execute_query(query, tag = tag, 
                                    result_transformer_=transform_query_result, 
                                    database_="neo4j", 
                                    routing_="r")
        return r
        
        
    
    def get_datatable(self, tag : str, filter_tag : str = None) -> pd.DataFrame:
        ""
        query = (
            "MATCH (d:Dataset {tag : $tag}) "
        )
        if filter_tag is not None:
            query += (
                "MATCH (f:Filter) "
                "WHERE f.tag = $filter_tag "
                "MATCH (d)<-[r:QUANTIFIED_IN]-(p:Protein)-[:PART_OF]->(f)"
                )
        else:
            query += (
                "MATCH (d)<-[r:QUANTIFIED_IN]-(p:Protein) "
                )
        query += "RETURN r.qs AS qs, r.sample_index AS idx, p.tag AS tag"
        
        datatable_long = self._driver.execute_query(query, routing_="r",tag = tag, filter_tag = filter_tag, result_transformer_=Result.to_df)
        
        return datatable_long.explode(["qs","idx"]).pivot(index="tag",columns="idx",values="qs").astype(float)
        
    #     index_dataset_node = MatchIndexedNode(cypher_label="d",label="Dataset",index_value=tag,index_prop="tag")
    #     with self._driver.session() as session:
    #         datatable =  session.execute_read(self._get_values,index_dataset_node)
    #        # print(datatable.explode(["qs","idx"]))
    #         r = 2
    #         print(r)
    #         return r
        
            
    # @staticmethod
    # def _get_values(tx, dataset_node : MatchIndexedNode):
                
    #     query = (
    #         f"{dataset_node.model_dump()} "
    #         "MATCH (d)<-[r:QUANTIFIED_IN]-(n:Protein) "
    #         "RETURN r.qs AS qs, r.sample_index AS idx, n.tag AS tag"
    #     )
       
        
    #     t1 = time.time()
    #     r = tx.run(query)
    #    # rr = list(r)        
    #     d1 = r.to_df().explode(["qs","idx"])
    #     print(time.time()-t1,"FIRST")
        
    #     # t1 = time.time()
    #     # r = tx.run(query2)
    #     # d2 = r.to_df()
    #     # print(time.time()-t1,"SECODND")
        
    #     # print("===")
        
    #     # print(d1,d2)
    #    # print(d2)
    #     return d1
    
    
    def is_quantified(self, tag : str, feature_node_label : NodeLabelModel, keys : List[str] = ['Q8ZddASD']):
        ""
        
        
        
        index_dataset_node = MatchIndexedNode(cypher_label="d",label="Dataset",index_value=tag,index_prop="tag")
        with self._driver.session() as session:
            return session.execute_read(self._is_q,index_dataset_node, feature_node_label, keys)
    
    @staticmethod
    def _is_q(tx, dataset_node : MatchIndexedNode, feature_node_label : NodeLabelModel, keys : List[str]):
        
        query = (
            "UNWIND $keys AS tag "
            f"{dataset_node.model_dump()} "
            "RETURN tag, EXISTS {"
            f"    ({dataset_node.cypher_label})<-[:QUANTIFIED_IN]->({feature_node_label.model_dump()} {{tag : tag}}) "
            "} AS is_quantified"
            )
        r = tx.run(query, keys=keys)
        return r.to_df()

    def is_quantified_in(self, feature_node_label : NodeLabelModel, keys : List[str] = ['P15924']):
        ""
        with self._driver.session() as session:
            return session.execute_read(self._is_q, feature_node_label, keys)
    
    @staticmethod
    def _is_q_in(tx, dataset_node : MatchIndexedNode, feature_node_label : NodeLabelModel, keys : List[str]):
        ""
      

class Neo4JFactory:
    
    def __init__(self, driver : Driver) -> None:
        
        self._driver = driver 
        
    def create_unique_constraint(self, constraint_name : str, node_label : NodeLabelModel, property_name : str):
        ""
        with self._driver.session() as session:
            session.execute_write(self._add_unique_constraint,constraint_name,node_label.model_dump(),property_name)
    
    @staticmethod
    def _add_unique_constraint(tx, constraint_name : str, node_label : str, property_name):
        """
        """
        query = (
            f"CREATE CONSTRAINT {constraint_name} IF NOT EXISTS "
            f"FOR ({node_label}) "
            f"REQUIRE n.{property_name} IS UNIQUE"
        )
        r = tx.run(query)
    
    def create_index(self, index_name : str, node_label : NodeLabelModel, properties : List[str]):
        
        with self._driver.session() as session:
            session.execute_write(self._add_index,index_name,node_label.model_dump(), properties)
    
    @staticmethod
    def _add_index(tx,index_name : str,node_label : str, properties : List[str]):
        """
        """
        query = (
            f"CREATE INDEX {index_name} IF NOT EXISTS "
            f"FOR ({node_label}) "
            f"ON ({', '.join('n.'+prop for prop in properties)})"
        )
        r = tx.run(query)
        
    def create_text_index(self, index_name : str, node_label : NodeLabelModel, property : str):
        with self._driver.session() as session:
            session.execute_write(self._add_text_index,index_name,node_label, property)
            
    @staticmethod
    def _add_text_index(tx,index_name : str, node_label : NodeLabelModel, property : str):
        query = (
            f"CREATE TEXT INDEX {index_name} IF NOT EXISTS "
            f"FOR ({node_label.model_dump()}) "
            f"ON ({node_label.cypher_label}.{property})"
        )
        r = tx.run(query)
    #CREATE TEXT INDEX text_index_name FOR (n:PointOfInterest) ON (n.name)
        
    def create_multiple_nodes(self, node_label : NodeLabelModel, nodes = list[BaseModel]):
        ""
        with self._driver.session() as session:
            result = session.execute_write(self._create_nodes_from_list,node_label, nodes)
            

    @staticmethod
    def _create_nodes_from_list(tx,node_label : NodeLabelModel, nodes : list[BaseModel]):
        "Careful this overwrites a given node with the same name and sets the current props."
        #assumes that all types are the same 
        # if not all(isinstance(node,nodes[0]) for node in nodes):
        #     raise TypeError("All nodes must be the same instance.")
        
        property_keys = [k for k in nodes[0].model_dump(by_alias=True, exclude_none=False).keys() if k != "tag"]
        a = '{tag : prop.tag}'
        # if not "name" in property_keys:
        #     raise ValueError("The node must contain the property name."){{name: prop.name}})
        query = (
            f"UNWIND $props AS prop "
            f"MERGE ({node_label.model_dump()} {a}) "
            f"ON CREATE SET {node_label.cypher_label} = prop, {node_label.cypher_label}.created_at = timestamp()" 
            f"ON MATCH SET {', '.join([f'{node_label.cypher_label}.{key} = prop.{key}' for key in property_keys])}, {node_label.cypher_label}.modified_at  = timestamp()"
            )
        
        properties = [node.model_dump(by_alias=True, exclude_none=True) for node in nodes]
        r = tx.run(query,props = properties)
        return list(r)
        
        
    def connect_multiple_nodes(self, rel):
                            #        source_node_label : NodeLabelModel,
                            #    target_node_label : NodeLabelModel,
                            #    source_target_nodes : list[dict["source_node_model" : BaseModel, "target_node_type" : str, "target_node_model" : BaseModel, "rel_props" : dict]], 
                            #    relationship_label : RelationLabelModel)
        
        with self._driver.session() as session:
            session.execute_write(self._create_relationships_from_list, rel)

    @staticmethod
    def _create_relationships_from_list(tx,rel): #source_node_label,target_node_label,relationship_label, source_target_nodes
        ""
        rels = [{"s" : relIndex["source"].model_dump(), "t" : relIndex["target"].model_dump(), "label" : relIndex["rel_label"]} for relIndex in rel]
        print(rels)
        #  rels = [{
        #     "source" : IndexedNode(cypher_label="sn",label="Dataset",index_prop="label",index_value="asd1324sdd"),
        #     "target" : IndexedNode(cypher_label="sn",label="Attribute",index_prop="tag",index_value="att_column_length"),
        #     "rel_label" : "HAS_ATTRIBUTE_VALUE"
        # }]
        # properties = [{
        #         "source_node_props" : rel["source_node_model"].model_dump(exclude_none=True), 
        #         "target_node_props": rel["target_node_model"].model_dump(exclude_none=True), 
        #         "rel_props" : rel["rel_props"]} for rel in source_target_nodes]
        
        query = (
            "UNWIND $props as prop "
            f"MATCH ( prop.s )"
            f"MATCH ( prop.t )"
            f"MERGE (sn)-[r:prop.rel_label]->(tn)"
            #f"SET r += prop.rel_props "
            "RETURN r"
        )
        re = tx.run(query,props = rels)
        rr = list(re)
        
        
    # def insert_nodes_from_csv(self, node_label : NodeLabelModel, file_path : str):
    #     ""
    #     with self._driver.session() as session:
    #         session.execute_write(self._insert_csv,node_label.label, file_path)
        
    # @staticmethod
    # def _insert_csv(tx, node_label : str, file_path : str, properties : List[Tuple[str,int]]):
        
    #     query = (
    #         f"LOAD CSV FROM '{file_path}' AS row "
    #         f"MERGE (n:{node_label} {f'{prop_name}' for prop_name, row_index in properties}) "
    #         f"RETURN n"
    #     )        
    #     tx.run(query)

    
    
    def get_nodes_tag_by_label(self, node_label : NodeLabelModel) -> pd.DataFrame:
        ""
        with self._driver.session() as session:
            return session.execute_read(self._get_nodes_tag_by_label, node_label)
    
    @staticmethod
    def _get_nodes_tag_by_label(tx, node_label : NodeLabelModel) -> pd.DataFrame:
        ""
        query = (
            f"MATCH ({node_label.model_dump()})"
            f"RETURN {node_label.cypher_label}.tag AS tag" 
        )
        r = tx.run(query)
        return r.to_df()
        
    def count_nodes_by_label(self, node_label : NodeLabelModel) -> int:
        
        with self._driver.session() as session:
            return session.execute_read(self._count_nodes_by_label, node_label = node_label) 
        
        
    @staticmethod
    def _count_nodes_by_label(tx, node_label : NodeLabelModel) -> int:
        query = (
            f"MATCH ({node_label.model_dump()}) "
            f"RETURN count({node_label.cypher_label}) as count"
        )
        r = tx.run(query)
        return r.single().data()["count"]
        
        
    def get_nodes(self, node_label : NodeLabelModel) -> List[Dict]:
        ""
        with self._driver.session() as session:
            return session.execute_read(self._find_nodes,node_label)
        
        
    @staticmethod
    def _find_nodes(tx,node_label : NodeLabelModel):
        ""
        query = (
            f"MATCH ({node_label.model_dump()}) "
            f"RETURN {node_label.cypher_label} as nodes"
        )
        r = tx.run(query)
        return [n.data()["nodes"] for n in list(r)]
        
    def find_node(self, index_node : MatchIndexedNode) -> List[BaseModel]:
        ""
        with self._driver.session() as session:
            return session.execute_read(self._find_node,index_node)
        
    @staticmethod
    def _find_node(tx, index_node ):
        
        query = (
            f"{index_node.model_dump()}"
            "RETURN n"
        )
        r = tx.run(query)
        return r.values()
    
    def connect_one_node_to_many(self, source_node : MatchIndexedNode, target_node_label : NodeLabelModel, properties : List[Dict], relationship_label : str = "HAS_ATTRIBUTE_VALUE"):
        
        with self._driver.session() as session:
            session.execute_write(self._connect_node_to_other_nodes,source_node,target_node_label,properties,relationship_label)
    
    @staticmethod
    def _connect_node_to_other_nodes(tx, source_node : MatchIndexedNode, target_node_label : NodeLabelModel, properties : List[Dict], relationship_label : str = "HAS_ATTRIBUTE_VALUE"):
                
        query = (
            f"UNWIND $props as prop "
            f"{source_node.model_dump()} "
            f"MATCH ({target_node_label.model_dump()} {{tag : prop.target.tag}}) "
            f"MERGE (sn)-[r:{relationship_label}]->(tn) "
            f"RETURN count(r) as count"
        )
        
        r = tx.run(query,props=properties)
        return r
    
    
    
    def connect_two_nodes_by_tag(self, source_node_label : NodeLabelModel, target_node_label : NodeLabelModel, relationship_label : str, properties : List[Dict]):
        with self._driver.session() as session:
            session.execute_write(self._connect_two_nodes_by_tag,source_node_label,target_node_label,relationship_label, properties)
    
    @staticmethod
    def _connect_two_nodes_by_tag(tx, source_node_label : NodeLabelModel, target_node_label : NodeLabelModel, relationship_label : str, properties : List[Dict]):
        
        
        query = (
            f"UNWIND $props as prop "
            f"MATCH ({source_node_label.model_dump()} {{tag : prop.source.tag}}) "
            f"MATCH ({target_node_label.model_dump()} {{tag : prop.target.tag}}) "
            f"MERGE (sn)-[r:{relationship_label}]->(tn) "
            f"RETURN count(r) as count"
        )
        
        r = tx.run(query,props=properties)
        
        
    
    def get_counts_by_tag(self, source_node_label : NodeLabelModel, target_node_label : NodeLabelModel):
        
        with self._driver.session() as session:
            return session.execute_read(self._get_matching_tags_in_relationships, source_node_label, target_node_label)
        
    @staticmethod
    def _get_matching_tags_in_relationships(tx, 
                                            source_node_label : NodeLabelModel, 
                                            target_node_label : NodeLabelModel, 
                                            relationshion_label : str = "HAS_ATTRIBUTE_VALUE",
                                            tags : List[str] = ['att_digestion_method:sp3','att_organism:UP000005640']):
        
        query = (
            f"MATCH ({source_node_label.model_dump()})-[:{relationshion_label}]->({target_node_label.model_dump()}) "
            f"WHERE tn.tag in {tags} "
            f"WITH collect(tn) as targetNodes, sn "
            f"WHERE size(targetNodes) = {len(tags)} "
            f"RETURN distinct(sn.tag) as tags"
        )
        r = tx.run(query)
        print(r.to_df())
        return r 



    def get_nodes_by_tag_list(self, node_label : NodeLabelModel, tags : List[str]) ->  List[Dict]:
        ""
        with self._driver.session() as session:
            return session.execute_read(self._find_nodes_by_tag_list,node_label,tags)
        
    @staticmethod
    def _find_nodes_by_tag_list(tx, node_label : NodeLabelModel, tags : List[str]) -> List[Dict]:
        
        query = (
            f"MATCH ({node_label.model_dump()}) "
            f"WHERE {node_label.cypher_label}.tag IN {tags} "
            f"RETURN collect({node_label.cypher_label}) as nodes"
        )
        r = tx.run(query)
        return r.data()[0]["nodes"]

    
    def full_text_search(self, index_name : str, query_string : str):
        
        query = (
            "CALL db.index.fulltext.queryNodes($index_name, $query_string) YIELD node, score "
            "RETURN node.tag, score "
        )
        
        
        return self._driver.execute_query(query, index_name=index_name, query_string = query_string)



# class Neo4JFeatures(FeaturesABC):
    
#     def __init__(self, driver : Driver) -> None:
#         self._driver = driver 
        
        
        
#     def get_protein_sequence(self, tags : str) -> List[str]:
#         """"""
        
#         cypher_query = (
#             "MATCH (p:Protein) "
#             "WHERE p.tag in $tags "
#             "MATCH (p)-[:HAS_SEQUENCE]-(s:Sequence) "
#             "RETURN p.tag as feature_tag, s.content as sequence"
#         ) 
        
#         try:
#             r, _, _ = self._driver.execute_query(cypher_query,
#                                 database_="neo4j", 
#                                 routing_="r",
#                                 tags = tags)
#                                # result_transformer_= transform_query_result)
            
#         except Exception as e:
#             print("Finding sequence resulted in an error " + str(e))
#             return []
#         return [sequence.data() for sequence in r]
        
        
#     def get_protein_by_tags(self, tags : List[str], as_data_frame : bool = True) -> List[FeatureNeoModel]|pd.DataFrame:
#         ""
#         query = (
#             "MATCH (p:Protein) "
#             "WHERE p.tag in $tags "
#             "RETURN properties(p) as protein" 
#         )
#         r,_,_ = self._driver.execute_query(query, tags = tags, database_="neo4j", routing_="r")
        
#         if as_data_frame:
#             if len(r) == 0: return pd.DataFrame()
#             return pd.DataFrame([ri.values()[0] for ri in r]).set_index("tag")
        
#         return [FeatureNeoModel(**ri.data()["protein"]) for ri in r]
        
#     def get_protein_tags(self, proteome_id : str|List[str] = "UP000005640", is_quantified : bool = True) -> List[str]:
#         """Returns the proteins in the database using the proteme_ids. 
#         TO DO: RATHER ADD TO THE PROTEOME DATABASE CLASS? 
#         Parameters
#         ----------
#         proteome_id : str | List[str], optional
#             _description_, by default "UP000005640"
#         is_quantified : bool, optional
#             If True only proteins that were quantified in at least on experiment will be returned.
#             If False all protein tags will be returned, by default True

#         Returns
#         -------
#         List[str]
#             The protein tags (Uniprot IDs)
#         """
#         if isinstance(proteome_id,str):
#             proteome_id = [proteome_id]
        
#         if is_quantified:
#             cypher_query = (
#                 "MATCH (p:Protein) "
#                 "WHERE p.proteome_id in $proteome_id AND EXISTS {(p)-[:QUANTIFIED_IN]->(:Dataset)}"
#                 "RETURN collect(p.tag) as query_result " 
#             )
#         else:
#             cypher_query = (
#                 "MATCH (p:Protein) "
#                 "WHERE p.proteome_id in $proteome_id "
#                 "RETURN collect(p.tag) as query_result " 
#             )
#         try:
#             r = self._driver.execute_query(cypher_query , 
#                                         database_="neo4j", 
#                                         routing_="r", 
#                                         proteome_id = proteome_id,
#                                         result_transformer_= transform_query_result
#                                         )
#         except Exception as e:
#             print("Query finding resulted in an error " + str(e))
#             return []
        
#         return r
    
#     def get_quant_stats(self, tags : List[str]):
#         """Returns the general stats of a list of tags. 
        
#         This includes the following stats:
        
#         - quantified_in (int): The number of datasets in which 
#         the protein has been quantified 
#         - total_number (int): The number of dataset of the same proteome
#         - abundance_quantiles (List[float]): The quantiles of the log2 intensity of the requested tag (n=3, 0.25, 0.5, 0.75 quantile)
#         - total_abundance_quantiles (List[float]) - The quantiles of all the datasets that used the proteome 
#         (n=4, min, 0.25, 0.5, 0.75, max). 

#         Parameters
#         ----------
#         tags : List[str]
#             The tags of the proteins/feature for which the quantification stats should be returned. 
#             If the protein is not in the database, it will simply be ignored. 
#         """
        
#         query = (
#             "MATCH (p:Protein) "
#             "WHERE p.tag in $tags "
#             "MATCH (p)-[:IN_PROTEOME]->(av:AttributeValue) "
#             "MATCH (p)-[r_quant:QUANTIFIED_IN]->(d) "
#             "WITH p.tag as tag, count(r_quant) as quantified_in, count(d) as total_number, apoc.agg.percentiles(r_quant.avg_log2_abundance, [0.25,0.5,0.75]) as abundance_quantiles, "
#             "apoc.coll.zip(collect(r_quant.variance),collect(r_quant.max_variance_attribute)) as variances "
#             "MATCH (d:Dataset)-[:HAS_ATTRIBUTE_VALUE]-(av) "
#             "MATCH (d)<-[r_all:QUANTIFIED_IN]-(pp:Protein) "
#             "RETURN tag, quantified_in, total_number, abundance_quantiles, apoc.agg.percentiles(r_all.avg_log2_abundance, [0,0.25,0.5,0.75,1.0]) as total_abundance_quantiles, variances"
#         )
        
        
#         r = self._driver.execute_query(query, tags = tags, routing_="r", result_transformer_=Result.to_df)
#         print(r)
        
#     def find(self, query : str = "FB", proteome_id : str|List[str] = "UP000005640", limit : int = 10) -> List[FeatureNeoModel]:
#         """Returns a list of features that are found by a query string. 

#         Parameters
#         ----------
#         query : str, optional
#             _description_, by default "FB"
#         proteome_id : str|List[str], optional
#             The proteome_ids (Uniprot), by default "UP000005640" (Human)

#         Returns
#         -------
#         List[FeatureNeoModel]
#             The list of features in the database that match the query.
#             The list has a maximum length of limit. 
#         """
        
#         if isinstance(proteome_id,str):
#             proteome_id = [proteome_id]
        

#         cypher_query = (
#             "MATCH (p:Protein) "
#             "WHERE p.s CONTAINS $query_string AND p.proteome_id in $proteome_id "
#             "RETURN collect(p)[0..$limit] as query_result " 
#         )
#         try:
#             r = self._driver.execute_query(cypher_query , 
#                                         database_="neo4j", 
#                                         routing_="r", 
#                                         result_transformer_= transform_query_result,
#                                         query_string = query.lower(),
#                                         proteome_id = proteome_id,
#                                         limit = limit)
#         except Exception as e:
#             print("Query finding resulted in an error " + str(e))
#             return []
#         return [FeatureNeoModel(**f) for f in r]
               
        
        
#     def add_proteome_details(self, proteome_id : str, proteome_info : Dict):
#         ""
#         #trim proteome_info 
#         for attr in ["reference","genomeAssembly","dbReference","component",'annotationScore','scores']:
#             if attr in proteome_info:
#                 del proteome_info[attr]
#         proteome_info["text"] = proteome_info["name"]
#         proteome_info["attribute_tag"] = "att_proteome"
#         proteome_info["s"] = f"{proteome_id} {proteome_info['description']} {proteome_info['name']}"
#         query = (
#             "MERGE (av:AttributeValue {tag : $proteome_id}) "
#             "SET av += $proteome_info "
#             "WITH av "
#             "MATCH (a:Attribute {tag : 'att_proteome'}) "
#             "MERGE (a)-[:HAS_VALUE]->(av) "
#             "RETURN av"
            
#         ) 
        
#         self._driver.execute_query(query, proteome_id = proteome_id, proteome_info = proteome_info)
        
    
#     def insert_uniprot_proteome(self, proteome_id : List[str] = ["UP000005640"], reviewed : bool = True, user_tag : str = None) -> int: #:#"):#"file:///UP000005640.txt"):#
        
#         settings = UniprotAnnotationSettings()
#         uniprotKB_URL = settings.uniprotKBAPI_URL
        
#         return download_proteome_annotations(uniprotKB_URL,proteome_id,
#                                              chunc_callback=self.handle_uniprot_chunc, 
#                                              add_proteome_callback=self.add_proteome_details, 
#                                              reviewed = reviewed,
#                                              user_tag = user_tag)
        
#     def handle_uniprot_chunc(self,data : pd.DataFrame, proteome_id : str, user_tag : str = None):
#         """Data from the Uniprot API are returned in several pages covering
#         500 entries. This function handles the chuncks and inserts the entries into the database. 
        

#         Parameters
#         ----------
#         data : pd.DataFrame
#             _description_
#         proteome_id : str
#             _description_
#         user_tag : str, optional
#             The user that added the proteome identified by its tag, by default None
#         """
#         self._insert_uniprot_db(data,proteome_id,user_tag=user_tag)

    
#     def _insert_uniprot_db(self, data : pd.DataFrame, proteome_id : str = "UP000005640", user_tag : str = None): 
#         """Insert data from a Uniprot reference proteome to the database. 

#         Parameters
#         ----------
#         data : pd.DataFrame
#             The protein data with the following headers
            
#                 - Length (int) : The number of amino acids
#                 - Gene names (str) : All gene names associated with the protein
#                 - Gene Names (primary) (str)
#                 - Protein Names (str) - The associated protein name 
#                 - Entry (str) : The Uniprot ID 
#                 - Sequence (str) : The protein sequence.
                
#         proteome_id : str, optional
#             The Uniprot reference proteome ID, by default "UP000005640"
#         user_tag : str, optional
#             The tag associated with a user, by default None
#         """
        
#         query = (
#             "UNWIND $uniprot_features as row "
#             "MERGE (n:Protein:AttributeValue {tag : row.Entry}) "
#             "ON CREATE "
#             " SET n += {aa_length : row.Length, gene_name : row.`Gene Names (primary)`, gene_names : row.`Gene Names`, protein_name : row.`Protein names`, created_at : timestamp(), proteome_id : $proteome_id, s : toLower(row.`Gene Names`)+' '+toLower(row.Entry)+' '+toLower(row.`Protein names`), viewed : 0} "
#             "ON MATCH "
#             " SET n.gene_names = row.`Gene Names`, n.protein_name = row.`Protein names`, n.gene_name = row.`Gene Names (primary)`, n.aa_length = row.Length, n.proteome_id = $proteome_id "
#             "WITH n, row "
#             "MERGE (av:AttributeValue {tag : $proteome_attribute_tag}) "
#             "ON CREATE "
#             "SET av.created_at = timestamp(), av.user_tag = $user_tag "
#             "ON MATCH "
#             "SET av.modified_at = timestamp(), av.user_Tag = $user_tag "
#             "WITH n,av, row "
#             "MERGE (n)-[r:IN_PROTEOME]->(av) "
#             "MERGE (sequence:Sequence {content : row.Sequence, version : row.`Sequence version`}) "
#             "MERGE (n)-[:HAS_SEQUENCE]-(sequence) "
#         )
#         self._driver.execute_query(query, 
#                                    proteome_attribute_tag = proteome_id, 
#                                    uniprot_features = data.to_dict(orient="records"), 
#                                    proteome_id = proteome_id,
#                                    user_tag = user_tag,
#                                    routing_="w",
#                                    database_="neo4j")
        
#         print("Page added to database ...")
        

# #         CALL {
# #   LOAD CSV WITH HEADERS FROM 'https://data.neo4j.com/importing-cypher/persons.csv' AS row
# #   MERGE (p:Person {tmdbId: row.person_tmdbId})
# #   SET p.name = row.name, p.born = row.born
# # } IN TRANSACTIONS OF 200 ROWS



class Neo4JCalculations():
    
    def __init__(self, driver : Driver, feature : Neo4JFeatures) -> None:
        ""
        self._driver = driver 
        self._feature = feature 
        
    def correlate_features(self, proteome_id : str = None, min_abs_r : float = 0.7, min_values : int = 10):
        ""
        batch_id = randrange(100000,1000000)
        tags = self._feature.get_protein_tags(proteome_id=proteome_id)
        print(f"batch id: {batch_id}")
        cypher_query = (
            "MATCH (p1:Protein {tag : $target_protein})-[r:QUANTIFIED_IN]-(d:Dataset)-[r1:QUANTIFIED_IN]-(p2:Protein ) " #{tag : "A1A4S6"}
            "WHERE NOT EXISTS {(p1)-[cw:CORRELATES_WITH]-(p2) WHERE cw.batch_id = $batch_id} " #get the relationships where the relation does not exists or the batch ID is different.
            "WITH apoc.coll.intersection(r.sample_index,r1.sample_index) as samples, r.qs as Q1, r1.qs as Q2, r.sample_index as IDX1, r1.sample_index as IDX2, p1, p2, d.tag as d_tag "
            "UNWIND samples as idx "
            "WITH collect(Q1[apoc.coll.indexOf(IDX1,idx)]) as q1, collect(Q2[apoc.coll.indexOf(IDX2,idx)]) as q2,p1,p2, apoc.coll.toSet(collect(d_tag)) as ds "
            "RETURN p1.tag,p2.tag,q1,q2,ds"
            ) 
        
        cypher_query_set = (
            "UNWIND $corr as cor "
            "MATCH (p1:Protein {tag : cor.tag_1}), (p2:Protein {tag : cor.tag_2}) "
            "MERGE (p1)-[cw:CORRELATES_WITH]-(p2) "
            "ON CREATE "
            "SET cw.created_at = timestamp(), cw.value = cor.r_value, cw.datasets = cor.datasets , cw.batch_id = $batch_id, cw.n = cor.n "
            "ON MATCH "
            "SET cw.modified_at = timestamp(), cw.value = cor.r_value, cw.datasets = cor.datasets, cw.batch_id = $batch_id, cw.n = cor.n, cw.matched = True "
            "RETURN cw "
        )
        
        for tag in ["Q9Y5T4","O14925","Q9Y4W6","Q15070"]:#
            try:
                r, _ , _ = self._driver.execute_query(cypher_query , 
                                database_="neo4j", 
                                routing_="r", 
                                #result_transformer_= transform_query_result,
                                target_protein = tag,
                                batch_id = batch_id)
                
            except Exception as e:
                print("Query finding resulted in an error " + str(e))
                r = []
            print(f"Calculating pearson for {len(r)} features")
            corr = []
            for d in r:
                v = d.values() 
                p = np.array(v[2], dtype=float)
                if p.size > min_values:
                    q = np.array(v[3], dtype=float)
                    dataset_tags = v[4]
                    r = pearson(p,q,check_nan=False,reverse=False)
                    
                    if abs(r) > min_abs_r:
                        corr.append({
                            "tag_1" : v[0],
                            "tag_2" : v[1],
                            "r_value" : r,
                            "n" : p.size,
                            "datasets" : dataset_tags
                        })
            print(f"Found {len(corr)} correlations that match min r.")
            if len(corr) > 0:
                try:
                    r, _ , _ = self._driver.execute_query(cypher_query_set, 
                                    database_="neo4j", 
                                    routing_="w", 
                                    #result_transformer_= transform_query_result,
                                    corr = corr,
                                    batch_id = batch_id)
                    
                except Exception as e:
                    print("Query finding resulted in an error " + str(e))
                    return []
            
                        
        
       # return [d.values() for d in r]
            
#                 [25.4862 25.4676 25.4362 25.3679 25.3477 25.2821 25.3239 25.4138 21.9742
#  21.7876 20.9388 21.8839 22.2036 20.8802] [19.6728 21.7307 21.7955 21.3376 21.8346 21.0559 21.343  20.6364 21.3857
#  21.0756 21.5356 21.0951 20.9742 20.5915] 14
                
                
#DB = MCNeo4JDatabase()