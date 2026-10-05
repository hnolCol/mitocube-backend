from typing import List, Tuple, Literal
from neo4j import Driver, Result
from lib.database.abstract.QC import QCABC
from config.models.performance import QCRunInsertModel, QCRunResponseModel, QCStandardInsertModel, QCStandardResponseModel, QCPrecursorInsertModel, QCPrecursorResponseModel


class Neo4JQC(QCABC):
    
    def __init__(self, driver : Driver) -> None:
        self._driver = driver 


    def exists(self, tag: str) -> bool:
        """
        Checks if a tag is associated with a QC run.
        """
        query = (
            "MATCH (qc:QCRun {tag : $tag}) "
            "RETURN count(qc) > 0 as exists "
        )
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value, tag = tag)
        return r.records[0]


    def count(self, by_instrument: bool = False) -> int | List[Tuple[str,int]]:
        """
        Counts the number of QC runs, optionally grouped by instrument.
        """
        if by_instrument:
            query = (
                "MATCH (qc:QCRun)-[:QUALITY_CHECKED]->(ms:AttributeValue) "
                "RETURN ms.tag as instrument, count(qc) as count "
            )
            r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value)
            return [(record["instrument"], record["count"]) for record in r.records]
        query = (
            "MATCH (qc:QCRun) "
            "RETURN count(qc) as count "
        )
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value)
        return r.records[0]


    def get(self, tags : List[str] = None, instrument_name_tag : str = None, qc_standard_tag : str = None, limit : int = 50) -> List[QCRunResponseModel]:
        """
        Returns the QC runs, optionally filtered by tags, instrument and QC standard.
        """
        query = "MATCH (qc:QCRun) "
        where = []
        if tags is not None:
            where.append("qc.tag IN $tags")
        if instrument_name_tag is not None:
            where.append("(qc)-[:QUALITY_CHECKED]->(:AttributeValue {tag : $instrument_name_tag})")
        if qc_standard_tag is not None:
            where.append("(qc)-[:USED_STANDARD]->(:QCStandard {tag : $qc_standard_tag})")
        if where:
            query += "WHERE " + " AND ".join(where) + " "
        query += (
            "OPTIONAL MATCH (qc)-[:USED_STANDARD]->(std:QCStandard) "
            "RETURN qc{.*, qc_standard_tag : std.tag} as run "
            "ORDER BY qc.tag "
            "LIMIT $limit "
        )
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value,
                                       tags = tags, instrument_name_tag = instrument_name_tag,
                                       qc_standard_tag = qc_standard_tag, limit = limit)
        runs = []
        for record in r.records:
            run = record["run"]
            run.pop("rt_peptides", None)
            run.pop("group_attr", None)
            run.pop("qc_precursors", None)
            runs.append(QCRunResponseModel.model_construct(**run))
        return runs


    def insert(self, performance_run : QCRunInsertModel) -> bool:
        """
        Adds a new QC run to the database. The run is linked to the instrument it was
        acquired on, the LC parts (via the group attributes) and the QC standard that
        was used to generate it.
        """
        attribute_values  = [{"tag" : a_tag, "value" : av_tag} for a_tag, av_tags in performance_run.group_attr.items() for av_tag in av_tags]
        peptides = [{'tag' : peptide_tag, 'rt' : rt} for peptide_tag, rt in performance_run.rt_peptides.items()]
        precursors = [{'tag' : p.precursor_tag, 'intensity' : p.intensity, 'score' : p.score, 'retention_time' : p.retention_time} for p in performance_run.qc_precursors]
        query = (
            "MERGE (qc:QCRun {tag : $performance_run_props.tag}) "
            "SET qc += $performance_run_props "
            "SET qc.created_at = timestamp() "
            "WITH qc "
            "MATCH (a:Attribute {tag: 'att_ms_name'})-[:HAS_VALUE]->(ms_instrument:AttributeValue) "
            "WHERE ms_instrument.tag = $performance_run_props.instrument_name_tag "
            "MERGE (ms_instrument)<-[:QUALITY_CHECKED]-(qc) "
            "WITH qc "
            "MATCH (std:QCStandard {tag : $performance_run_props.qc_standard_tag}) "
            "MERGE (qc)-[:USED_STANDARD]->(std) "
            "WITH qc "
            "UNWIND $attribute_values as attribute_value "
            "MATCH (a:Attribute {tag : attribute_value.tag})-[:HAS_VALUE]->(lc_part:AttributeValue {tag : attribute_value.value}) "
            "MERGE (lc_part)<-[r:LC_MS_SYSTEM]-(qc) "
            "WITH qc "
            "UNWIND $peptides as peptide "
            "MERGE (pep:Peptide {tag : peptide.tag}) "
            "MERGE (pep)<-[r_rt:RT_CHECK]-(qc) "
            "SET r_rt.rt = peptide.rt, r_rt.created_at = timestamp() "
            "WITH qc "
            "UNWIND $precursors as precursor "
            "MATCH (pre:Precursor {tag : precursor.tag}) "
            "MERGE (qc)-[r_pre:QUANTIFIED]->(pre) "
            "SET r_pre.intensity = precursor.intensity, r_pre.score = precursor.score, "
            "r_pre.retention_time = precursor.retention_time, r_pre.created_at = timestamp() "
        )
        self._driver.execute_query(query, routing_="w", result_transformer_=Result.value,
                                   performance_run_props = performance_run.model_dump(exclude_none=True, exclude=["rt_peptides","group_attr","qc_precursors"]),
                                   peptides = peptides,
                                   attribute_values = attribute_values,
                                   precursors = precursors)
        return True 


    def delete(self, tag: str) -> bool:
        """
        Deletes a QC run and all its relationships.
        """
        query = (
            "MATCH (qc:QCRun {tag : $tag}) "
            "DETACH DELETE qc "
            "RETURN count(qc) as deleted "
        )
        r = self._driver.execute_query(query, routing_="w", result_transformer_=Result.value, tag = tag)
        return r.records[0] > 0


    def update(self, tag: str, performance_run: QCRunInsertModel) -> bool:
        """
        QC runs are immutable, updating is not supported. To change a run, delete it and insert a new one.
        """
        raise NotImplementedError("QC runs are immutable and cannot be updated.")


    def standard_exists(self, tag : str) -> bool:
        """
        Checks if a tag is associated with a QC standard.
        """
        query = (
            "MATCH (std:QCStandard {tag : $tag}) "
            "RETURN count(std) > 0 as exists "
        )
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value, tag = tag)
        return r.records[0]


    def get_standards(self, type : str = None, vendor : str = None) -> List[QCStandardResponseModel]:
        """
        Returns the QC standards, optionally filtered by type and vendor.
        """
        query = "MATCH (std:QCStandard) "
        where = []
        if type is not None:
            where.append("std.type = $type")
        if vendor is not None:
            where.append("std.vendor = $vendor")
        if where:
            query += "WHERE " + " AND ".join(where) + " "
        query += "RETURN std {.*} as standard ORDER BY std.tag "
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value,
                                       type = type, vendor = vendor)
        return [QCStandardResponseModel.model_construct(**record["standard"]) for record in r.records]


    def insert_standard(self, standard : QCStandardInsertModel) -> bool:
        """
        Adds a new QC standard to the database. Standards are immutable, an existing tag is merged.
        """
        query = (
            "MERGE (std:QCStandard {tag : $props.tag}) "
            "SET std += $props "
        )
        self._driver.execute_query(query, routing_="w", result_transformer_=Result.value,
                                   props = standard.model_dump())
        return True 


    def delete_standard(self, tag : str) -> bool:
        """
        Deletes a QC standard. A standard can only be deleted if no QC run is linked to it.
        """
        query = (
            "MATCH (std:QCStandard {tag : $tag}) "
            "WHERE NOT ()-[:USED_STANDARD]->(std) "
            "DELETE std "
            "RETURN count(std) as deleted "
        )
        r = self._driver.execute_query(query, routing_="w", result_transformer_=Result.value, tag = tag)
        return r.records[0] > 0


    def insert_qc_precursors(self, run_tag : str, precursors : List[QCPrecursorInsertModel]) -> bool:
        """
        Adds the quantified QCPrecursors to a QC run. Only a specific subset of precursors is recorded
        for QC, the full quantification data is not uploaded. Precursors that do not exist in the
        database are skipped.
        """
        if not self.exists(tag = run_tag):
            return False
        precursor_props = [{'tag' : p.precursor_tag, 'intensity' : p.intensity, 'score' : p.score, 'retention_time' : p.retention_time} for p in precursors]
        query = (
            "MATCH (qc:QCRun {tag : $run_tag}) "
            "UNWIND $precursors as precursor "
            "MATCH (pre:Precursor {tag : precursor.tag}) "
            "MERGE (qc)-[r:QUANTIFIED]->(pre) "
            "SET r.intensity = precursor.intensity, r.score = precursor.score, "
            "r.retention_time = precursor.retention_time, r.created_at = timestamp() "
        )
        self._driver.execute_query(query, routing_="w", result_transformer_=Result.value,
                                   run_tag = run_tag, precursors = precursor_props)
        return True 


    def get_qc_precursors(self, run_tag : str) -> List[QCPrecursorResponseModel]:
        """
        Returns the QCPrecursors that were recorded for a QC run.
        """
        query = (
            "MATCH (qc:QCRun {tag : $run_tag})-[r:QUANTIFIED]->(pre:Precursor) "
            "RETURN pre.tag as precursor_tag, r.intensity as intensity, r.score as score, r.retention_time as retention_time "
            "ORDER BY pre.tag "
        )
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.value, run_tag = run_tag)
        return [QCPrecursorResponseModel(**dict(record)) for record in r.records]
