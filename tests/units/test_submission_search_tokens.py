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


class TestBuildV2WhereResearchGroup:
    def _build(self, **kwargs):
        defaults = dict(
            scope_tags=None,
            search_string=None,
            state=None,
            trait_tags=None,
            attribute_tag=None,
            ca_tags=None,
            protein_tags=None,
            ca_search_string=None,
            user_tags=None,
            user_role="any",
            genotype_tag=None,
            consortium_tags=None,
            research_group_tags=None,
            include_sample_ca=False,
            ca_match_all=True,
        )
        defaults.update(kwargs)
        return Neo4JSubmissionFilter._build_v2_where(object(), **defaults)

    def test_no_research_group_filter(self):
        where, params = self._build()
        assert not any("research_group_tags" in w for w in where)
        assert "research_group_tags" not in params

    def test_research_group_filter_added(self):
        where, params = self._build(research_group_tags=["rg1", "rg2"])
        assert any("ResearchGroup" in w and "$research_group_tags" in w for w in where)
        assert params["research_group_tags"] == ["rg1", "rg2"]

    def test_research_group_filter_combines_with_user_filter(self):
        where, params = self._build(user_tags=["u1"], research_group_tags=["rg1"])
        assert any("$user_tags" in w for w in where)
        assert any("$research_group_tags" in w for w in where)
