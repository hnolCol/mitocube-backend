
from typing import List 
from neo4j import Driver

from config.models.genotype import MinimalGenotypeModel, GenotypeModel 

from lib.data.database.abstract.Genotypes import GenotypeABC

class Neo4JGenotype(GenotypeABC):
    """
    Database class  that handles the genotypes. """
    
    def __init__(self, driver : Driver) -> None:

        self._driver = driver 
        
        
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
        
        
    def get(self, tags : List[str] = None, proteome_tags : List[str] = None, protein_tags : List[str] = None) -> List[MinimalGenotypeModel]:
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
        
        if tags is not None:
            
            query = (
                 "MATCH (g:Genotype) "
                 "WHERE g.tag in $tags "
            )
        
        elif protein_tags is not None and proteome_tags is not None:
            query = (
                "MATCH (g:Genotype)-[:EFFECTS]->(p:Protein) "
                "WHERE p.tag in $protein_tags AND g.proteome_tag in $proteome_tags "
            )
        elif protein_tags is None and proteome_tags is not None:
            query = (
                "MATCH (g:Genotype) "
                "WHERE g.proteome_tag in $proteome_tags "
            )
        elif protein_tags is not None and proteome_tags is None:
            #since protein_tags are proteome_id specific this is actually not very logical
            query = (
                "MATCH (g:Genotype)-[:EFFECTS]->(p:Protein) "
                "WHERE p.tag in $protein_tags "
            )
        else:
            query = ("MATCH (g:Genotype) ")
        
        query += "RETURN g.tag as tag, g.text as text, g.proteome_tag as proteome_tag "

        r, _, _ = self._driver.execute_query(query, 
                                             tags = tags,
                                             proteome_tags = proteome_tags, 
                                             protein_tags = protein_tags, 
                                             routing_="r", 
                                             database_="neo4j")
        return [MinimalGenotypeModel(**ri.data()) for ri in r]
    
        
    def find(self, query : str) -> List[MinimalGenotypeModel]:
        query_string = query.lower() 
        query = (
            "MATCH (g:Genotype) "
            "WHERE g.s CONTAINS $query_string "
            "RETURN g.tag as tag, g.text as text, g.proteome_tag as proteome_tag"
        )
        
        r, _ , _= self._driver.execute_query(query, query_string = query_string, routing_="r", database_="neo4j")
        return [MinimalGenotypeModel(**ri.data()) for ri in r]