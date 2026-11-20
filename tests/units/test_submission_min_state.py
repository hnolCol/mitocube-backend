"""Unit tests for the min_state filter of the submission query (find_v2/count_v2).

min_state restricts to submissions whose latest IN_STATE state is >=
min_state (e.g. min_state=5 -> ACTIVE and PUBLISHED), complementing the
exact state list filter.
"""
from lib.database.neo4j.Submission import Neo4JSubmissionFilter


def _build(**kwargs):
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
        min_state=None,
    )
    defaults.update(kwargs)
    return Neo4JSubmissionFilter._build_v2_where(object(), **defaults)


def test_min_state_alone_adds_greater_equal_clause():
    where, params = _build(min_state=5)
    assert any("latest.s >= $min_state" in w for w in where)
    assert params["min_state"] == 5
    assert "states" not in params


def test_min_state_combines_with_exact_state_list():
    where, params = _build(state=[3], min_state=5)
    clause = [w for w in where if "latest.s" in w]
    assert len(clause) == 1
    assert "latest.s IN $states" in clause[0] and "latest.s >= $min_state" in clause[0]
    assert params["states"] == [3]
    assert params["min_state"] == 5


def test_no_state_filter_without_state_or_min_state():
    where, params = _build()
    assert not any("latest.s" in w for w in where)
    assert "states" not in params and "min_state" not in params
