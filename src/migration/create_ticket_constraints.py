"""
Migration: create the uniqueness constraints for Ticket nodes.

The support ticket workflow (routers/tickets, lib/database/neo4j/Tickets.py)
relies on two uniqueness constraints:

- Ticket.tag        (unique, like every other entity tag)
- Ticket.reference  (unique, e.g. "TIC-000123")

insert_ticket retries on a reference collision, which only works if the
ticket_reference constraint exists. Without it, duplicate references can be
created and the retry loop never triggers.

Usage
-----
Run from the repository root with the database settings in place:

    PYTHONPATH=src python -m migration.create_ticket_constraints --dry-run
    PYTHONPATH=src python -m migration.create_ticket_constraints

The constraints are created with IF NOT EXISTS, so the migration is safe to
re-run. --dry-run only reports which constraints already exist.
"""
import argparse

from neo4j import Result

from lib.database.Database import get_db


CONSTRAINTS = [
    ("ticket_tag",
     "CREATE CONSTRAINT ticket_tag IF NOT EXISTS FOR (t:Ticket) REQUIRE t.tag IS UNIQUE"),
    ("ticket_reference",
     "CREATE CONSTRAINT ticket_reference IF NOT EXISTS FOR (t:Ticket) REQUIRE t.reference IS UNIQUE"),
]


def get_existing_constraints(db) -> list:
    """Returns the names of the existing constraints in the database."""
    query = "SHOW CONSTRAINTS"
    r = db.connection.driver.execute_query(query, routing_="r", result_transformer_=Result.data)
    return [row["name"] for row in r]


def create_ticket_constraints(db) -> list:
    """Creates the ticket constraints that do not exist yet.
    Returns the names of the constraints created."""
    existing = get_existing_constraints(db)
    created = []
    for name, query in CONSTRAINTS:
        if name in existing:
            continue
        db.connection.driver.execute_query(query, routing_="s")
        created.append(name)
    return created


def main():
    parser = argparse.ArgumentParser(description="Create the Ticket tag and reference uniqueness constraints.")
    parser.add_argument("--dry-run", action="store_true", help="Only report which constraints already exist.")
    args = parser.parse_args()

    db = get_db()

    existing = get_existing_constraints(db)
    missing = [name for name, _ in CONSTRAINTS if name not in existing]

    if args.dry_run:
        print(f"Existing constraints: {existing or 'none'}")
        print(f"Would create: {missing or 'none'}")
        return

    created = create_ticket_constraints(db)
    print(f"Created constraints: {created or 'none'}")
    print(f"Already present: {[name for name, _ in CONSTRAINTS if name not in created] or 'none'}")


if __name__ == "__main__":
    main()
