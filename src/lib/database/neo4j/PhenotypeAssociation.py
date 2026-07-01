from neo4j import Driver, Result
from typing import List
from lib.database.abstract.PhenotypeAssociation import PhenotypeAssociationABC
from lib.database.abstract.ConditionApplications import ConditionApplicationABC
from lib.database.abstract.Genotypes import GenotypeABC
from config.models.PhenotypeAssociation import PhenotypeAssociationModel, PhenotypeAssociationInputModel, PhenotypeAssociationFullInsertModel
from config.models.attributes import AttributeTree
from services.random_generators import get_random_string


class Neo4jPhenotypeAssociations(PhenotypeAssociationABC):

    def __init__(self, driver: Driver, condition_applications: ConditionApplicationABC, genotypes: GenotypeABC) -> None:
        self._driver = driver
        self._condition_applications = condition_applications
        self._genotypes = genotypes

    def _insert_condition_applications(self, pa_tag: str, sample_data: List[AttributeTree]):
        """Insert condition applications for a phenotype association.

        Parameters
        ----------
        pa_tag : str
            The tag of the phenotype association.
        sample_data : List[AttributeTree]
            The condition application tree to insert.
        """
        ts = []
        for attribute_tree in sample_data:
            for c in attribute_tree.children:
                updated_tree = AttributeTree(
                    tag=attribute_tree.tag,
                    type=attribute_tree.type,
                    value=attribute_tree.value,
                    children=[c]
                )
                tag = self._condition_applications.insert(condition_application=updated_tree)
                ts.append(tag)

        query = (
            "MATCH (pa:PhenotypeAssociation {tag: $pa_tag}) "
            "MATCH (ca:ConditionApplication) "
            "WHERE ca.tag IN $tags "
            "MERGE (pa)-[r:HAS_APPLICATION]->(ca) "
            "SET r.created_at = timestamp() "
        )
        self._driver.execute_query(query, routing_="w", pa_tag=pa_tag, tags=ts)

    def count(self) -> int:
        "Returns the total number of phenotype associations in the database."
        query = (
            "MATCH (pa:PhenotypeAssociation) "
            "RETURN count(pa) "
        )
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value)
        return r[0] if r else 0

    def exists(self, tag: str) -> bool:
        "Checks if a phenotype association with the given tag exists."
        query = (
            "WITH EXISTS {(pa:PhenotypeAssociation {tag: $tag})} AS association_exists "
            "RETURN association_exists "
        )
        r = self._driver.execute_query(query, tag=tag, routing_="r", result_transformer_=Result.value)
        return r[0] if r else False

    def insert(self, data: PhenotypeAssociationFullInsertModel, user_tag: str) -> str:
        "Insert a new phenotype association."
        tag = get_random_string(5)

        query = (
            "MERGE (pa:PhenotypeAssociation {tag: $tag}) "
            "ON CREATE SET "
            "  pa.created_at = timestamp(), "
            "  pa.is_active = true, "
            "  pa.description = $description, "
            "  pa.observation_notes = $observation_notes, "
            "  pa.att_protein_mutation = $att_protein_mutation, "
            "  pa.publication = $publication "
            "WITH pa "
            "MATCH (ph:Phenotype {tag: $phenotype_tag}) "
            "MERGE (ph)<-[:OBSERVED_IN]-(pa) "
            "WITH pa "
            "MATCH (u:User {tag: $user_tag}) "
            "MERGE (u)-[:CREATED {created_at: timestamp()}]->(pa) "
        )
        self._driver.execute_query(
            query,
            tag=tag,
            description=data.description,
            observation_notes=data.observation_notes,
            att_protein_mutation=data.att_protein_mutation,
            publication=data.publication,
            phenotype_tag=data.phenotype_tag,
            user_tag=user_tag,
            routing_="w",
            database_="neo4j"
        )

        if data.protein_tag:
            self._driver.execute_query(
                "MATCH (pa:PhenotypeAssociation {tag: $tag}) "
                "MATCH (p:Protein {tag: $protein_tag}) "
                "MERGE (pa)-[:MAY_INVOLVE]->(p) ",
                tag=tag, protein_tag=data.protein_tag,
                routing_="w", database_="neo4j"
            )

        if data.disease_tag:
            self._driver.execute_query(
                "MATCH (pa:PhenotypeAssociation {tag: $tag}) "
                "MATCH (d:Disease {tag: $disease_tag}) "
                "MERGE (pa)-[:ASSOCIATED_WITH]->(d) ",
                tag=tag, disease_tag=data.disease_tag,
                routing_="w", database_="neo4j"
            )

        if data.variant_tag:
            self._driver.execute_query(
                "MATCH (pa:PhenotypeAssociation {tag: $tag}) "
                "MATCH (v:Variant {tag: $variant_tag}) "
                "MERGE (pa)-[:LINKED_TO_VARIANT]->(v) ",
                tag=tag, variant_tag=data.variant_tag,
                routing_="w", database_="neo4j"
            )

        # resolve genotype_tag 
        genotype_tag = data.genotype_tag
        if genotype_tag is None and data.genotype is not None:
            self._genotypes.insert(data=data.genotype, user_tag=user_tag)
            from services.encryption import create_hierarchical_hash
            genotype_tag = create_hierarchical_hash(
                [c.model_dump() for c in data.genotype.components]
            )

        if genotype_tag:
            self._driver.execute_query(
                "MATCH (pa:PhenotypeAssociation {tag: $tag}) "
                "MATCH (g:Genotype {tag: $genotype_tag}) "
                "MERGE (pa)-[:HAS_GENOTYPE]->(g) ",
                tag=tag, genotype_tag=genotype_tag,
                routing_="w", database_="neo4j"
            )

        if data.condition_applications:
            self._insert_condition_applications(tag, data.condition_applications)

        return tag

    def get(self, tag: str) -> PhenotypeAssociationModel | None:
        "Returns a phenotype association by tag."
        query = (
            "MATCH (pa:PhenotypeAssociation {tag: $tag}) "
            "OPTIONAL MATCH (ph:Phenotype)<-[:OBSERVED_IN]-(pa) "
            "OPTIONAL MATCH (pa)-[:ASSOCIATED_WITH]->(d:Disease) "
            "OPTIONAL MATCH (pa)-[:MAY_INVOLVE]->(p:Protein) "
            "OPTIONAL MATCH (pa)-[:LINKED_TO_VARIANT]->(v:Variant) "
            "OPTIONAL MATCH (pa)-[:HAS_GENOTYPE]->(g:Genotype) "
            "RETURN pa.tag AS tag, "
            "       pa.description AS description, "
            "       pa.observation_notes AS observation_notes, "
            "       pa.att_protein_mutation AS att_protein_mutation, "
            "       pa.publication AS publication, "
            "       pa.created_at AS created_at, "
            "       ph.tag AS phenotype_tag, "
            "       d.tag AS disease_tag, "
            "       p.tag AS protein_tag, "
            "       v.tag AS variant_tag, "
            "       g.tag AS genotype_tag "
        )
        r = self._driver.execute_query(query, tag=tag, routing_="r", result_transformer_=Result.data)
        return PhenotypeAssociationModel(**r[0]) if r else None

    def find(self, query: str = "", limit: int = 20) -> List[str]:
        "Search phenotype associations by description."
        cypher = "MATCH (pa:PhenotypeAssociation) WHERE pa.is_active = true "
        if query:
            cypher += "AND pa.description CONTAINS $query "
        cypher += "RETURN pa.tag LIMIT $limit"
        r = self._driver.execute_query(
            cypher, query=query.lower(), limit=limit,
            routing_="r", result_transformer_=Result.value
        )
        return r

    def find_by_phenotype(self, phenotype_tag: str, limit: int = 20) -> List[str]:
        "Returns phenotype association tags linked to a given phenotype."
        query = (
            "MATCH (ph:Phenotype {tag: $phenotype_tag})<-[:OBSERVED_IN]-(pa:PhenotypeAssociation) "
            "WHERE pa.is_active = true "
            "RETURN pa.tag LIMIT $limit"
        )
        r = self._driver.execute_query(
            query,
            phenotype_tag=phenotype_tag, limit=limit,
            routing_="r", result_transformer_=Result.value
        )
        return r

    def find_by_disease(self, disease_tag: str, limit: int = 20) -> List[str]:
        "Returns phenotype association tags linked to a given disease."
        query = (
            "MATCH (pa:PhenotypeAssociation)-[:ASSOCIATED_WITH]->(d:Disease {tag: $disease_tag}) "
            "WHERE pa.is_active = true "
            "RETURN pa.tag LIMIT $limit"
        )
        r = self._driver.execute_query(
            query,
            disease_tag=disease_tag, limit=limit,
            routing_="r", result_transformer_=Result.value
        )
        return r

    def find_by_protein(self, protein_tag: str, limit: int = 20) -> List[str]:
        "Returns phenotype association tags linked to a given protein."
        query = (
            "MATCH (pa:PhenotypeAssociation)-[:MAY_INVOLVE]->(p:Protein {tag: $protein_tag}) "
            "WHERE pa.is_active = true "
            "RETURN pa.tag LIMIT $limit",
        )
        r = self._driver.execute_query(
            query,
            protein_tag=protein_tag, limit=limit,
            routing_="r", result_transformer_=Result.value
        )
        return r

    def find_by_genotype(self, genotype_tag: str, limit: int = 20) -> List[str]:
        "Returns phenotype association tags linked to a given genotype."
        query =(
            "MATCH (pa:PhenotypeAssociation)-[:HAS_GENOTYPE]->(g:Genotype {tag: $genotype_tag}) "
            "WHERE pa.is_active = true "
            "RETURN pa.tag LIMIT $limit",
        )
        r = self._driver.execute_query(
            query,
            genotype_tag=genotype_tag, limit=limit,
            routing_="r", result_transformer_=Result.value
        )
        return r

    def delete(self, tag: str, is_active: bool = False) -> bool:
        "Soft delete a phenotype association by setting is_active."
        query = (
            "MATCH (pa:PhenotypeAssociation {tag: $tag}) "
            "SET pa.is_active = $is_active "
            "RETURN true AS ok",
        )
        r = self._driver.execute_query(
            query,
            tag=tag, is_active=is_active,
            routing_="w", result_transformer_=Result.value
        )
        return bool(r)