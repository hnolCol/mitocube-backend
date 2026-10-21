"""
Migration: swap the CURATOR / GROUP_CURATOR role values.

The new GROUP_CURATOR role (2) was inserted below the existing CURATOR
role, which moved CURATOR from 2 to 3. Users that were curators before
that change hold role = 2 in the database and would silently become
group curators. This migration bumps every existing role = 2 user to
role = 3 (global curator), preserving their previous access.

Usage
-----
Run from the repository root with the database settings in place:

    PYTHONPATH=src python -m migration.swap_curator_role_values --dry-run
    PYTHONPATH=src python -m migration.swap_curator_role_values

Use --dry-run first to see how many users would be updated. Run this
once during the release, before any group curator is assigned.
"""
import argparse

from neo4j import Result

from lib.database.Database import get_db


def get_curators_to_bump(db) -> int:
    """Returns the number of users with role = 2 that would be bumped to 3."""
    query = (
        "MATCH (u:User) "
        "WHERE u.role = 2 "
        "RETURN count(u) "
    )
    r = db.connection.driver.execute_query(query, routing_="r", result_transformer_=Result.value)
    return r[0]


def bump_curator_roles(db) -> int:
    """Sets role = 3 on every user with role = 2. Returns the number of updated users."""
    query = (
        "MATCH (u:User) "
        "WHERE u.role = 2 "
        "SET u.role = 3 "
        "RETURN count(u) "
    )
    r = db.connection.driver.execute_query(query, routing_="w", result_transformer_=Result.value)
    return r[0]


def main():
    parser = argparse.ArgumentParser(description="Bump existing curators (role = 2) to the new CURATOR value (3).")
    parser.add_argument("--dry-run", action="store_true", help="Only report the number of users that would be updated.")
    args = parser.parse_args()

    db = get_db()

    if args.dry_run:
        n = get_curators_to_bump(db)
        print(f"{n} user(s) with role = 2 would be bumped to role = 3 (CURATOR).")
        return

    n = bump_curator_roles(db)
    print(f"Bumped {n} user(s) from role = 2 to role = 3 (CURATOR).")


if __name__ == "__main__":
    main()
