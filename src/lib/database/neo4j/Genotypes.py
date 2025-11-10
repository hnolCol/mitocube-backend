
from typing import List 
from neo4j import Driver, Result

from config.models.genotype import MinimalGenotypeModel, GenotypeModel, InsertGeneticApplicationModel
from config.models.attributes import AttributeTree
from lib.database.abstract.Genotypes import GenotypeABC
from lib.database.abstract.ConditionApplications import ConditionApplicationABC
from services.encryption import create_hierarchical_hash
import uuid
class Neo4JGenotype(GenotypeABC):
    """
    Database class  that handles the genotypes. """
    
    def __init__(self, driver : Driver, condition_applications : ConditionApplicationABC) -> None:

        self._driver = driver
        self._condition_applications = condition_applications
        
        
    def _add(self, genotypes : List[GenotypeModel], user_tag : str = None):
        
        def extract_genotype_attributes(genotype_attributes):
            ""
            gen_attrs = []
            n = 0
            for attribute in genotype_attributes:
                #there might be multiple protein mutations
                for idx in range(len(attribute["att_protein_mutation"])):
                    gen_attrs.append({})
                    mutation_tag = attribute["att_protein_mutation"][idx].tag
                    position_of_mutation = attribute["att_protein_position"][mutation_tag]
                    gen_attrs[n]["protein_tag"] = attribute["att_protein_coding_sequence"][0].key
                    gen_attrs[n]["engineering_tag"] = attribute["att_gene_engineering"][0].tag
                    gen_attrs[n]["method_tag"] = attribute["att_gene_editing_method"][0].tag
                    gen_attrs[n]["mutation_tag"] = mutation_tag
                    gen_attrs[n]["position_tag"] = position_of_mutation.attribute_value.tag
                    gen_attrs[n]["aa_position"] = position_of_mutation.aa_position
                    gen_attrs[n]["aa"] = position_of_mutation.aa
                    gen_attrs[n]["substitution"] = position_of_mutation.substitution
                    n += 1
            return gen_attrs
                
            
        genotype_props = [{"tag" : genotype.label, 
                           "proteome_tag" : genotype.proteome_tag, 
                           "text" : genotype.text, 
                           "attributes" : extract_genotype_attributes(genotype.attributes)} for genotype in genotypes if "att_protein_mutation" in genotype.attributes[0] and "att_protein_position" in genotype.attributes[0]]

        query = (
            "UNWIND $genotypes as genotype "
            "MERGE (g:Genotype {tag : genotype.tag}) "
            "ON CREATE "
            "SET g.created_at = timestamp(), g.text = genotype.text, g.proteome_tag = genotype.proteome_tag "
            "ON MATCH "
            "SET g.modified_at = timestamp(), g.text = genotype.text, g.proteome_tag = genotype.proteome_tag "
            "WITH g, genotype "
            "UNWIND genotype.attributes as attribute "
            "MATCH (p:Protein {tag : attribute.protein_tag}) "
            "SET g.s = toLower(genotype.text)+' '+p.s "
            "WITH g,p,genotype, attribute "
            "MERGE (g)-[effect_r:EFFECTS {tag : genotype.tag}]->(p) "
            "SET effect_r.created_at = timestamp() "
            "WITH attribute,p,genotype,g "
            "MATCH (engineer_attribute:AttributeValue {tag : attribute.engineering_tag}) "
            "MATCH (method_attribute:AttributeValue {tag : attribute.method_tag}) "
            "MATCH (prot_mutation_attribute:AttributeValue {tag : attribute.mutation_tag}) "
            "MATCH (position_attribute:AttributeValue {tag : attribute.position_tag}) "
            "MERGE (method_attribute)<-[:MEDIATED_BY {tag : genotype.tag}]-(engineer_attribute) "
            "MERGE (method_attribute)-[:MODIFYING {tag : genotype.tag}]-(p) "
            "MERGE (p)-[:INTRODUCING {tag : genotype.tag}]-(prot_mutation_attribute) "
            "MERGE (prot_mutation_attribute)-[at_r:AT {tag : genotype.tag}]->(position_attribute) "
            "SET at_r.position = attribute.aa_position, at_r.amino_acids = attribute.aa, at_r.substitution = attribute.substitution "
            )
        
        if user_tag is not None:
            query += ("WITH g "
                      "MATCH (u:User {tag : $user_tag}) "
                      "MERGE (u)-[r_defined:DEFINED {tag : g.tag}]->(g) "
                      "ON CREATE "
                      "SET r_defined.created_at = timestamp() "
            )
        
        self._driver.execute_query(query, genotypes = genotype_props, user_tag = user_tag, routing_="w",  database_="neo4j")
        
    def exists(self, tag : str) -> bool:
        "Checks if a genotype with the given tag exists in the database."
        query = (
            "WITH EXISTS {MATCH (g:Genotype) WHERE g.tag = $tag} AS genotype_exists "
            "RETURN genotype_exists"
        )
        
        r = self._driver.execute_query(query, tag = tag, result_transformer_=Result.value)
        return r[0]

    def component_exists(self, tag : str) -> bool:
        "Checks if a genotype component with the given tag exists in the database."
        query = (
            "WITH EXISTS {MATCH (gc:GenotypeComponent) WHERE gc.tag = $tag} AS genotype_component_exists "
            "RETURN genotype_component_exists"
        )   
        r = self._driver.execute_query(query, tag = tag, result_transformer_=Result.value)
        return r[0]

    def add_genotypes(self, genotypes : List[GenotypeModel], user_tag : str = None):
        """Adds multiple genotypes into the database. 

        Parameters
        ----------
        genotypes : List[GenotypeModel]
            _description_
        user_tag : str, optional
            _description_, by default None
        """
        self._add(genotypes, user_tag=user_tag)
        
        
    def add(self, genotype : GenotypeModel, user_tag : str):
        """Adss a genotype to the database. 

        Parameters
        ----------
        genotype : GenotypeModel
            _description_
        user_tag : str
            _description_
        """
        self._add([genotype], user_tag = user_tag)
        
        
    def get(self, tag : str) -> MinimalGenotypeModel:
        """Returns the genotypes by the tags. 
        If tag is None (default) all genotypes will be returned. 

        Parameters
        ----------
        tags : List[str], optional
            The list of genotype tags that should be returned, by default None
        proteome_tags : List[str], optional
            The proteome_ids to consider when return the genotype, by default None
        protein_tags : List[str], optional
            The protein tags (Uniprot IDs). Provide a list of tags to get 
            all the genotypes that effect the given gene coding sequence, by default None

        Returns
        -------
        List[MinimalGenotypeModel]
            _description_
        """
        
        query = (
            "MATCH (g:Genotype) "
            "WHERE g.tag = $tag "
            "RETURN g.tag as tag, g.text as text, g.proteome_tag as proteome_tag"
        )
        
        r = self._driver.execute_query(query, tag = tag, routing_="r", result_transformer_=Result.value)
        return MinimalGenotypeModel(**r[0].data()) if r.size() > 0 else None
    
        
    def insert_genotype(self, tag : str,  text : str, protein_tags : List[str], application_tags : List[str], user_tag : str, description : str|None, publication : str|None, technical_text : str|None) -> bool:
        """Inserts a new genotype into the database.
        Parameters
        ----------
        tag : str
            _description_
        text : str
            _description_
        application_tags : List[str]
            The tags the genotype is connected to. 
        description : str|None
        """
        query = (
            "MERGE (gc:Genotype {tag : $tag}) "
            "ON CREATE "
            "SET gc.created_at = timestamp(), gc.text = $text, gc.description = $description, gc.publication = $publication, gc.technical_text = $technical_text, gc.s = toLower($text)+ ' '+ toLower($description) + ' '+ toLower($technical_text) "
            "ON MATCH "
            "SET gc.modified_at = timestamp(), gc.text = $text, gc.description = $description, gc.publication = $publication, gc.technical_text = $technical_text, gc.s = toLower($text)+ ' '+ toLower($description) + ' '+ toLower($technical_text) "
            "WITH gc "
            "MATCH (u:User {tag : $user_tag}) "
            "MERGE (u)-[r_defined:CREATED {tag : gc.tag}]->(gc) "
            "WITH gc "
            "UNWIND $application_tags as application_tag "
            "MATCH (comp:ConditionApplication {tag : application_tag}) "
            "MERGE (gc)-[r:HAS_APPLICATION]->(comp) "
            "WITH gc "
            "UNWIND $protein_tags as protein_tag "
            "MATCH (p:Protein {tag : protein_tag}) "
            "MERGE (gc)-[r_effects:EFFECTS {tag : gc.tag}]->(p) "
            "SET r_effects.created_at = timestamp() "
        )

        self._driver.execute_query(query, tag = tag, text = text, user_tag = user_tag, application_tags = application_tags, description = description, publication = publication, technical_text = technical_text, routing_="w", database_="neo4j", protein_tags = protein_tags)
        return True

    def insert(self, data : InsertGeneticApplicationModel, user_tag : str) -> bool:
        """Inserts a new genotype into the database.

        Parameters
        ----------
        data : InsertGeneticApplicationModel
            The genotype information to be inserted.
        user_tag : str
            The user who is inserting the genotype.
        Returns
        -------
        bool
            True if the insertion was successful, False otherwise.
        """
        def _is_feature(component : AttributeTree) -> bool:
            return component.type == "attribute" and component.tag == "att_feature"

        def _find_protein_tag(components : List[AttributeTree]) -> str:
            
            for component in components:
                if _is_feature(component) and len(component.children) > 0:
                    #the value is actually in the children 
                    return component.children[0].value
                if len(component.children) > 0:
                    return _find_protein_tag(component.children)

            return None 

        protein_tags = [_find_protein_tag([c]) for c in data.components]
        if len(protein_tags) == 0:
            raise ValueError("No feature (protein tag) found in the genotype components.")
        genotype_tag = create_hierarchical_hash([d.model_dump() for d in data.components])
        if self.exists(genotype_tag):
            return False

        tags = []
        for attribute_tree in data.components:
            tag = self._condition_applications.insert(condition_application=attribute_tree) 
            tags.append(tag)

        self.insert_genotype(tag = genotype_tag, text = data.text, application_tags=tags, user_tag=user_tag, description=data.description, publication=data.publication, technical_text=data.technical_text, 
                             protein_tags=[tag for tag in protein_tags if tag is not None])
        return True
    
    
    def find(self, search_string : str = None, limit : int = None, user_tag : str = None) -> List[str]:
        """Finds genotype tags that match the search string. 
        Returns the genotype tags that contain the search string.
        """ 
        
        if user_tag is not None:
            query = "MATCH (u:User {tag : $user_tag})-[:CREATED]->(g:Genotype)-[:EFFECTS]->(p:Protein)  "
        else:
            query = "MATCH (g:Genotype)-[:EFFECTS]->(p:Protein) " 
        if search_string is not None and search_string != "":
            query += "WHERE g.s CONTAINS $query_string OR p.s CONTAINS $query_string "
        query += "RETURN DISTINCT g.tag as tag " 
        if limit is not None:
            query += " LIMIT $limit"

        r = self._driver.execute_query(query, query_string = search_string.lower() , routing_="r", result_transformer_=Result.value, limit=limit)
        return r