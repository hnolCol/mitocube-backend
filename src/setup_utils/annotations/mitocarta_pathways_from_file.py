import os
import pandas as pd
import requests
from collections import defaultdict


base_url = "http://localhost:5002/api/annotations/"
Token = "your_Token_here"  # Replace with your actual Token

headers = {
    "Authorization": f"Bearer {Token}",
    "Content-Type": "application/json"
}



annotatiion_file = "path_to_your/MitoCarta3.0.xlsx"  # Replace with the actual path to your MitoCarta3.0.xlsx file
sheet_name = "A Human MitoCarta3.0"
group_tag = "enter_your_group_tag_here"  # Replace with your actual group tag

df = pd.read_excel(annotatiion_file, sheet_name=sheet_name)


def explode(value):
    if pd.isna(value):
        return []
    return [v.strip() for v in str(value).split("|") if v.strip()]


pathway_to_proteins = defaultdict(list)

for i, row in df.iterrows():

    uniprot = row["UniProt"]
    if pd.isna(uniprot):
        continue

    for pathway in explode(row["MitoCarta3.0_MitoPathways"]):
        pathway_to_proteins[pathway].append(str(uniprot).strip())


for pathway, proteins in pathway_to_proteins.items():
    print(f"Uploading {pathway} ({len(proteins)} proteins)")

    r = requests.post(
        base_url,
        headers=headers,
        json={
            "text": pathway,
            "description": pathway,
            "group_tag": group_tag,
            "protein_tags": proteins
        }
    )

    print("Status:", r.status_code)
    
