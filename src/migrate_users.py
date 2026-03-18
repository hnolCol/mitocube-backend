import json
from neo4j import GraphDatabase
import os

from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent / ".env")

uri = os.getenv("db_uri")
user = os.getenv("db_user")
password = os.getenv("db_pw")

driver = GraphDatabase.driver(uri, auth=(user, password))

json_path = "/Users/PParsa/Downloads/users.json"

def migrate_users(json_path):
    with open(json_path, "r") as f:
        users = json.load(f)

    with driver.session() as session:
        for user in users:

            session.run("""
                MERGE (u:User {label: $label})
                SET u.firstname = $firstname,
                    u.lastname = $lastname,
                    u.institute = $institute,
                    u.research_group = $research_group,
                    u.created_on = $created_on,
                    u.email = $email,
                    u.id = $id,
                    u.updated_on = $updated_on,
                    u.password = $password,
                    u.allow_login = $allow_login,
                    u.role = $role
            """,
            label=user["label"],
            firstname=user.get("firstname"),
            lastname=user.get("lastname"),
            institute=user.get("institute"),
            research_group=user.get("research_group"),
            created_on=user.get("created_on"),
            email=user.get("email"),
            id=user.get("id"),
            updated_on=user.get("updated_on"),
            password=user.get("password"),
            allow_login=user.get("allow_login"),
            role=user.get("role")
            )

if __name__ == "__main__":
    migrate_users(json_path)