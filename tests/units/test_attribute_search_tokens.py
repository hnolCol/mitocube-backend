import sys
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC_DIR))

pytest.importorskip("neo4j")

from services.regex import build_token_contains_clause, tokenize_search_string
from lib.database.neo4j.Attributes import Neo4JAttributes


class FakeDriver:
    """Captures the query and parameters; returns canned empty results."""

    def __init__(self):
        self.calls = []

    def execute_query(self, query=None, query_=None, **kwargs):
        q = query if query is not None else query_
        self.calls.append((q, kwargs))
        return []


class TestTokenizeSearchString:
    def test_splits_on_whitespace_and_lowercases(self):
        assert tokenize_search_string("WT MB") == ["wt", "mb"]
        assert tokenize_search_string("  Knockdown   parl ") == ["knockdown", "parl"]
        assert tokenize_search_string("PARL") == ["parl"]

    def test_empty_and_invalid_input(self):
        assert tokenize_search_string("") == []
        assert tokenize_search_string("   ") == []
        assert tokenize_search_string(None) == []


class TestBuildTokenContainsClause:
    def test_multi_token_clause_uses_and_semantics(self):
        clause, params = build_token_contains_clause("a.s", "WT MB")
        assert clause == "a.s CONTAINS $token_0 AND a.s CONTAINS $token_1"
        assert params == {"token_0": "wt", "token_1": "mb"}

    def test_empty_search_string_matches_all(self):
        clause, params = build_token_contains_clause("a.s", "   ")
        assert clause == "true"
        assert params == {}


class TestFindTraitTokens:
    def test_multi_word_search_builds_and_clauses(self):
        driver = FakeDriver()
        attrs = Neo4JAttributes(driver)
        attrs.find_trait("WT MB", attribute_tag="att_treatment", limit=10)
        query, params = driver.calls[0]
        assert "a.tag = $attribute_tag" in query
        assert "t.s CONTAINS $token_0 AND t.s CONTAINS $token_1" in query
        assert "search_string" not in params
        assert params["token_0"] == "wt"
        assert params["token_1"] == "mb"
        assert params["attribute_tag"] == "att_treatment"


class TestFindAttributeTokens:
    def test_multi_word_search_builds_and_clauses(self):
        driver = FakeDriver()
        attrs = Neo4JAttributes(driver)
        attrs.find_attribute("WT MB")
        query, params = driver.calls[0]
        assert "a.s CONTAINS $token_0 AND a.s CONTAINS $token_1" in query
        assert "search_string" not in params
        assert params["token_0"] == "wt"
        assert params["token_1"] == "mb"

    def test_empty_search_string_matches_all(self):
        driver = FakeDriver()
        attrs = Neo4JAttributes(driver)
        attrs.find_attribute("")
        query, params = driver.calls[0]
        assert "AND true" in query
        assert not any(k.startswith("token_") for k in params)


class TestFindAttributesAndTraitsTokens:
    def test_multi_word_search_matches_attribute_or_trait_per_token(self):
        driver = FakeDriver()
        attrs = Neo4JAttributes(driver)
        attrs.find_attributes_and_traits(search_string="WT MB")
        query, params = driver.calls[0]
        # WHERE must be present even when only the search string is given
        assert "WHERE" in query
        assert "(a.s CONTAINS $token_0 OR t.s CONTAINS $token_0) AND (a.s CONTAINS $token_1 OR t.s CONTAINS $token_1)" in query
        assert "search_string" not in params
        assert params["token_0"] == "wt"
        assert params["token_1"] == "mb"

    def test_single_token_keeps_or_semantics_between_attribute_and_trait(self):
        driver = FakeDriver()
        attrs = Neo4JAttributes(driver)
        attrs.find_attributes_and_traits(search_string="dmso")
        query, params = driver.calls[0]
        assert query.count("a.s CONTAINS $token_0 OR t.s CONTAINS $token_0") == 1
        assert params["token_0"] == "dmso"

    def test_empty_search_string_adds_no_token_clause(self):
        driver = FakeDriver()
        attrs = Neo4JAttributes(driver)
        attrs.find_attributes_and_traits(search_string="")
        query, params = driver.calls[0]
        assert "token_" not in query
        assert not any(k.startswith("token_") for k in params)

    def test_combines_with_attribute_groups(self):
        driver = FakeDriver()
        attrs = Neo4JAttributes(driver)
        attrs.find_attributes_and_traits(search_string="WT MB", attribute_groups=["sample"])
        query, params = driver.calls[0]
        assert "ag.tag IN $attribute_groups" in query
        assert "(a.s CONTAINS $token_0 OR t.s CONTAINS $token_0)" in query
        assert params["attribute_groups"] == ["sample"]
