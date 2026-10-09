"""
Command-line entry point for database setup and data migration.

Extracted from app.py's __main__ block into ordered, named steps so the
setup process is testable, documented, and can be run without starting
the web server.

Usage (from the src directory):

    python -m setup_utils.cli --setup_database --resources_path ... 

The web server entry point (app.py) delegates its --setup flags here.
"""
import argparse
import os
import sys

import pandas as pd

from config.settings.proteomes.control_proteomes import get_control_proteome_settings
from lib.database.Database import Database

DB = Database.DB()
CTRL_PROTEOME_SETTINGS = get_control_proteome_settings()


def _resolve(resources_path, *relative):
    """Join and return the path only if it exists, else None."""
    full = os.path.join(resources_path, *relative)
    return full if os.path.exists(full) else None


def step_bootstrap(args, ctx):
    """Bootstrap: lead user, research groups, attributes, users, maintenance data.

    Runs only under --setup_database. Creates the lead-contact user when the
    database has no users yet (an email with the generated password is sent
    to the lead contact).
    """
    DB.users.check(lead_tag=args.lead_user_tag)
    lead_user = DB.users.get_lead_user()
    if lead_user is None:
        raise ValueError(
            "Setup failed: no lead user exists in the database and none could be created."
        )
    ctx["lead_user"] = lead_user

    research_group_file = _resolve(args.resources_path, "research_groups", "research_groups.txt")
    if research_group_file is not None and args.add_research_groups:
        rgs = DB.research_groups._utils_insert_from_file(file_path=research_group_file, sep="\t")
        print(rgs)
        ctx["default_rg"] = rgs.iloc[0]["tag"]

    genotype_file = _resolve(args.resources_path, "genotypes", "genotypes.json")
    ctx["genotype_file"] = genotype_file

    # Adding attributes sets is_updating on all attributes; required for
    # correct trait associations during proteome addition.
    DB.attributes._utils_insert_from_file(
        file_path=os.path.join(args.resources_path, "attributes", "attributes.json")
    )

    if args.users is not None and os.path.exists(args.users):
        user_tags = DB.users._utils_migrate(path_to_user_data=args.users)
        default_rg = ctx.get("default_rg")
        if default_rg is None:
            raise ValueError(
                "Cannot migrate users: no default research group available. "
                "Provide --add_research_groups with a research_groups.txt file."
            )
        DB.research_groups.insert_users(tag=default_rg, user_tags=user_tags)
    else:
        raise ValueError(
            f"User path {args.users} does not exist, cannot migrate users. "
            "Please provide a valid path to the users.json file."
        )

    # Maintenance module reference data.
    DB.instrument_states._utils_insert_from_file(
        file_path=os.path.join(args.resources_path, "maintenance", "instrumentstates.txt"), sep="\t"
    )
    DB.maintenance_events._utils_insert_maintenance_state_from_file(
        file_path=os.path.join(args.resources_path, "maintenance", "maintenancestates.txt")
    )
    DB.maintenance_procedures._utils_insert_from_file(
        file_path=os.path.join(args.resources_path, "maintenance", "procedures.txt"), sep="\t"
    )
    DB.symptoms._utils_insert_from_file(
        file_path=os.path.join(args.resources_path, "symptoms", "symptoms.txt"), sep="\t"
    )
    DB.spareparts._utils_insert_from_file(
        file_path=os.path.join(args.resources_path, "maintenance", "spareparts.txt"), sep="\t"
    )


def step_proteomes(args, ctx):
    """Add control proteome and/or UniProt reference proteomes."""
    lead_user = ctx.get("lead_user") or DB.users.get_lead_user()

    if CTRL_PROTEOME_SETTINGS.add_control_proteome or args.add_control_proteome:
        control_proteome = pd.read_csv(CTRL_PROTEOME_SETTINGS.control_proteome_file, sep="\t")
        DB.proteomes.add_proteome_details(
            proteome_tag="ctrl",
            proteome_info={
                "name": "Ctrl proteome",
                "description": "Control / misc proteins such as GFP, and lucZ.",
            },
        )
        DB.proteomes.insert_proteome_from_dataframe(
            control_proteome, proteome_tag="ctrl", user_tag=lead_user
        )
        DB.proteomes.set_updating(tag="ctrl", updating=False)

    if args.proteomes is not None:
        print("Adding proteomes: " + args.proteomes + " from Uniprot. This may take a while... "
              "If they exist already, they will be updated.")
        DB.proteomes.insert_uniprot_proteome(
            proteome_tags=args.proteomes.split(","),
            reviewed=args.reviewed_proteins_only,
            user_tag=lead_user,
        )


def step_annotations(args, ctx):
    """Add MitoCarta annotations (requires --setup_database for the lead user)."""
    if not (args.setup_database and args.mitocarta_annotations):
        return
    lead_user = ctx.get("lead_user") or DB.users.get_lead_user()
    DB.annotations._utils_insert_from_file(
        file_path=os.path.join(args.resources_path, "annotations", "MitoCarta", "annotations.json"),
        folder_path=os.path.join(args.resources_path, "annotations"),
        user_tag=lead_user,
    )


def step_genotypes(args, ctx):
    """Migrate genotypes from genotypes.json."""
    genotype_file = ctx.get("genotype_file")
    if genotype_file is None:
        return
    from migrate_genotypes import MigrateGenotypes

    lead_user = ctx.get("lead_user") or DB.users.get_lead_user()
    ctx["genotype_mapper_file_path"] = MigrateGenotypes(
        path_to_genotypes=genotype_file, fallback_user_tag=lead_user
    ).migrate()


def step_submissions(args, ctx):
    """Migrate a submission folder into the database."""
    if args.migrate_submissions is None:
        return
    genotype_file = ctx.get("genotype_file")
    if genotype_file is None:
        print("No genotype file provided, genotypes are likely to be missed...")
    from MigrateDatabase import MigrateData

    MigrateData(
        path_to_submission_folder=args.migrate_submissions,
        genotype_labels_path=ctx.get("genotype_mapper_file_path"),
        fallback_user_tag=ctx.get("lead_user") or DB.users.get_lead_user(),
    ).run()


def step_external_resources(args, ctx):
    """Add crosslinking external-resource datasets from Excel files."""
    if not args.external_resources_xl:
        return
    DB.external_resources._utils_insert_from_file(
        file_path=os.path.join(args.resources_path, "external_resources", "external_resources.json"),
        folder_path=os.path.join(args.resources_path, "external_resources"),
    )


STEPS = [
    ("bootstrap", step_bootstrap),
    ("proteomes", step_proteomes),
    ("annotations", step_annotations),
    ("genotypes", step_genotypes),
    ("submissions", step_submissions),
    ("external_resources", step_external_resources),
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Set up the mitocube database: bootstrap data, add proteomes, "
        "annotations and migrate submissions. See docs/SETUP.md for a runbook."
    )
    parser.add_argument("--setup_database", action="store_true",
                        help="Run the bootstrap step (lead user, research groups, attributes, "
                             "users, maintenance data). NOT idempotent; see docs/SETUP.md.")
    parser.add_argument("--migrate_submissions", default=None,
                        help="Path to a submission folder (one subfolder per submission, each "
                             "containing params.json and data.txt).")
    parser.add_argument("--proteomes", default=None,
                        help="Comma-separated UniProt proteome ids, e.g. UP000005640,UP000002311.")
    parser.add_argument("--add_control_proteome", action="store_true",
                        help="Add the control proteome (GFP, luciferase etc.). "
                             "Development/testing aid; not for production.")
    parser.add_argument("--resources_path", default="/home/cloud/resources/",
                        help="Path to the resources folder containing attributes/, genotypes/, "
                             "research_groups/, maintenance/, annotations/ etc.")
    parser.add_argument("--lead_user_tag", default=None,
                        help="Tag for the lead user created on an empty database.")
    parser.add_argument("--users", default=None,
                        help="Path to users.json for user migration.")
    parser.add_argument("--mitocarta_annotations", action="store_true",
                        help="Add MitoCarta annotations. Not for production use.")
    parser.add_argument("--reviewed_proteins_only", action="store_true",
                        help="Only add reviewed proteins when adding UniProt proteomes.")
    parser.add_argument("--external_resources_xl", action="store_true",
                        help="Add crosslinking datasets from Excel files in the resources "
                             "folder. Not for production use.")
    parser.add_argument("--add_research_groups", action="store_true",
                        help="Add research groups from research_groups.txt. Not for production use.")
    return parser


def run(args=None) -> None:
    """Execute all setup steps in order. Exposes the resolved args for tests."""
    parsed = build_parser().parse_args(args)
    ctx = {}

    if parsed.setup_database:
        step_bootstrap(parsed, ctx)
    step_proteomes(parsed, ctx)
    step_annotations(parsed, ctx)
    step_genotypes(parsed, ctx)
    step_submissions(parsed, ctx)
    step_external_resources(parsed, ctx)


if __name__ == "__main__":
    run()
