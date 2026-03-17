
from typing import List 
from neo4j import Driver, Result

from config.models.genotype import MinimalGenotypeModel, GenotypeModel, InsertGeneticApplicationModel
from config.models.attributes import AttributeTree
from config.models.conditions_applications import ConditionApplicationTreeModel
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
    
    def get_text(self, tag: str) -> str|None:
        """Returns the text of a genotype by its tag.

        Parameters
        ----------
        tag : str
            The unique genotype tag.

        Returns
        -------
        The text, if found, otherwise None.
        """
        query = (
            "MATCH (g:Genotype) "
            "WHERE g.tag = $tag "
            "RETURN g.text "
        )

        r = self._driver.execute_query(query, tag=tag, routing_="r", result_transformer_=Result.value)
        return r[0] if len(r) > 0 else None
    
    def get_description(self, tag: str) -> str | None:
        """Returns the description of a genotype by its tag.

        Parameters
        ----------
        tag : str
            The unique genotype tag.

        Returns
        -------
        str | None
            The description, if found, otherwise None.
        """
        query = (
            "MATCH (g:Genotype) "
            "WHERE g.tag = $tag "
            "RETURN g.description"
        )
        r = self._driver.execute_query(query, tag=tag, routing_="r", result_transformer_=Result.value)
        return r[0] if r else None
    
    def get_item(self, tag: str) -> dict[str, str] | None:
        """Returns combined information about a genotype (text, description).

        Parameters
        ----------
        tag : str
            The unique genotype tag.

        Returns
        -------
        dict[str, str] | None
            A dictionary with text, and description(if found), otherwise None.
        """
        query = (
            "MATCH (g:Genotype) "
            "WHERE g.tag = $tag "
            "RETURN g.text AS text, g.description AS description"
        )
        r = self._driver.execute_query(query, tag=tag, routing_="r", result_transformer_=Result.data)
        return r[0] if r else None
    
    def get_condition_applications(self, tag : str) -> List[str]:

        query = (
            "MATCH (g:Genotype)-[:HAS_APPLICATION]->(ca:ConditionApplication) "
            "WHERE g.tag = $tag "
            "RETURN ca.tag AS tag"
        )

        r = self._driver.execute_query(query, tag=tag, routing_="r", result_transformer_=Result.value)
        return r


    def get_proteins(self, tag: str) -> list[str] | None:
        """Returns the proteins affected by a genotype.

        Parameters
        ----------
        tag : str
            The unique genotype tag.

        Returns
        -------
        list[str] | None
            A list of affected protein tags, if any exist.
        """
        query = (
            "MATCH (g:Genotype)-[:EFFECTS]->(p:Protein) "
            "WHERE g.tag = $tag "
            "RETURN p.tag"
        )
        r = self._driver.execute_query(query, tag=tag, routing_="r", result_transformer_=Result.value)
        return r if r else None
    
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
            return component.type == "attribute" and component.tag == "att_protein"

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

    def edit_genotype( self, tag: str, text: str, application_tags: List[str], protein_tags: List[str], user_tag : str, description: str , publication: str | None, technical_text: str | None) -> bool:
        """Edits the existing genotype.
        """
    

        if len(protein_tags) == 0:
            raise ValueError("No feature (protein tag) found in the genotype components.")

        if text.strip() == "":
            raise ValueError("Text cannot be empty.")

        if description.strip() == "":
            raise ValueError("Description cannot be empty.")


        query = (
            "MATCH (gc:Genotype {tag : $tag}) "
            "SET gc.modified_at = timestamp(), gc.text = $text, gc.description = $description, gc.publication = $publication, gc.technical_text = $technical_text, gc.s = toLower($text)+ ' '+ toLower($description) + ' '+ toLower($technical_text) "

            "WITH gc "
            "MATCH (gc)-[oldApp:HAS_APPLICATION]->() "
            "DELETE oldApp "

            "WITH gc "
            "UNWIND $application_tags AS application_tag "
            "MATCH (comp:ConditionApplication {tag : application_tag}) "
            "MERGE (gc)-[:HAS_APPLICATION]->(comp) "

            "WITH gc "
            "MATCH (gc)-[oldEff:EFFECTS]->() "
            "DELETE oldEff "

            "WITH gc "
            "UNWIND $protein_tags AS protein_tag "
            "MATCH (p:Protein {tag : protein_tag}) "
            "MERGE (gc)-[r_effects:EFFECTS]->(p) "
            "SET r_effects.created_at = timestamp() "

            "WITH gc "
            "MATCH (u:User {tag : $user_tag}) "
            "MERGE (u)-[:MODIFIED]->(gc) "
        )


        self._driver.execute_query(query, tag = tag, text = text, application_tags = application_tags, 
                                   description = description, publication = publication, 
                                   technical_text = technical_text, user_tag = user_tag, 
                                   routing_="w", database_="neo4j", protein_tags = protein_tags)
        return True
    

    def edit(self, tag : str, data : InsertGeneticApplicationModel, user_tag : str) -> bool:
        """Edits an existing genotype in the database.

        Parameters
        ----------
        data : InsertGeneticApplicationModel
            The genotype information to be edited.
        user_tag : str
            The user who is editing the genotype.
        Returns
        -------
        bool
            True if the edit was successful, False otherwise.
        """
        genotype_tag = tag
        if not self.exists(genotype_tag):
            raise ValueError(f"Genotype with tag {genotype_tag} does not exist.")
        
        def _is_feature(component : AttributeTree) -> bool:
            return component.type == "attribute" and component.tag == "att_protein"

        def _find_protein_tag(components : List[AttributeTree]) -> str:
            t = []
            for component in components:
                print(component, _is_feature(component), len(component.children))
                if _is_feature(component) and len(component.children) > 0:
                    #the value is actually in the children 
                    t.append(component.children[0].value)
                if len(component.children) > 0: 
                    tags = _find_protein_tag(component.children)
                    if len(tags) > 0:
                        t.append(tags[0])
            if len(t) > 0:
                return t
            return []

        ex_protein_tags = [_find_protein_tag([c]) for c in data.components]
        protein_tags = [tags[0] for tags in ex_protein_tags if len(tags) > 0]
        print(protein_tags)
        if len(protein_tags) == 0:
            raise ValueError("No feature (protein tag) found in the genotype components.")
        

        tags = []
        for attribute_tree in data.components:
            tag = self._condition_applications.insert(condition_application=attribute_tree) 
            tags.append(tag)

        self.edit_genotype(tag = genotype_tag, text = data.text, application_tags=tags, user_tag=user_tag, description=data.description, publication=data.publication, technical_text=data.technical_text, 
                             protein_tags=[tag for tag in protein_tags if tag is not None])
        return True
        

    def find(self, search_string : str = None, proteome_tags : List[str] = None, limit : int = None, user_tag : str = None) -> List[str]:
        """Finds genotype tags that match the search string. 
        Returns the genotype tags that contain the search string.
        """ 
        
        if user_tag is not None:
            query = "MATCH (u:User {tag : $user_tag})-[:CREATED]->(g:Genotype)-[:EFFECTS]->(p:Protein)  "
        else:
            query = "MATCH (g:Genotype)-[:EFFECTS]->(p:Protein) "
        if proteome_tags is not None:
            query += "WHERE EXISTS {(p)<-[:IN_PROTEOME]-(proteome:Proteome) WHERE proteome.tag in proteome_tags}" 
        if search_string is not None and search_string != "":
            query += "WHERE g.s CONTAINS $query_string OR p.s CONTAINS $query_string "
        query += "RETURN DISTINCT g.tag as tag " 
        if limit is not None:
            query += " LIMIT $limit"

        r = self._driver.execute_query(query, query_string = search_string.lower() , routing_="r", result_transformer_=Result.value, limit=limit, proteome_tags = proteome_tags)
        return r
    
    def count_samples(self, tag) -> int:
        """Counts the number of relationships associated with a genotype.

        Parameters
        ----------
        tag : str
            The unique genotype tag.

        Returns
        -------
        int
            The number of relationships (samples linked to the genotype).
        """

        query = (
        "MATCH (g:Genotype {tag: $tag})-[r]->(s:Sample) "
        "RETURN count(r) AS count"
    )
        r = self._driver.execute_query(query, tag=tag, routing_="r", result_transformer_=Result.value)
        return r if r else None


    def delete(self, tag) -> bool:
        """Detach and delete a genotype by its tag.

        Parameters
        ----------
        tag : str
            The genotype tag to delete.

        Returns
        -------
        bool
            True if deleted successfully, False otherwise.
        """
        if not self.exists(tag): False

        query = (
            "MATCH (g:Genotype) WHERE g.tag = $tag "
            "DETACH DELETE g "
        )
        try:
            r = self._driver.execute_query(query, routing_="w", tag = tag)
        except:
            False
        return True
    
    def condition_applications(self, tag : str) -> List[str]:
        """Gets the condition applications associated with the genotype.

        Parameters
        ----------
        tag : str
            The genotype tag.

        Returns
        -------
        List[str]
            A list of condition application tags associated with the genotype.
        """

        query = (
            "MATCH (g:Genotype)-[:HAS_APPLICATION]->(ca:ConditionApplication) "
            "WHERE g.tag = $tag "
            "RETURN ca.tag AS tag"
        )

        r = self._driver.execute_query(query, tag=tag, routing_="r", result_transformer_=Result.value)
        return r
    
    def condition_application_data(self, tag : str) -> List[ConditionApplicationTreeModel]:
        """Gets the condition application data associated with the genotype.

        Parameters
        ----------
        tag : str
            The genotype tag.

        Returns
        -------
        List[ConditionApplicationTreeModel]
            A list of condition application tree models associated with the genotype.
        """

        query = (
            "MATCH (g:Genotype)-[:HAS_APPLICATION]->(ca:ConditionApplication) "
            "WHERE g.tag = $tag "
            "RETURN ca"
        )

        ca_tags = self._driver.execute_query(query, tag=tag, routing_="r", result_transformer_=Result.value)
        return [self._condition_applications.get_tree(tag=ca_tag) for ca_tag in ca_tags]
