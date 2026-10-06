from __future__ import annotations
from typing import List, Dict, Optional
from neo4j import Driver, Result
import pandas as pd
from lib.database.abstract.PTMSites import PTMSitesABC
from lib.database.abstract.Samples import SamplesABC
from config.models.ptms import PTMSiteInsertModel, PTMSiteResponseModel


class Neo4JPTMSites(PTMSitesABC):

    def __init__(self, driver : Driver, samples : SamplesABC) -> None:
        self._driver = driver
        self._samples = samples


    def exists(self, tag : str) -> bool:
        query = (
            "MATCH (ptm:PTMSite {tag : $tag}) "
            "RETURN count(ptm) > 0 as exists "
        )
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value, tag = tag)
        return r.records[0]


    def count(self, submission_tag : str = None) -> int:
        if submission_tag is not None:
            query = (
                "MATCH (s:Submission {tag : $submission_tag})-[:HAS_SAMPLE]->(:Sample)-[:QUANTIFIED]->(ptm:PTMSite) "
                "RETURN count(DISTINCT ptm) as count "
            )
            r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value, submission_tag = submission_tag)
            return r.records[0]
        query = (
            "MATCH (ptm:PTMSite) "
            "RETURN count(ptm) as count "
        )
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value)
        return r.records[0]


    def find(self, search_string : str, submission_tag : str = None, limit : int = None) -> List[str]:
        query = "MATCH (ptm:PTMSite) WHERE ptm.tag CONTAINS $search_string "
        if submission_tag is not None:
            query += "AND EXISTS {(ptm)<-[:QUANTIFIED]-(:Sample)<-[:HAS_SAMPLE]-(:Submission {tag : $submission_tag})} "
        query += "RETURN ptm.tag as tag ORDER BY ptm.tag "
        if limit is not None:
            query += "LIMIT $limit "
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value,
                                       search_string = search_string, submission_tag = submission_tag, limit = limit)
        return [record["tag"] for record in r.records]


    def get(self, tag : str) -> PTMSiteResponseModel:
        query = (
            "MATCH (ptm:PTMSite {tag : $tag})-[:OF_PROTEIN_GROUP]->(pg:ProteinGroup) "
            "OPTIONAL MATCH (ptm)-[:SUPPORTED_BY]->(pre:Precursor) "
            "WITH ptm, pg, collect(pre.tag) as precursor_tags "
            "RETURN ptm.tag as tag, pg.tag as protein_group_tag, ptm.protein_tag as protein_tag, "
            "ptm.position as position, ptm.modification as modification, ptm.residue as residue, "
            "precursor_tags, "
            "EXISTS {(ptm)<-[:QUANTIFIED]-(:Sample)} as quantified "
        )
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.data, tag = tag)
        if not r:
            raise ValueError(f"PTM site with tag {tag} not found.")
        data = dict(r[0])
        data["precursor_tags"] = data.pop("precursor_tags", [])
        return PTMSiteResponseModel(**data)


    def insert(self, ptm_site : PTMSiteInsertModel) -> bool:
        props = ptm_site.model_dump(exclude_none=True, exclude=["precursor_tags", "value", "score", "site_localization"])
        query = (
            "MERGE (ptm:PTMSite {tag : $props.tag}) "
            "SET ptm += $props, ptm.created_at = timestamp() "
            "WITH ptm "
            "MATCH (pg:ProteinGroup {tag : $props.protein_group_tag}) "
            "MERGE (ptm)-[r_pg:OF_PROTEIN_GROUP]->(pg) "
            "SET r_pg.created_at = timestamp() "
            "WITH ptm "
            "UNWIND $precursor_tags as precursor_tag "
            "MATCH (pre:Precursor {tag : precursor_tag}) "
            "MERGE (ptm)-[r_sup:SUPPORTED_BY]->(pre) "
            "SET r_sup.created_at = timestamp() "
        )
        self._driver.execute_query(query, routing_="w", result_transformer_=Result.value,
                                   props = props, precursor_tags = ptm_site.precursor_tags)
        return True 


    def bulk_insert(self, ptm_sites : List[PTMSiteInsertModel], batch_size : int = 1000, transaction_batch_size : int = 400) -> int:
        total = 0
        sites_data = [s.model_dump(exclude_none=True) for s in ptm_sites]
        query = f"""
        CALL () {{
            UNWIND $ptm_sites as site
            MERGE (ptm:PTMSite {{tag: site.tag}})
            SET ptm += site, ptm.created_at = timestamp()
            WITH ptm, site
            MATCH (pg:ProteinGroup {{tag: site.protein_group_tag}})
            MERGE (ptm)-[r_pg:OF_PROTEIN_GROUP]->(pg)
            SET r_pg.created_at = timestamp()
            WITH ptm, site
            UNWIND site.precursor_tags as precursor_tag
            MATCH (pre:Precursor {{tag: precursor_tag}})
            MERGE (ptm)-[r_sup:SUPPORTED_BY]->(pre)
            SET r_sup.created_at = timestamp()
            RETURN count(r_sup) AS created
        }} IN TRANSACTIONS OF {transaction_batch_size} ROWS
        RETURN sum(created) AS total
        """
        with self._driver.session() as session:
            for i in range(0, len(sites_data), batch_size):
                batch = sites_data[i:i+batch_size]
                r = session.run(query, ptm_sites = batch)
                record = r.single()
                if record and record["total"] is not None:
                    total += record["total"]
        return total


    def is_quantified(self, tag : str) -> bool:
        query = (
            "MATCH (ptm:PTMSite {tag : $tag}) "
            "RETURN EXISTS {(ptm)<-[:QUANTIFIED]-(:Sample)} as quantified "
        )
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value, tag = tag)
        return r.records[0]


    def get_abundance(self, tag : str, submission_tags : List[str] = None) -> pd.DataFrame:
        query = (
            "MATCH (ptm:PTMSite {tag : $tag})<-[r:QUANTIFIED]-(sample:Sample) "
        )
        if submission_tags is not None:
            query += "WHERE EXISTS {(sample)<-[:HAS_SAMPLE]-(:Submission {tag IN $submission_tags})} "
        query += (
            "RETURN sample.tag as sample_tag, r.value as value, r.score as score, "
            "r.site_localization as site_localization "
        )
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.data,
                                       tag = tag, submission_tags = submission_tags)
        return pd.DataFrame(r)


    def insert_quantification_data_from_df(self, submission_tag : str, sample_tag : str, quantification_data : pd.DataFrame) -> int:
        if not all(column in quantification_data.columns for column in ['tag', 'value']):
            raise ValueError("DataFrame must contain 'tag' and 'value' columns.")
        quantification_data = quantification_data.dropna(subset=['tag', 'value'])
        if quantification_data.empty:
            return 0
        if not self._samples.exists(tag=sample_tag):
            raise ValueError(f"Sample with tag {sample_tag} does not exist.")
        sample_tag = self._samples._get_sample_tag(sample_tag, submission_tag)
        if not self._samples.exists(tag=sample_tag):
            raise ValueError(f"Sample with tag {sample_tag} does not exist.")
        query = (
            "MATCH (s:Submission {tag: $submission_tag})-[:HAS_SAMPLE]->(sample:Sample {tag: $sample_tag}) "
            "UNWIND $quantification_data as data "
            "MATCH (ptm:PTMSite {tag: data.tag}) "
            "MERGE (ptm)<-[r:QUANTIFIED]-(sample) "
            "SET r.value = data.value, r.created_at = timestamp(), r.score = data.score, r.site_localization = data.site_localization "
            "RETURN COUNT(r)"
        )
        r = self._driver.execute_query(query,
                                       submission_tag=submission_tag,
                                       sample_tag=sample_tag,
                                       quantification_data=quantification_data.to_dict(orient="records"),
                                       routing_="w",
                                       result_transformer_=Result.value)
        return r[0] if len(r) > 0 else 0
