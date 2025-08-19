from typing import List, Tuple, Literal
from neo4j import Driver, Result

from lib.database.abstract.Samples import SamplesABC
from services.encryption import create_hierarchical_hash
from config.models.submissions.submissions import AttributeTree
import uuid
class Neo4JSamples(SamplesABC):
    "" 
    def __init__(self, driver : Driver):
        
        self._driver = driver 
    
    def _get_sample_tag(self, sample_name : str, submission_tag : str) -> str:
        """Generates a sample tag based on the sample name and submission tag.
        
        Parameters
        ----------
        sample_name : str
            The name of the sample.
        submission_tag : str
            The tag of the submission to which the sample belongs.
        
        Returns
        -------
        str
            A unique sample tag.
        """
        return f"{submission_tag}|{sample_name}"
    
    def exists(self, tag : str) -> bool:
        "Check if a sample is associated with the given tag."
        
        query = (
            "WITH EXISTS {(s:Sample {tag : $tag})} as exists "
            "RETURN exists"
        )
        
        r = self._driver.execute_query(query,routing_="r",result_transformer_=Result.value, tag = tag)
        return r[0]


    def condition_procedure_exists(self, tag : str) -> bool:
        "Check if a condition procedure exists for the given tag."
        
        query = (
            "WITH EXISTS {(ca:ConditionApplication {tag : $tag})} as exists "
            "RETURN exists"
        )
        
        r = self._driver.execute_query(query,routing_="r",result_transformer_=Result.value, tag = tag)
        return r[0]
    
    def count(self, trait_tag : str = None) -> int:
        
        "Counts the number of samples. If a specific trait tag is provided, the number of samples with a trait will be counted."
        
        if trait_tag is not None:
            query = (
                "MATCH (s:Sample)<-[:HAS_SAMPLE]-(submission:Submission)-[:HAS_ATTRIBUTE_VALUE]->(trait:Trait) "
                "WHERE trait.tag = $trait_tag "
                "RETURN count(s) as count"
            )
        else:
            query = (
                "MATCH (s:Sample) "
                "RETURN count(s) as count"
            )
        
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.data, trait_tag = trait_tag)
        return r[0]["count"] 
        
        
    def insert(self, submission_tag : str, sample_name : str, sample_index : int) -> str:
        "Insert a new sample to a given submission" 
        #if self.exists(tag = tag): raise ValueError("Sample tag exists already. ")
        sample_tag = self._get_sample_tag(sample_name, submission_tag)
        if self.exists(tag = sample_tag): raise ValueError("Sample tag exists already. ")
        query = (
            "MATCH (s:Submission {tag : $submission_tag}) "
            "MERGE (sample:Sample {tag : $sample_tag, name : $sample_name, sample_index : $sample_index, created_at : timestamp()}) "
            "MERGE (s)-[:HAS_SAMPLE]->(sample) "
            "RETURN sample.tag "
        )

        r = self._driver.execute_query(query, routing_="w", result_transformer_=Result.value, sample_tag=sample_tag,
                                   submission_tag=submission_tag, sample_name=sample_name, sample_index=sample_index)
        return r[0] if len(r) > 0 else None
     
    def handle_children(self, sample_tag, trait_node, parent_tag):
        
        for attribute_node in trait_node["children"]:
            attribute_tag = attribute_node["tag"]
            trait_nodes = attribute_node["children"]
            if len(trait_nodes) > 0:
                for trait_node in trait_nodes:
                    parent_tag_2 = self.insert_condition_value(sample_tag, attribute_tag=attribute_tag, value = trait_node.get("value"), trait_tag= trait_node["tag"], parent_tag=parent_tag)
                    if len(trait_node.get("children",[])) > 0:
                       # for child in trait_node["children"]:
                        self.handle_children(sample_tag, trait_node=trait_node, parent_tag=parent_tag_2)
    
    def insert_condition_value(self, sample_tag : str, parent_tag : str, attribute_tag : str, trait_tag : str, value : str|float|int = None ):
        
        cv_tag = uuid.uuid4().hex
        query = (
            "MATCH (ca:ConditionApplication|ConditionValue {tag : $parent_tag}) "
            "MERGE (cv:ConditionValue {tag : $cv_tag, text : $value || $trait_tag}) "
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
                "MERGE (ca)-[r:HAS_VALUE]->(cv) "
                "SET r.created_at = timestamp(), r.attribute_tag = $attribute_tag, r.trait_tag = $trait_tag"
            )
        
        self._driver.execute_query(query, value = value, trait_tag = trait_tag, cv_tag = cv_tag, attribute_tag = attribute_tag, parent_tag = parent_tag)
        return cv_tag 
    
    def insert_condition_application(self, sample_tag : str, sample_data : List[AttributeTree]):
        """Insert a condition application for a given sample.
        The condition application is a hierarchical structure that describes the conditions applied to the sample. 
        The data structure is used to generate a unique tag for the condition application. Hence, if the datastructure is the same, the same tag will be used connecting the 
        samples to the same condition node. 

        Parameters
        ----------
        sample_tag : str
            The tag of the sample.
        sample_data : List[AttributeTree]
            The condition data to insert.
        This data should be a list of AttributeTree objects, where each object represents a condition application.
        Each dictionary should have the following structure, here is a complex example having multiple attributes and traits:
        {
            "type": "attribute",
            "tag": "att_compound",
            "children": [               
                {
                    "type": "trait",
                    "tag": "att_compound:dmso",
                    "children": [       
                        {
                            "type": "attribute",
                            "tag": "att_concentration",
                            "children": [
                                {"type": "trait", "tag": "mM", "value": 2, 
                                 "children": [
                                     {"type" : "attribute", "tag" : "temperature", "children" : [
                                         {"type" : "trait", "tag" : "high"}
                                     ]}
                                 ]}
                            ]
                        },
                        {
                            "type": "attribute",
                            "tag": "Time",
                            "children": [
                                {"type": "trait", "tag": "h", "value": 5, "children": []}
                            ]
                        }
                    ]

        """
        sample_data = [x.model_dump() for x in sample_data]  # Convert Pydantic models to dicts if necessary
        print(sample_data)
        ca_tag = create_hierarchical_hash(sample_data)
    

        if self.condition_procedure_exists(tag = ca_tag):
            ##if exists, then just connect to the samples 
            query = (
                "MATCH (ca:ConditionApplication {tag : $ca_tag}) "
                "MATCH (s:Sample {tag : $sample_tag}) "
                "MERGE (s)-[:HAS_APPLICATION]->(ca) "
            )
            
            self._driver.execute_query(query, routing_="w", ca_tag = ca_tag, sample_tag = sample_tag)
            
        else:
            for condition_application in sample_data:
                attribute_tag = condition_application["tag"]
                for trait_node in condition_application["children"]:
                    trait_tag = trait_node["tag"]
                    
                    query = (
                        "MATCH (s:Sample {tag : $sample_tag}) "
                        "MERGE (ca:ConditionApplication {tag : $ca_tag}) "
                        "ON CREATE SET ca.created_at = timestamp() "
                        "WITH ca, s "
                        "MATCH (a:Attribute {tag : $attribute_tag})-[:PART_OF]->(ag:AttributeGroup {tag : 'sample'}) " #only sample attributes are allowed here "
                        "MATCH (t:Trait {tag : $trait_tag}) "
                        #connect to sample 
                        "MERGE (s)-[:HAS_APPLICATION]->(ca) "
                        "MERGE (ca)-[:OF_ATTRIBUTE]->(a) "
                        "MERGE (ca)-[:INSTANCE_OF]-(t) "
                    )
                    
                    self._driver.execute_query(query, routing_= "w", ca_tag = ca_tag, sample_tag = sample_tag, trait_tag = trait_tag, attribute_tag = attribute_tag)        
                    
                    if len(trait_node.get("children",[])) > 0:
                        # for child in trait_node["children"]:
                        self.handle_children(sample_tag, trait_node=trait_node, parent_tag=ca_tag)
                    
    
    def get_condition_procedure_by_sample(self, tag: str = None, sort_by_most_frequent : bool = True, limit : int = None) -> List[str]|str:
        """Get all condition procedures for a given sample. If no sample tag is provided, all condition procedures are returned.
        You may also sort the results by the most frequent condition procedures.
        If only one tag is found, a single string is returned. If no tag is found, an empty list is returned. 
        
        Parameters
        ----------
        tag : str, optional
            The tag of the sample to get the condition procedures for.
        sort_by_most_frequent : bool
            If True, the results are sorted by the most frequent condition procedures.
        limit : int, optional
            The maximum number of results to return. If None, all results are returned.
            
        Returns
        -------
        List[str]|str
            A list of condition procedure tags. If only a single tag is found, a single string is returned.
            If no tag is found, an empty list is returned.
        """
        
        query = (
            "MATCH (ca:ConditionApplication)<-[r:HAS_APPLICATION]-(s:Sample) "
        )

        if tag is not None:
            query += "WHERE s.tag = $tag "
            
        query += "RETURN ca.tag as tag "
        if sort_by_most_frequent:
            query += "ORDER BY count(r) DESC "
        if limit is not None:
            query += "LIMIT $limit "    

        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value, tag=tag)
        if len(r) == 1:
            return r[0] 
        else:
            return r
    
        
    def get_condition_procedure(self, tag : str):
        """Get a condition procedure by its tag."""
        
        query = (
            "MATCH (ca:ConditionApplication {tag : $tag}) "
            "RETURN ca.tag as tag, ca.text as text, ca.created_at as created_at "
        )
        
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value, tag=tag)
        return r[0] if len(r) > 0 else None 
        
    
    def get_samples_by_genotype(self, genotype_tag : str):
        "" 
        query = (
            "MATCH (s:Sample)-[:HAS_GENOTYPE]->(g:Genotype) "
            "WHERE g.tag = $genotype_tag "
            "RETURN s.tag as tag, g.tag as genotype_tag "
        )
        
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.data, genotype_tag=genotype_tag)
        return r 

    def get_sample(self, tag : str):
        "Returns a sample an its trait as well genotype annotation."
        
        query = (
            "MATCH (s:Sample {tag : $tag})-[:HAS_SAMPLE]-(submission:Submission) " 
            "OPTIONAL MATCH (s)-[:HAS_GENOTYPE]->(g:Genotype) "
            "OPTIONAL MATCH (s)-[:HAS_SAMPLE_ATTRIBUTE_VALUE]->(trait:AttributeValue)"
            "RETURN s.tag as tag, g.tag as genotype_tag, trait.tag as trait_tag, submission.tag as submission_tag "
        )
        
        r = self._driver.execute_query(query,routing_="r",result_transformer_=Result.data, tag = tag)
        return  r 
    

    
    def get_sample_string(self, tag : str) -> str:
        """Return a string for sample that describes the traits for a given sample. 
        This should be used to either visualize the sample in the gui. Or to access
        statistics as the string will be explicit for the trait/attributes"""
        
        query = (
            "MATCH (ca:ConditionApplication)-[]-(s:Sample {tag : $tag}) " 
            "CALL apoc.path.expand(ca, 'HAS_VALUE|HAS_UNIT|HAS_CHILD>', null, 1, 10) YIELD path "
            "WITH path "
            "WITH nodes(path) AS nodelist, length(path) AS depth "

            "WITH [x IN nodelist WHERE x:Trait OR x:ConditionValue | x.tag] AS tags, depth "

            "ORDER BY depth DESC "

            "WITH collect(tags) AS tagpaths "

            "WITH [tp IN tagpaths | "
            "reduce(output = "", tag IN reverse(tp) | "
            "   CASE output "
            "    WHEN "" THEN tag "
            "    ELSE tag + '(' + output + ')' "
            "    END) "
            "] AS nestedStrings "

            "RETURN nestedStrings "

            )
        
        r = self._driver.execute_query(query, routing = "r", result_transformer_=Result.value, tag = tag)
        print(r)
        
        return r 
    
    
    
    
    
    
    
