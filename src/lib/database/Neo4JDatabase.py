
from neo4j import GraphDatabase, Driver

from typing import List, Dict

from config.enums.states import SubmissionStatesEnums
from config.enums.users.roles import UserRolesEnum
from config.settings.db import get_db_settings

from lib.database.neo4j.Features import Neo4JFeatures
from services.json import read_json 

from pydantic import BaseModel, field_validator, model_serializer


import numpy as np 
from random import randrange


from lib.data.utils.pearson import pearson


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
    ConstraintModel(constrain_label  = "protein_tag", node_label = NodeLabelModel(label = "Protein"),property_name = ["tag"]),
    ConstraintModel(constrain_label  = "sample_tag", node_label = NodeLabelModel(label = "Sample"),property_name = "tag"),
    ConstraintModel(constrain_label  = "submission_label",node_label = NodeLabelModel(label = "Submission"),property_name ="tag"),
    ConstraintModel(constrain_label  = "attribute_tag",node_label = NodeLabelModel(label = "Attribute"),property_name ="tag"),
    ConstraintModel(constrain_label  = "trait_tag",node_label = NodeLabelModel(label = "Trait"),property_name ="tag"),
    ConstraintModel(constrain_label  = "state_tag",node_label = NodeLabelModel(label = "State"),property_name ="tag"),
    ConstraintModel(constrain_label  = "user_tag",node_label = NodeLabelModel(label = "User"),property_name = ["tag","email"]),
    ConstraintModel(constrain_label  = "state_tag",node_label = NodeLabelModel(label = "State"),property_name ="tag"),
    ConstraintModel(constrain_label  = "user_role_tag",node_label = NodeLabelModel(label = "Role"),property_name ="tag"),
    ConstraintModel(constrain_label  = "metatext_tag",node_label = NodeLabelModel(label = "MetaText"),property_name ="tag"), #meta text? 
    ConstraintModel(constrain_label  = "qc_tag",node_label = NodeLabelModel(label = "QCRun"),property_name ="tag"),
    ConstraintModel(constrain_label  = "peptide_tag",node_label = NodeLabelModel(label = "Peptide"),property_name ="tag"),
    ConstraintModel(constrain_label  = "news_tag",node_label = NodeLabelModel(label = "News"),property_name ="tag"),
    ConstraintModel(constrain_label  = "research_group_tag",node_label = NodeLabelModel(label = "ResearchGroup"),property_name = "tag"),
    ConstraintModel(constrain_label  = "phenotype_tag",node_label = NodeLabelModel(label = "Phenotype"),property_name = "tag"),
    ConstraintModel(constrain_label  = "comment_tag",node_label = NodeLabelModel(label = "Comment"),property_name = "tag"),
    ConstraintModel(constrain_label  = "maintenance_procedure_tag",node_label = NodeLabelModel(label = "MaintenanceProcedure"),property_name = "tag"),
    ConstraintModel(constrain_label  = "symptom_tag",node_label = NodeLabelModel(label = "Symptom"),property_name = "tag"),
    ConstraintModel(constrain_label  = "spare_part_tag",node_label = NodeLabelModel(label = "SparePart"),property_name = "tag"),
    ConstraintModel(constrain_label  = "maintenance_state_tag",node_label = NodeLabelModel(label = "MaintenanceState"), property_name = "tag"),
    ConstraintModel(constrain_label  = "maintenance_event_tag",node_label = NodeLabelModel(label = "MaintenanceEvent"), property_name = "tag"),
    ConstraintModel(constrain_label  = "condition_application_tag",node_label = NodeLabelModel(label = "ConditionApplication"), property_name = "tag"),
    ConstraintModel(constrain_label  = "meta_text_tag",node_label = NodeLabelModel(label = "MetaText"), property_name = "tag"),
    ConstraintModel(constrain_label  = "view_counter_submission_tag",node_label = NodeLabelModel(label = "ViewCounter"), property_name = "submission_tag"),
    ConstraintModel(constrain_label  = "protein_group_tag",node_label = NodeLabelModel(label = "ProteinGroup"), property_name = "tag"),
    ConstraintModel(constrain_label  = "genotype_tag",node_label = NodeLabelModel(label = "Genotype"), property_name = "tag"),
    ConstraintModel(constrain_label  = "condition_value_tag",node_label = NodeLabelModel(label = "ConditionValue"), property_name = "tag"),
    ConstraintModel(constrain_label  = "external_service_tag",node_label = NodeLabelModel(label = "ExternalService"), property_name = "tag"),
    ConstraintModel(constrain_label  = "statistics_tag",node_label = NodeLabelModel(label = "Statistics"), property_name = "tag"),
    ConstraintModel(constrain_label  = "run_tag",node_label = NodeLabelModel(label = "Run"), property_name = "tag"),
    ConstraintModel(constrain_label  = "runlist_tag",node_label = NodeLabelModel(label = "RunList"), property_name = "tag"),
    ConstraintModel(constrain_label  = "annotation_tag",node_label = NodeLabelModel(label = "Annotation"), property_name = "tag"),
    ConstraintModel(constrain_label  = "annotation_group_tag",node_label = NodeLabelModel(label = "AnnotationGroup"), property_name = "tag"),
    ConstraintModel(constrain_label  = "phenotype_association_tag",node_label = NodeLabelModel(label = "PhenotypeAssociation"), property_name = "tag"),
    ConstraintModel(constrain_label  = "disease_tag",node_label = NodeLabelModel(label = "Disease"), property_name = "tag"),
    ConstraintModel(constrain_label  = "variant_tag",node_label = NodeLabelModel(label = "Variant"), property_name = "tag"),
    ConstraintModel(constrain_label  = "instrument_state_tag",node_label = NodeLabelModel(label = "InstrumentState"), property_name = "tag"),
    ConstraintModel(constrain_label  = "xl_tag",node_label = NodeLabelModel(label = "XL"), property_name = "tag")

]

DB_SETTINGS = get_db_settings()



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
    

class Neo4JConstructor:
    
    def __init__(self, driver : Driver) -> None:
        self._driver = driver 
        self.features = Neo4JFeatures(driver=driver)
        self.factory = Neo4JFactory(driver=driver)
        
        self._add_constraints()
        self._add_indices()
        self._add_states()
        #self._add_unit(units=units)
        self._add_user_roles()   
        
    def set_up_phenotypes(self):
        
        phenotype_json = read_json("/Users/hnolte/Documents/GitHub/mitocube-backend/resources/phenotypes/phenotypes.json")
        
        
    def _add_indices(self):
        
        self.factory.create_index("index_protein_proteome_id",NodeLabelModel(label="Protein"),["proteome_id"]) 
        self.factory.create_text_index("protein_s",NodeLabelModel(label = "Protein"),"s")
        self.factory.create_text_index("user_s",NodeLabelModel(label = "User"),"s")
        self.factory.create_text_index("phenotype_s",NodeLabelModel(label = "Phenotype"),"s")
        self.factory.create_text_index("genotype_s",NodeLabelModel(label = "Genotype"),"s")
        self.factory.create_text_index("protein_gene_search",NodeLabelModel(label = "Protein"),"gene_name")
        self.factory.create_text_index("protein_tag_search",NodeLabelModel(label = "Protein"),"tag")    
        self.factory.create_text_index("trait_search",NodeLabelModel(label = "Trait"),"s")   
        self.factory.create_text_index("symptom_search",NodeLabelModel(label = "Symptom"),"s") 
        self.factory.create_text_index("sparepart_search",NodeLabelModel(label = "SparePart"),"s")  
        self.factory.create_text_index("externalservice_search",NodeLabelModel(label = "ExternalService"),"s")   
        
        
        
    def _add_constraints(self):
    
        for c in constraints:
            if isinstance(c.property_name,str):
                self.factory.create_unique_constraint(c.constrain_label,node_label=c.node_label,property_name=c.property_name)
                self.factory.create_index(f"index_{c.constrain_label}",c.node_label,[c.property_name])
            else:
                self.factory.create_unique_constraint(c.constrain_label,node_label=c.node_label,property_name=c.property_name[0])
                self.factory.create_index(f"index_{c.constrain_label}",c.node_label,c.property_name)

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
        
        pass
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
            f"ON CREATE SET {node_label.cypher_label} += properties(prop), {node_label.cypher_label}.created_at = timestamp()" 
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