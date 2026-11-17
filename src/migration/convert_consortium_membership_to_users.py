"""
Migration: convert consortium membership from research-group level to user level.

Consortium membership is now a direct (User)-[:MEMBER_OF]->(Consortium) relation.
The (ResearchGroup)-[:MEMBER_OF]->(Consortium) relation is kept, but only marks
the group as eligible: users of an eligible group can be added as direct
members, and the heads (PIs) of the group must be members.

This migration creates direct memberships for the heads (PIs) of all eligible
research groups. Non-head users do not get a membership; curators/admins add
the legally entitled users manually afterwards. This intentionally reduces
access, which is the safe direction.

Usage
-----
Run from the repository root with the database settings in place:

    PYTHONPATH=src python -m migration.convert_consortium_membership_to_users --dry-run
    PYTHONPATH=src python -m migration.convert_consortium_membership_to_users

Use --dry-run first to see how many memberships would be created.
"""
import argparse

from neo4j import Result

from lib.database.Database import get_db


def count_expected_head_memberships(db) -> int:
    """Returns the number of head (PI) memberships that would be created."""
    query = (
        "MATCH (c:Consortium)<-[:MEMBER_OF]-(rg:ResearchGroup) "
        "MATCH (h:User)-[:HEAD_OF]->(rg) "
        "RETURN count(DISTINCT [h.tag, c.tag]) "
    )
    r = db.connection.driver.execute_query(query, routing_="r", result_transformer_=Result.value)
    return r[0]


def create_head_memberships(db) -> int:
    """Creates a direct membership (origin = 'head') for every head (PI) of an
    eligible research group of a consortium. Returns the number of created memberships."""
    query = (
        "MATCH (c:Consortium)<-[:MEMBER_OF]-(rg:ResearchGroup) "
        "MATCH (h:User)-[:HEAD_OF]->(rg) "
        "MERGE (h)-[m:MEMBER_OF]->(c) "
        "ON CREATE "
        "SET m.created_at = timestamp(), m.origin = 'head', m.added_by = 'migration' "
        "RETURN count(m) "
    )
    r = db.connection.driver.execute_query(query, routing_="w", result_transformer_=Result.value)
    return r[0]


def main():
    parser = argparse.ArgumentParser(description="Create direct consortium memberships for the heads (PIs) of eligible research groups.")
    parser.add_argument("--dry-run", action="store_true", help="Only report the number of memberships that would be created.")
    args = parser.parse_args()

    db = get_db()

    if args.dry_run:
        print(f"Head (PI) memberships that would be created: {count_expected_head_memberships(db)}")
        return

    created = create_head_memberships(db)
    print(f"Created {created} head (PI) memberships. Non-head users keep no consortium access until curators add them.")


if __name__ == "__main__":
    main()
