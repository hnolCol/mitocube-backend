from lib.database.neo4j.Submission import Neo4JSubmissionFilter


class TestTokenizeSearchString:
    def test_splits_on_whitespace_and_lowercases(self):
        assert Neo4JSubmissionFilter._tokenize_search_string("Knockdown parl") == ["knockdown", "parl"]

    def test_collapses_extra_whitespace(self):
        assert Neo4JSubmissionFilter._tokenize_search_string("  knockdown  \t parl  ") == ["knockdown", "parl"]

    def test_single_token(self):
        assert Neo4JSubmissionFilter._tokenize_search_string("PARL") == ["parl"]

    def test_empty_string_returns_no_tokens(self):
        assert Neo4JSubmissionFilter._tokenize_search_string("   ") == []
