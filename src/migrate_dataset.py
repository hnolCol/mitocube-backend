import json
import os
from pathlib import Path
from neo4j import GraphDatabase

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

uri = os.getenv("db_uri")
user = os.getenv("db_user")
password = os.getenv("db_pw")

driver = GraphDatabase.driver(uri, auth=(user, password))

path = "/Users/PParsa/Documents/GitHub/mitocube-backend/params.json"

def migrate_dataset(tx, data):
    tx.run("""
        MATCH (u:User {label: $user_label})
        MERGE (s:Submission {label: $label})
        SET s.title = $title,
            s.state = $state,
            s.created_on = $created_on,
            s.modified_on = $modified_on,
            s.n_samples = $n_samples
        MERGE (u)-[:CREATED]->(s)
    """,
    label=data["label"],
    user_label=data["user_label"],
    title=data.get("title"),
    state=data.get("state"),
    created_on=data.get("created_on"),
    modified_on=data.get("modified_on"),
    n_samples=data.get("n_samples")
    )


def migrate_metatext(tx, data):
    metatext = data.get("metatext", {})

    cleaned = {
        key.replace("metatext:", ""): value
        for key, value in metatext.items()
    }

    tx.run("""
        MATCH (s:Submission {label: $label})
        SET s += $metatext
    """,
    label=data["label"],
    metatext=cleaned
    )

def migrate_dataset_attributes(data):

    attributes = data.get("dataset_attributes", {})

    with driver.session() as session:

        for attr_tag, values in attributes.items():

            for raw_value in values:

                session.run("""
                    MERGE (a:Attribute {tag: $attr_tag})
                    MERGE (t:Trait {tag: $trait_tag})

                    MERGE (ca:ConditionApplication {
                        submission_label: $submission_label,
                        attribute_tag: $attr_tag,
                        trait_tag: $trait_tag
                    })
                    ON CREATE SET ca.created_at = timestamp()

                    MERGE (ca)-[:OF_ATTRIBUTE]->(a)
                    MERGE (ca)-[:INSTANCE_OF]->(t)

                    WITH ca
                    MATCH (s:Submission {label: $submission_label})
                    MERGE (s)-[:HAS_APPLICATION]->(ca)
                """,
                attr_tag=attr_tag,
                trait_tag=raw_value,
                submission_label=data["label"]
                )

def migrate_samples(tx, data):

    sample_names = data.get("sample_names", [])
    replicates = data.get("replicates", [])

    for i, sample_name in enumerate(sample_names):

        replicate = replicates[i] if i < len(replicates) else None

        tx.run("""
            MATCH (s:Submission {label: $submission_label})
            MERGE (sm:Sample {name: $sample_name, submission_label: $submission_label})
            SET sm.replicate = $replicate
            MERGE (s)-[:HAS_SAMPLE]->(sm)
        """,
        submission_label=data["label"],
        sample_name=sample_name,
        replicate=replicate
        )


def migrate_sample_attributes(data):

    sample_attrs = data.get("samples_attributes", {})
    sample_names = data.get("sample_names", [])

    with driver.session() as session:

        for attr_tag, value_map in sample_attrs.items():

            for raw_value, indices in value_map.items():

                parsed_value = None
                if ":" in raw_value:
                    parsed_value = raw_value.split(":", 1)[1]

                for index in indices:
                    if index >= len(sample_names):
                        continue

                    sample_name = sample_names[index]

                    session.run("""
                        MERGE (a:Attribute {tag: $attr_tag})
                        MERGE (t:Trait {tag: $trait_tag})

                        MERGE (ca:ConditionApplication {
                            sample_name: $sample_name,
                            attribute_tag: $attr_tag,
                            trait_tag: $trait_tag
                        })
                        ON CREATE SET ca.created_at = timestamp()

                        MERGE (ca)-[:OF_ATTRIBUTE]->(a)
                        MERGE (ca)-[:INSTANCE_OF]->(t)

                        WITH ca
                        MATCH (sm:Sample {name: $sample_name, submission_label: $submission_label})
                        MERGE (sm)-[:HAS_APPLICATION]->(ca)
                    """,
                    attr_tag=attr_tag,
                    trait_tag=raw_value,
                    sample_name=sample_name,
                    submission_label=data["label"]
                    )



def migrate_genotypes(tx, data):

    genotypes = data.get("samples_genotypes", {})
    sample_names = data.get("sample_names", [])

    for genotype_label, indices in genotypes.items():

        for index in indices:
            if index < len(sample_names):
                sample_name = sample_names[index]

                tx.run("""
                    MATCH (sm:Sample {name: $sample_name, submission_label: $submission_label})
                    MERGE (g:Genotype {label: $genotype_label})
                    MERGE (sm)-[:HAS_GENOTYPE]->(g)
                """,
                sample_name=sample_name,
                submission_label=data["label"],
                genotype_label=genotype_label
                )



def migrate_timeline(tx, data):

    timeline = data.get("timeline", {})
    entries = timeline.get("entries", [])

    for entry in entries:

        tx.run("""
            MATCH (s:Submission {label: $submission_label})
            MERGE (e:TimelineEntry {
                label: $entry_label,
                submission_label: $submission_label
            })
            SET e.state = $state,
                e.comment = $comment,
                e.created_on = $created_on,
                e.user_label = $user_label
            MERGE (s)-[:HAS_TIMELINE_ENTRY]->(e)
        """,
        submission_label=data["label"],
        entry_label=entry["label"],
        state=entry.get("state"),
        comment=entry.get("comment"),
        created_on=entry.get("created_on"),
        user_label=entry.get("user_label")
        )


def migrate_single_submission(path):

    with open(path, "r") as f:
        data = json.load(f)

    with driver.session() as session:
        session.execute_write(migrate_dataset, data)
        session.execute_write(migrate_metatext, data)
        session.execute_write(migrate_samples, data)
        session.execute_write(migrate_genotypes, data)
        session.execute_write(migrate_timeline, data)

    migrate_dataset_attributes(data)
    migrate_sample_attributes(data)


if __name__ == "__main__":
    migrate_single_submission(path)  
    driver.close()