from typing import List, Tuple
from neo4j import Driver, Result
import pandas as pd

from lib.database.abstract.Precursors import PrecursorsABC
from lib.database.abstract.Samples import SamplesABC
from lib.database.abstract.Cache import CacheABC
from config.models.precursors import PrecursorInsertModel, PrecursorResponseModel


class Neo4JPrecursors(PrecursorsABC):

    def __init__(self, driver: Driver, samples: SamplesABC, cache: CacheABC = None) -> None:
        self._driver = driver
        self._samples = samples
        self.cache = cache

    def count(self, submission_tag: str = None) -> int:
        """Counts the number of precursors. If a submission tag is given, only counts precursors associated with that submission (e.g. that were quantified).

        Parameters
        ----------
        submission_tag : str, optional
            The tag of the submission to count precursors for. If None, counts all precursors, by default None.

        Returns
        -------
        int
            The number of precursors.
        """
        query = "MATCH (p:Precursor) "

        if submission_tag is not None:
            query += "WHERE (p)<-[:QUANTIFIED]-(:Sample)<-[:HAS_SAMPLE]-(:Submission {tag : $submission_tag}) "
        query += "RETURN count(p) "

        r = self._driver.execute_query(query, submission_tag=submission_tag, result_transformer_=Result.value)
        return r[0]

    def count_by_protein_group(self, protein_group_tag: str, submission_tag: str = None) -> int:
        """Counts the number of precursors associated with a given protein group.
        If a submission tag is given, only precursors quantified in that submission are counted.

        Parameters
        ----------
        protein_group_tag : str
            The tag of the protein group to count precursors for.
        submission_tag : str, optional
            If provided, only precursors quantified in the given submission are counted, by default None.

        Returns
        -------
        int
            The number of precursors associated with the protein group.
        """
        query = "MATCH (pg:ProteinGroup {tag : $protein_group_tag})-[:HAS_PRECURSOR]->(p:Precursor) "

        if submission_tag is not None:
            query += "WHERE EXISTS {(p)<-[:QUANTIFIED]-(:Sample)<-[:HAS_SAMPLE]-(submission:Submission {tag : $submission_tag})} "
        query += "RETURN count(p) "

        r = self._driver.execute_query(query, protein_group_tag=protein_group_tag, submission_tag=submission_tag, result_transformer_=Result.value)
        return r[0]

    def exists(self, tag: str) -> bool:
        query = (
            "WITH EXISTS {(p:Precursor {tag : $tag})} as precursor_exists "
            "RETURN precursor_exists "
        )
        r = self._driver.execute_query(query, tag=tag, result_transformer_=Result.value)
        return r[0]

    def find(self, search_string: str, submission_tag: str = None, limit: int = None, provide_protein_info: bool = False) -> List[str] | List[Tuple[str, List[str]]]:
        """Finds all precursors matching the search string.

        Parameters
        ----------
        search_string : str
            The search string to match against precursor tags (sequence followed by charge state). The search string is transformed to upper case.
        submission_tag : str, optional
            If provided, only precursors associated/quantified in the given submission are returned, by default None.
        limit : int, optional
            The maximum number of results to return. If None, all matching precursors are returned.
        provide_protein_info : bool, optional
            If True, returns a list of tuples with the precursor tag and a list of associated protein group tags, by default False.

        Returns
        -------
        List[str] | List[Tuple[str, List[str]]]
            A list of matching precursor tags.
            If provide_protein_info is True, returns a list of tuples with the precursor tag and a list of associated protein group tags.
        """
        if provide_protein_info:
            query = "MATCH (p:Precursor)<-[:HAS_PRECURSOR]-(pg:ProteinGroup) "

            if submission_tag is not None:
                query += "WHERE EXISTS {(p)<-[:QUANTIFIED]-(:Sample)<-[:HAS_SAMPLE]-(submission:Submission {tag : $submission_tag})} AND p.tag CONTAINS $search_string "
            else:
                query += "WHERE p.tag CONTAINS $search_string "

            query += "RETURN p.tag, collect(distinct pg.tag) as protein_groups "

        else:
            query = "MATCH (p:Precursor) "
            if submission_tag is not None:
                query += "WHERE EXISTS {(p)<-[:QUANTIFIED]-(:Sample)<-[:HAS_SAMPLE]-(submission:Submission {tag : $submission_tag})} AND p.tag CONTAINS $search_string "
            else:
                query += "WHERE p.tag CONTAINS $search_string "

            query += "RETURN p.tag "

        if limit is not None:
            query += "LIMIT $limit "
        if provide_protein_info:
            r = self._driver.execute_query(query, search_string=search_string.upper(), limit=limit, result_transformer_=Result.values, routing_="r", submission_tag=submission_tag)
            return [(ri[0], ri[1]) for ri in r]
        else:
            r = self._driver.execute_query(query, search_string=search_string.upper(), limit=limit, result_transformer_=Result.value, routing_="r", submission_tag=submission_tag)
            return [ri for ri in r]

    def get(self, tag: str) -> PrecursorResponseModel:
        """Returns a precursor by its tag (sequence.charge). The protein_group_tag is the protein group
        associated with the precursor that has the least proteins connected to itself (e.g. the protein group
        consisting of a single protein). All associated protein groups are returned in protein_group_tags.

        Parameters
        ----------
        tag : str
            The precursor tag (sequence followed by the charge state).

        Returns
        -------
        PrecursorResponseModel
            The precursor model.
        """
        query = (
            "MATCH (p:Precursor {tag : $tag})<-[:HAS_PRECURSOR]-(pg:ProteinGroup) "
            "WITH p, collect(pg.tag) as protein_group_tags "
            "WITH p, protein_group_tags, EXISTS {(p)<-[:QUANTIFIED]-(s:Sample)} as quantified, "
            "[(pg:ProteinGroup)-[:HAS_PRECURSOR]->(p) | [pg.tag, count {(pg)-[:HAS_PROTEINS]->(:Protein)}]][..] as pg_sizes "
            "RETURN p.tag as tag, p.sequence as sequence, p.charge as charge, p.mz as mz, p.im as im, "
            "protein_group_tags, quantified, pg_sizes"
        )

        r = self._driver.execute_query(query, tag=tag, routing_="r", result_transformer_=Result.data)

        if not r:
            raise ValueError(f"Precursor with tag {tag} not found.")

        data = r[0]
        pg_sizes = data.pop("pg_sizes", [])
        data["protein_group_tag"] = None
        if pg_sizes:
            data["protein_group_tag"] = min(pg_sizes, key=lambda x: x[1])[0]
        return PrecursorResponseModel(**data)

    def get_by_protein_group(self, protein_group_tag: str, submission_tag: str = None, limit: int = None) -> List[PrecursorResponseModel]:
        """Returns all precursors associated with a given protein group.

        Parameters
        ----------
        protein_group_tag : str
            The tag of the protein group to retrieve precursors for.
        submission_tag : str, optional
            If provided, only precursors quantified in the given submission are returned, by default None.
        limit : int, optional
            The maximum number of results to return. If None, all precursors are returned.

        Returns
        -------
        List[PrecursorResponseModel]
            The precursor models associated with the protein group.
        """
        query = (
            "MATCH (pg:ProteinGroup {tag : $protein_group_tag})-[:HAS_PRECURSOR]->(p:Precursor) "
        )

        if submission_tag is not None:
            query += "WHERE EXISTS {(p)<-[:QUANTIFIED]-(:Sample)<-[:HAS_SAMPLE]-(submission:Submission {tag : $submission_tag})} "

        query += (
            "RETURN p.tag as tag, p.sequence as sequence, p.charge as charge, p.mz as mz, p.im as im, "
            "pg.tag as protein_group_tag, "
            "EXISTS {(p)<-[:QUANTIFIED]-(s:Sample)} as quantified "
            "ORDER BY p.tag "
        )

        if limit is not None:
            query += "LIMIT $limit "

        r = self._driver.execute_query(query, protein_group_tag=protein_group_tag, submission_tag=submission_tag, limit=limit, routing_="r", result_transformer_=Result.data)
        return [PrecursorResponseModel(**ri) for ri in r]

    def get_abundance(self, tag: str, submission_tags: List[str] = None) -> pd.DataFrame:
        """Retrieves the abundance data of a precursor by its tag.

        Parameters
        ----------
        tag : str
            The tag of the precursor to retrieve.
        submission_tags : List[str], optional
            A list of submission tags to filter the abundance data by, by default None (all submissions).

        Returns
        -------
        pd.DataFrame
            DataFrame containing the abundance data of the precursor.
                Headers:
                - precursor_tag: The tag of the precursor.
                - sample_tag: The tag of the sample.
                - submission_tag: The tag of the submission.
                - value: The abundance value of the precursor in the sample.

        Raises
        ------
        ValueError
            If the precursor with the given tag does not exist.
        """
        if not self.exists(tag=tag):
            raise ValueError(f"Precursor with tag {tag} does not exist.")

        if self.cache is not None:
            cache_key = self.cache.calculate_key([tag, submission_tags if submission_tags is not None else "None"])
            if self.cache.exists(cache_key):
                return self.cache.get(cache_key)

        query = "MATCH (p:Precursor {tag : $tag})<-[r:QUANTIFIED]-(s:Sample)<-[:HAS_SAMPLE]-(sub:Submission)"

        if submission_tags is not None:
            query += " WHERE sub.tag IN $submission_tags "
        query += "RETURN p.tag as precursor_tag, s.tag as sample_tag, sub.tag as submission_tag, r.value as value"

        r = self._driver.execute_query(query, tag=tag, submission_tags=submission_tags, result_transformer_=Result.to_df, routing_="r")
        if r.empty:
            raise ValueError(f"No abundance data found for precursor with tag {tag}.")
        if self.cache is not None:
            self.cache.insert(cache_key, r)
        return r

    def insert(self, protein_group_tags: List[str], peptide_sequence: str, charge: int, mz: float = None, im: float = None) -> bool:
        """Inserts a precursor into the database. The precursor tag is derived from the
        peptide sequence and the charge state (sequence.charge). The precursor is connected
        to the given protein groups.

        Parameters
        ----------
        protein_group_tags : List[str]
            The tags of the protein groups associated with the precursor.
        peptide_sequence : str
            The amino acid sequence of the peptide underlying the precursor.
        charge : int
            The charge state of the precursor.
        mz : float, optional
            The mass-to-charge ratio of the precursor, by default None.
        im : float, optional
            The ion mobility value of the precursor (e.g. from timsTOF instruments), by default None.

        Returns
        -------
        bool
            True if the insertion was successful, False otherwise.
        """
        precursor_tag = f"{peptide_sequence}.{charge}"

        query = (
            "MERGE (p:Precursor {tag: $precursor_tag}) "
            "SET p.sequence = $peptide_sequence, p.charge = $charge, p.created_at = timestamp() "
            "SET p.mz = CASE WHEN $mz IS NOT NULL THEN $mz ELSE p.mz END, "
            "p.im = CASE WHEN $im IS NOT NULL THEN $im ELSE p.im END "
            "WITH p "
            "UNWIND $protein_group_tags as protein_group_tag "
            "MATCH (pg:ProteinGroup {tag: protein_group_tag}) "
            "MERGE (p)<-[r:HAS_PRECURSOR]-(pg) "
            "SET r.created_at = timestamp() "
            "RETURN count(p) > 0"
        )

        r = self._driver.execute_query(query, precursor_tag=precursor_tag, peptide_sequence=peptide_sequence, charge=charge, mz=mz, im=im, protein_group_tags=protein_group_tags, routing_="w", result_transformer_=Result.value)
        return r[0]

    def bulk_insert(self, precursors: List[PrecursorInsertModel], batch_size: int = 1000, transaction_batch_size: int = 400) -> int:
        """Bulk inserts a list of precursors into the database. The precursor tags are derived from the
        peptide sequence and the charge state (sequence.charge). The precursors are connected
        to their respective protein groups. Precursors that already exist are merged.

        The input is chunked on the client side (batch_size) and each chunk is inserted using a
        CALL { ... } IN TRANSACTIONS subquery so that Neo4J commits the insert in smaller
        transactions (transaction_batch_size), avoiding memory errors for large inputs
        (e.g. 90K precursors per sample).

        Parameters
        ----------
        precursors : List[PrecursorInsertModel]
            The precursors to insert.
        batch_size : int, optional
            The number of precursors sent to the database per query, by default 1000
        transaction_batch_size : int, optional
            The number of rows per internal transaction (IN TRANSACTIONS OF ... ROWS), by default 400

        Returns
        -------
        int
            The number of inserted precursors.
        """
        precursors_data = [p.model_dump() for p in precursors]
        total = 0
        query = f"""
        CALL () {{
            UNWIND $precursors as precursor
            MERGE (p:Precursor {{tag: precursor.sequence + '.' + toString(precursor.charge)}})
            SET p.sequence = precursor.sequence, p.charge = precursor.charge, p.created_at = timestamp()
            SET p.mz = CASE WHEN precursor.mz IS NOT NULL THEN precursor.mz ELSE p.mz END,
                p.im = CASE WHEN precursor.im IS NOT NULL THEN precursor.im ELSE p.im END
            WITH p, precursor
            UNWIND precursor.protein_group_tags as protein_group_tag
            MATCH (pg:ProteinGroup {{tag: protein_group_tag}})
            MERGE (p)<-[r:HAS_PRECURSOR]-(pg)
            SET r.created_at = timestamp()
            RETURN count(r) AS created
        }} IN TRANSACTIONS OF {transaction_batch_size} ROWS
        RETURN sum(created) AS total
        """
        with self._driver.session() as session:
            for i in range(0, len(precursors_data), batch_size):
                batch = precursors_data[i:i+batch_size]
                result = session.run(
                    query,
                    precursors=batch
                )
                record = result.single()
                total += record["total"] if record else 0
        return total

    def is_quantified(self, precursor_tag: str) -> bool:
        """Checks if a precursor is quantified.

        Parameters
        ----------
        precursor_tag : str
            The tag of the precursor to check.

        Returns
        -------
        bool
            True if the precursor is quantified, False otherwise.
        """
        query = (
            "MATCH (p:Precursor {tag: $precursor_tag})<-[:QUANTIFIED]-(s:Sample) "
            "RETURN COUNT(s) > 0"
        )

        r = self._driver.execute_query(query, precursor_tag=precursor_tag, routing_="r", result_transformer_=Result.value)
        return r[0]

    def insert_quantification_data_from_df(self, submission_tag: str, sample_tag: str, quantification_data: pd.DataFrame) -> int:
        """Inserts quantification data for multiple precursors for a specific sample.

        Parameters
        ----------
        submission_tag : str
            The tag of the submission to which the quantification data belongs.
        sample_tag : str
            The tag of the sample for which the quantification data is being inserted.
        quantification_data : pd.DataFrame
            DataFrame containing the quantification data with columns:
                - tag (precursor tag)
                - value (quantification value, log2 intensity).
                - score (score for the identification of the precursor, optional).
                - retention_time (retention time of the precursor, optional).

        Returns
        -------
        int
            The number of quantification entries inserted.

        Raises
        ------
        ValueError
            If the DataFrame does not contain the required columns or if the sample does not exist.
            If the sample does not exist, no data will be inserted and 0 is returned.
        """
        if not all(column in quantification_data.columns for column in ['tag', 'value']):
            raise ValueError("DataFrame must contain 'tag' and 'value' columns.")
        quantification_data = quantification_data.dropna()

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
            "MATCH (p:Precursor {tag: data.tag}) "
            "MERGE (p)<-[r:QUANTIFIED]-(sample) "
            "SET r.value = data.value, r.created_at = timestamp(), r.score = data.score, r.retention_time = data.retention_time "
            "RETURN COUNT(r)"
        )

        r = self._driver.execute_query(query,
                                       submission_tag=submission_tag,
                                       sample_tag=sample_tag,
                                       quantification_data=quantification_data.to_dict(orient="records"),
                                       routing_="w",
                                       result_transformer_=Result.value)
        return r[0] if len(r) > 0 else 0
