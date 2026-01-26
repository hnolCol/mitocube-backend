import os
import io
import requests
import pandas as pd
from collections import defaultdict

base_url = "http://localhost:5002/api/annotations/"
Token = "YOUR_TOKEN"  # Replace with your actual Token


headers = {
    "Authorization": f"Bearer {Token}",
    "Content-Type": "application/json"
}


group_tag = "GROUP_TAG"  # Replace with your actual group tag

uniprot_url = "https://rest.uniprot.org/uniprotkb/search"

params = {
    "query": "proteome:UP000005640",
    "format": "tsv",
    "fields": ",".join([
        "accession",
        "go_c",
        "go_p",
        "go_f",
        "ft_transmem",
        "ft_signal",
        "ft_transit"
    ]),
    "size": 10    # test first
}

#Download from Uniprot
r = requests.get(uniprot_url, params=params)
r.raise_for_status()
df = pd.read_csv(io.StringIO(r.text), sep="\t")

annotations = defaultdict(list)

for _, row in df.iterrows():
    protein = row["Entry"]

    #  GOCC 
    if pd.notna(row.get("Gene Ontology (cellular component)")):
        for term in row["Gene Ontology (cellular component)"].split(";"):
            annotations[f"GOCC:{term.strip()}"].append(protein)

    #  GOBP 
    if pd.notna(row.get("Gene Ontology (biological process)")):
        for term in row["Gene Ontology (biological process)"].split(";"):
            annotations[f"GOBP:{term.strip()}"].append(protein)

    #  GOMF 
    if pd.notna(row.get("Gene Ontology (molecular function)")):
        for term in row["Gene Ontology (molecular function)"].split(";"):
            annotations[f"GOMF:{term.strip()}"].append(protein)

    #  UniProt features (one annotation each) 
    if pd.notna(row.get("Transmembrane")):
        annotations["Transmembrane domain"].append(protein)

    if pd.notna(row.get("Signal peptide")):
        annotations["Signal peptide"].append(protein)

    if pd.notna(row.get("Transit peptide")):
        annotations["Transit peptide"].append(protein)

#Upload (like Mitocarta)
def upload(text, proteins):
    if not proteins:
        return

    proteins = list(set(proteins)) 
    print(f"Uploading {text} ({len(proteins)} proteins)")

    r = requests.post(
        base_url,
        headers=headers,
        json={
            "text": text,
            "description": text,
            "group_tag": group_tag,
            "protein_tags": proteins
        }
    )

    print("Status:", r.status_code)

for text, proteins in annotations.items():
    upload(text, proteins)

print("Done.")
