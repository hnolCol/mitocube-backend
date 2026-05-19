from lib.database.abstract.ConditionApplications import ConditionApplicationABC
from config.models.conditions_applications import ConditionApplicationItemModel, ConditionApplicationTreeModel
from services.condition_application import build_condition_application_tree
from config.models.attributes import AttributeTree
from services.encryption import create_hierarchical_hash
from typing import Dict, List 
from neo4j import Driver, Result 
from lib.database.abstract.Attributes import AttributesABC
from lib.database.abstract.Proteins import ProteinsABC


class Neo4JConditionApplications(ConditionApplicationABC):
    
    def __init__(self, driver : Driver, attributes: AttributesABC, proteins: ProteinsABC, *args, **kwargs) -> None:
        
        self._driver = driver
        self._attributes = attributes
        self._proteins = proteins


    def _has_values(self, tag : str) -> bool:
        """Check if a condition application has values associated with it.

        Parameters
        ----------
        tag : str
            The tag of the condition application.

        Returns
        -------
        bool
            True if the condition application has values, False otherwise.
        """
        query = (
            "MATCH (ca:ConditionApplication {tag : $ca_tag})-[:HAS_VALUE*0..]->(cv:ConditionValue) "
            "RETURN COUNT(cv) > 0 AS has_values "
        )
        r = self._driver.execute_query(query, routing_="r", ca_tag=tag, result_transformer_=Result.value)
        return r[0] if len(r) > 0 else False 
    

    def exists(self, tag : str) -> bool: 
        """If a submission tag is associated with a condition application. 
        Condition applications are always associated with submissions, but such submissions that 
        have specific conditions applied to them.

        Parameters
        ----------
        tag : str
            _description_

        Returns
        -------
        bool
            _description_
        """
        
        query = "WITH EXISTS {(ca:ConditionApplication {tag : $ca_tag})} as exists RETURN exists"
        r = self._driver.execute_query(query, routing_="r", ca_tag=tag, result_transformer_=Result.value)
       
        return r[0] if len(r) > 0 else False

    def get(self, tag: str) -> List[List[ConditionApplicationItemModel]]:
        "Return the condition application details. Returns None if not found."

        if not self._has_values(tag):
            query = (
                "MATCH (ca:ConditionApplication {tag : $ca_tag}) "
                "MATCH (ca)-[:OF_ATTRIBUTE]->(a:Attribute) "
                "MATCH (ca)-[:INSTANCE_OF]->(t:Trait) "
                "RETURN [[{ label : labels(ca)[0], tag : ca.tag, attribute_tag : a.tag, trait_tag : t.tag, value : null}]] AS children "
            )
        else:

            query = (
                "MATCH (ca:ConditionApplication {tag : $ca_tag}) "
                "OPTIONAL MATCH p = ((ca)-[:HAS_VALUE*0..]->(cv:ConditionValue)) "
                "WITH ca, collect(nodes(p)) AS paths "
                "RETURN [path IN paths | "
                "            [n IN path | "
                "                { "
            "                       label: labels(n)[0], " #label of the node 
                "                   tag : n.tag, "
                "                    trait_tag: [(n)-[:INSTANCE_OF]->(t:Trait) | t.tag][0], "
                "                    attribute_tag: [(n)-[:OF_ATTRIBUTE]->(a:Attribute) | a.tag][0], "
                "                    protein_tag : CASE WHEN [(n)-[:OF_ATTRIBUTE]->(a:Attribute) | a.tag][0] = 'att_protein' THEN [(n)-[:EFFECTS]->(p:Protein) | p.tag][0] ELSE null END, "
                "                    value : n.value      "           
                "                    } "
                "            ] "
                "    ] AS children "
            )

        r = self._driver.execute_query(query, routing_="r", ca_tag=tag, result_transformer_=Result.value)
        return [[ConditionApplicationItemModel(**rii) for rii in ri] for ri in r[0]] if len(r) > 0 and len(r[0]) > 0 else [[]]


    def get_attribute(self, tag: str) -> str:
        "Return the attribute tag of the condition application. Only the first level attribute is returned."
        if not self.exists(tag):
            return None
        query = (
            "MATCH (ca:ConditionApplication {tag : $ca_tag})-[:OF_ATTRIBUTE]->(a:Attribute) "
            "RETURN a.tag "
        )

        r = self._driver.execute_query(query, routing_="r", ca_tag=tag, result_transformer_=Result.value)
        return r[0] if len(r) > 0 else None

    def get_tree(self, tag: str) -> List[ConditionApplicationTreeModel]:
        "Return a human-readable text representation of the condition application."

        ca = self.get(tag)
        return build_condition_application_tree(ca)



    def extract_ca_item(self, item : ConditionApplicationTreeModel, add_separator = False) -> str:
        """Extracts the text representation of a condition application item recursively.
        Parameters
        ----------
        item : Dict
            The condition application item. The keys must include 'value', 'trait_tag', 'attribute_tag', and 'children'.
            If no children are present, 'children' should be an empty list.
        add_separator : bool, optional
            Whether to add a separator after the item, by default False
        """
        t = ""
        if item.value is not None:
                val = item.value
                if isinstance(val, float):
                    # Use general format, strip trailing .0, use scientific notation for small numbers
                    t += f"{val:.6g}"
                elif item.attribute_tag == "att_protein":
                    if "||" in str(item.value):
                        protein_tags = item.value.split("||")
                        gene_names = [self._proteins.get_gene_name(tag) for tag in protein_tags if tag]
                        t += " | ".join(gene_names)
                    else:
                        t += f"{self._proteins.get_gene_name(item.value)}"
                else:
                    t += f"{val}"
        if item.attribute_tag != "att_protein":
            #this would add the proteome which appers to be clumpy.feature_tag}/data
            t += f"{self._attributes.get_trait_text(item.trait_tag)}"
        if item.children is not None and len(item.children) > 0:
            t += " ("
            for n,c in enumerate(item.children):
                t += self.extract_ca_item(c, add_separator = n < len(item.children)-1) 
                t += ", " if add_separator else ""
            t += ")"
        return t

    def get_text(self, tag : str) -> str:
        "Return a human-readable text representation of the condition application."

        ca_tree = self.get_tree(tag)
        if ca_tree is not None and len(ca_tree) > 0:
            return self.extract_ca_item(ca_tree[0])
        else:
            return ""


    def _handle_children(self, trait_node : dict, parent_tag : str, extra_data_for_hash : dict = {}):
        
        for attribute_node in trait_node.get("children", []):
            if attribute_node.get("type") != "attribute":
                raise ValueError("Child node is not of type attribute.")
            attribute_tag = attribute_node["tag"]
            trait_nodes = attribute_node["children"]
            if len(trait_nodes) > 0:
                for trait_node in trait_nodes:
                    parent_tag_2 = self.insert_condition_value(attribute_tag=attribute_tag, value = trait_node.get("value"), trait_tag= trait_node["tag"], parent_tag=parent_tag, extra_data_for_hash = extra_data_for_hash)
                    # if len(trait_node.get("children",[])) > 0:
                    #     self._handle_children(trait_node=trait_node, parent_tag=parent_tag_2)
                    if len(trait_node.get("children", [])) > 0:
                        self._handle_children(trait_node=trait_node, parent_tag=parent_tag_2, extra_data_for_hash=extra_data_for_hash)
            
    def insert_condition_value(self, parent_tag : str, attribute_tag : str, trait_tag : str, value : str|float|int = None, extra_data_for_hash : dict = {}) -> str:
        gcv_tag = create_hierarchical_hash(data = {"parent_tag" : parent_tag, "attribute_tag" : attribute_tag, "trait_tag" : trait_tag, "value" : value, **extra_data_for_hash})         
        #gcv_tag = create_hierarchical_hash(data = {"attribute_tag" : attribute_tag, "trait_tag" : trait_tag, "value" : value, **extra_data_for_hash})
        query = (
            "MATCH (ca:ConditionApplication|ConditionValue {tag : $parent_tag}) "
            "MERGE (cv:ConditionValue {tag : $gcv_tag}) "
            "ON CREATE SET cv.created_at = timestamp() "
        )
        if value is not None:
            query += "SET cv.value = $value "
        if attribute_tag == "att_protein" and value is not None:
             query += (
                "WITH ca,cv "
                "MATCH (p:Protein {tag : $value}) "
                "WITH ca,cv,p "
                "MERGE (cv)-[:EFFECTS]->(p) "
            )
        query += (
                "WITH ca,cv "
                "MERGE (a:Attribute {tag : $attribute_tag}) "
                "MERGE (t:Trait {tag : $trait_tag}) "
                "WITH ca,cv,a,t "
                "MERGE (cv)-[:OF_ATTRIBUTE]-(a) "
                "MERGE (cv)-[:INSTANCE_OF]-(t) "
                "MERGE (ca)-[r:HAS_VALUE]->(cv) "
                "SET r.created_at = timestamp(), r.attribute_tag = $attribute_tag, r.trait_tag = $trait_tag"
            )
        
        self._driver.execute_query(query, value = value, trait_tag = trait_tag, gcv_tag = gcv_tag, attribute_tag = attribute_tag, parent_tag = parent_tag)

        return gcv_tag


    def insert(self, condition_application : AttributeTree, extra_data_for_hash : Dict={}) -> str:
        """Inserts a new condition application into the database.

        Parameters
        ----------
        condition_application : AttributeTree
            The condition application to insert.
            The condition application to insert.


        Returns
        -------
        str
            The tag of the inserted condition application.

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
        component = condition_application.model_dump()  # Convert Pydantic models to list of dicts if necessary
        hash_tag = create_hierarchical_hash({**component, **extra_data_for_hash})        

        if not self.exists(hash_tag):
            attribute_tag = component.get("tag") 
            for child in component.get("children", []):
                child_tag = child.get("tag")
                
                query = (
                    "MERGE (ca:ConditionApplication {tag : $hash_tag}) "
                    "ON CREATE SET ca.created_at = timestamp() "
                    "WITH ca "
                    "MATCH (a:Attribute {tag : $attribute_tag}) "
                    "MERGE (ca)-[:OF_ATTRIBUTE]->(a) "
                    "WITH ca, a "
                    "MATCH (t:Trait {tag : $child_tag}) "
                    "MERGE (ca)-[:INSTANCE_OF]->(t) "
                )
                self._driver.execute_query(query, hash_tag = hash_tag, routing_="w", database_="neo4j", child_tag = child_tag, attribute_tag=attribute_tag)
                if len(child.get("children",[])) > 0:
                    self._handle_children(trait_node=child, parent_tag=hash_tag, extra_data_for_hash = extra_data_for_hash)     
        return hash_tag
    
    def delete(self, tag: str) -> bool:
        """Deletes a condition application from the database.

        Parameters
        ----------
        tag : str
            The tag of the condition application to delete.

        Returns
        -------
        bool
            True if the deletion was successful, False otherwise.
        """
        
        
    def find(self, search_string : str = None, samples_only : bool = True, submission_tag : str = None, attribute_tag : str = None, trait_tag : str = None, sort_by_frequency : bool = True, limit : int = None) -> List[str]:
        "Returns the tags of matching condition applications."
        
        query = "MATCH (ca:ConditionApplication)<-[r:HAS_APPLICATION]-(:Sample|Submission)"
        if search_string is not None and search_string != "":
            
            query += ("MATCH (ca)-[:OF_ATTRIBUTE]->(a:Attribute) "
                      "MATCH (ca)-[:INSTANCE_OF]->(t:Trait) "
                      "WITH ca, a, t, r WHERE t.s CONTAINS $search_string OR a.s CONTAINS $search_string")
            if samples_only:
                query += " AND EXISTS {(ca)<-[:HAS_APPLICATION]-(s:Sample)} "
        else:
            if samples_only:
                if submission_tag is not None:
                    query += "WHERE EXISTS {(ca)<-[:HAS_APPLICATION]-(s:Sample)-[:HAS_SAMPLE]-(submission:Submission {tag : $submission_tag})} "
                else:
                    query += "WHERE EXISTS {(ca)<-[:HAS_APPLICATION]-(s:Sample)} "
            
            if attribute_tag is not None or trait_tag is not None:
                if not samples_only:
                    query += "WHERE "
                else:
                    query += "AND "
                    
                if attribute_tag is not None:
                    query += "(EXISTS {(ca)-[:OF_ATTRIBUTE]->(a:Attribute {tag : $attribute_tag})} OR EXISTS {(ca)-[:HAS_VALUE*0..]->(:ConditionValue)-[:OF_ATTRIBUTE]->(:Attribute {tag : $attribute_tag})}) "
                if trait_tag is not None:
                    if attribute_tag is not None:
                        query += "AND "
                    query += "(EXISTS {(ca)-[:INSTANCE_OF]->(t:Trait {tag : $trait_tag})} OR EXISTS {(ca)-[:HAS_VALUE*0..]->(:ConditionValue)-[:INSTANCE_OF]->(t:Trait {tag : $trait_tag})}) "
        
        query += "RETURN ca.tag as tag, count(r) as freq "

        if sort_by_frequency:
            query += "ORDER BY freq DESC "
        if limit is not None:
            query += "LIMIT $limit "

        r = self._driver.execute_query( query_= query, routing_="r",  search_string = search_string, submission_tag=submission_tag, attribute_tag=attribute_tag, trait_tag=trait_tag, limit = limit, result_transformer_=Result.value)

        return r
    

    