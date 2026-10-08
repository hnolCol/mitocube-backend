# Database setup and data migration runbook

The setup logic lives in [`src/setup_utils/cli.py`](../src/setup_utils/cli.py).
It can be run standalone (from the `src` directory) or through the server
entry point — both are equivalent:

```bash
# standalone (does not start the web server)
cd src
python -m setup_utils.cli --setup_database --resources_path /path/to/resources ...

# through app.py (runs setup, then starts the server)
python src/app.py --setup_database --resources_path /path/to/resources ...
```

## Prerequisites

- **Neo4j** running and reachable (env: `db_uri`, `db_user`, `db_pw`) — see
  [`neo4j.md`](../src/setup_utils/neo4j.md) for server administration.
- **MongoDB** running (used by the MFA/query-cache/AI runtimes).
- All required settings available as environment variables or in `.env`
  (see the settings classes in `src/config/settings/`).
- A **resources folder** (see `--resources_path`) laid out as:

```
resources/
  attributes/attributes.json          # attribute definitions (required)
  genotypes/genotypes.json            # optional, for genotype migration
  research_groups/research_groups.txt # optional, for --add_research_groups
  annotations/MitoCarta/annotations.json  # optional, for --mitocarta_annotations
  maintenance/instrumentstates.txt    # optional, maintenance module data
  maintenance/maintenancestates.txt
  maintenance/procedures.txt
  maintenance/spareparts.txt
  symptoms/symptoms.txt
  external_resources/external_resources.json # optional, for --external_resources_xl
```

## Steps and their order

The CLI executes steps in a fixed order. Later steps depend on earlier
ones (e.g. proteomes need the lead user created by the bootstrap step).

| # | Step | Triggered by | What it does |
|---|------|--------------|--------------|
| 1 | bootstrap | `--setup_database` | Ensures a lead user exists (creates the lead-contact user with `--lead_user_tag` on an empty database; the generated password is emailed). Loads attributes, migrates users from `--users`, optionally loads research groups and maintenance reference data. **Not idempotent.** |
| 2 | proteomes | `--proteomes` and/or `--add_control_proteome` | Adds UniProt reference proteomes and/or the control proteome. Data is assigned to the lead user. |
| 3 | annotations | `--setup_database --mitocarta_annotations` | Adds MitoCarta annotations. Requires the bootstrap step for the lead user. |
| 4 | genotypes | presence of `genotypes/genotypes.json` under the resources path | Migrates genotype definitions. |
| 5 | submissions | `--migrate_submissions` | Migrates a submission folder (one subfolder per submission with `params.json` and `data.txt`). Warns if no genotype file was found. |
| 6 | external resources | `--external_resources_xl` | Adds crosslinking datasets from Excel files. |

## Flags

| Flag | Meaning | Production-safe? |
|------|---------|------------------|
| `--setup_database` | Run the bootstrap step | Only on first setup / deliberate re-bootstrap; not idempotent |
| `--resources_path` | Root of the resources folder | yes |
| `--lead_user_tag` | Tag for the lead user created on an empty DB | yes |
| `--users` | Path to `users.json` to migrate users | yes |
| `--proteomes` | Comma-separated UniProt proteome ids | yes |
| `--reviewed_proteins_only` | Restrict proteome insert to reviewed proteins | yes |
| `--migrate_submissions` | Path to a submission folder | yes |
| `--add_control_proteome` | Add control proteome (GFP, luciferase, …) | dev/testing only |
| `--mitocarta_annotations` | Add MitoCarta annotations | dev/testing only |
| `--add_research_groups` | Load research groups from file | dev/testing only |
| `--external_resources_xl` | Add crosslinking Excel datasets | dev/testing only |

## Common scenarios

### Fresh database, full setup

```bash
python -m setup_utils.cli --setup_database \
  --resources_path /path/to/resources \
  --lead_user_tag <tag> \
  --users /path/to/users.json \
  --proteomes UP000005640,UP000002311 \
  --reviewed_proteins_only
```

The bootstrap creates the lead user if the database is empty and emails
the generated password to the configured lead contact. The setup aborts
with a clear error if no lead user exists or can be created.

### Incremental: add a proteome to a running instance

```bash
python -m setup_utils.cli --proteomes UP000589203 \
  --resources_path /path/to/resources --reviewed_proteins_only
```

Only the proteome step runs; no bootstrap.

### Migrate submissions later

```bash
python -m setup_utils.cli --migrate_submissions /path/to/submissions \
  --resources_path /path/to/resources
```

Genotypes are picked up automatically if `genotypes/genotypes.json`
exists under the resources path; otherwise a warning is printed.

## Failure behavior

- Missing user file (`--users`) or missing default research group abort
  the bootstrap with an explicit `ValueError` — no partial silent state.
- A missing lead user after the bootstrap check aborts setup.
- If Neo4j is unreachable, the first database call fails with the
  driver's connection error — check `db_uri`/`db_user`/`db_pw`.
