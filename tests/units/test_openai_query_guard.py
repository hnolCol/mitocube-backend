import sys
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC_DIR))

from lib.database.neo4j.query_guard import validate_read_only_query  # noqa: E402


class TestValidateReadOnly:
    @pytest.mark.parametrize("query", [
        "MATCH (p:Protein) RETURN p.tag",
        "MATCH (s:Submission) WHERE s.title = 'set and delete' RETURN s.tag",
        "MATCH (u:User) RETURN u.tag, u.email",
    ])
    def test_read_queries_pass(self, query):
        validate_read_only_query(query)

    @pytest.mark.parametrize("query", [
        "MATCH (u:User {tag : 'abc'}) SET u.role = 0 RETURN u",
        "MATCH (u:User {tag : 'abc'}) SET u['password'] = 'x' RETURN u",
        "MATCH (n) DETACH DELETE n",
        "MERGE (p:Protein {tag : 'x'}) RETURN p",
        "CREATE (p:Protein {tag : 'x'})",
        "MATCH (p:Plate) REMOVE p.format RETURN p",
        "DROP INDEX idx",
        "LOAD CSV WITH HEADERS FROM 'file:///x.csv' AS row RETURN row",
        "MATCH (p) FOREACH (x IN [1] | SET p.x = x) RETURN p",
        "CALL db.labels() YIELD label RETURN label",
    ])
    def test_write_and_call_queries_rejected(self, query):
        with pytest.raises(ValueError):
            validate_read_only_query(query)

    @pytest.mark.parametrize("query", [
        "MATCH (u:User) RETURN u.password",
        "MATCH (u:User) RETURN u['password']",
        "MATCH (u:User) RETURN properties(u).password",
        "MATCH (u:User) RETURN u {password} AS p",
    ])
    def test_password_access_rejected(self, query):
        with pytest.raises(ValueError):
            validate_read_only_query(query)
