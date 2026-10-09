"""
Migration: backfill the status property on consortium SHARED_WITH relations.

The consortium share approval flow (research group heads / PIs approving
shares) introduced a `status` property on the SHARED_WITH relation
("pending" | "approved" | "denied"). Shares created before that change have
no status property and are therefore invisible to the access checks, which
only consider status = 'approved'.

This migration marks all existing (pre-approval-flow) share relations as
approved, since they were created when sharing was immediate and thus
intended to be accessible to the consortium.

Usage
-----
Run from the repository root with the database settings in place:

    PYTHONPATH=src python -m migration.backfill_shared_with_status --dry-run
    PYTHONPATH=src python -m migration.backfill_shared_with_status

Use --dry-run first to see how many relations would be updated.
"""
import argparse

from neo4j import Result

from lib.database.Database import get_db


def get_shared_with_relations_without_status(db) -> int:
    """Returns the number of SHARED_WITH relations that have no status property."""
    query = (
        "MATCH ()-[r:SHARED_WITH]->() "
        "WHERE r.status IS NULL "
        "RETURN count(r) "
    )
    r = db.connection.driver.execute_query(query, routing_="r", result_transformer_=Result.value)
    return r[0]


def backfill_shared_with_status(db) -> int:
    """Sets status = 'approved' on all SHARED_WITH relations without a status
    property. Returns the number of updated relations."""
    query = (
        "MATCH ()-[r:SHARED_WITH]->() "
        "WHERE r.status IS NULL "
        "SET r.status = 'approved', r.approved_at = timestamp() "
        "RETURN count(r) "
    )
    r = db.connection.driver.execute_query(query, routing_="w", result_transformer_=Result.value)
    return r[0]


def main():
    parser = argparse.ArgumentParser(description="Backfill status = 'approved' on SHARED_WITH relations created before the share approval flow.")
    parser.add_argument("--dry-run", action="store_true", help="Only report the number of relations that would be updated.")
    args = parser.parse_args()

    db = get_db()

    if args.dry_run:
        n = get_shared_with_relations_without_status(db)
        print(f"{n} SHARED_WITH relation(s) without status would be set to 'approved'.")
        return

    n = backfill_shared_with_status(db)
    print(f"Set status = 'approved' on {n} SHARED_WITH relation(s).")


if __name__ == "__main__":
    main()
