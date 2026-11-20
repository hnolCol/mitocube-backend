"""Unit test: get_proteins_in_submission must cover protein-group-level
quantification (sample-[:QUANTIFIED]->ProteinGroup-[:HAS_PROTEINS]->Protein),
otherwise the annotation enrichment/shift universe is empty for submissions
quantified at protein group level (the level used by the volcano plots).
"""
from lib.database.neo4j.Submission import Neo4JSubmissions


class FakeDriver:
    def __init__(self, result=None):
        self.queries = []
        self._result = result if result is not None else ["P1", "P2"]

    def execute_query(self, query, **kwargs):
        self.queries.append(query)
        return self._result


def make_submissions(driver):
    return Neo4JSubmissions(driver=driver, meta=None, proteomes=None, condition_applications=None)


def test_get_proteins_in_submission_covers_protein_groups_and_proteins():
    driver = FakeDriver()
    result = make_submissions(driver).get_proteins_in_submission("sub_a")
    assert result == ["P1", "P2"]
    assert len(driver.queries) == 1
    query = driver.queries[0]
    # direct protein-level quantification
    assert "[:QUANTIFIED]->(p:Protein)" in query
    # protein-group-level quantification resolved via HAS_PROTEINS
    assert "[:QUANTIFIED]->(pg:ProteinGroup)-[:HAS_PROTEINS]->(p:Protein)" in query
    assert "UNION" in query
