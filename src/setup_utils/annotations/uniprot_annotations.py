import os
import io
import requests
import pandas as pd
from collections import defaultdict

base_url = "http://localhost:5002/api/annotations/"
Token = "your_Token_here"  # Replace with your actual Token


headers = {
    "Authorization": f"Bearer {Token}",
    "Content-Type": "application/json"
}


group_tag = "vLavX"

uniprot_url = "https://rest.uniprot.org/uniprotkb/search"

params = {
    "query": "proteome:UP000005640",
    "format": "tsv",
    "fields": ",".join([
        "accession",
        "go",
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

#Group GO terms (like pathways)
go_terms = defaultdict(list)
tm_terms = defaultdict(list)
signal_terms = defaultdict(list)
transit_terms = defaultdict(list)

for _, row in df.iterrows():
    protein = row["Entry"] if "Entry" in row else row["accession"]

    if pd.isna(row["Gene Ontology (GO)"]):
        continue

    for go in row["Gene Ontology (GO)"].split(";"):
        go_terms[go.strip()].append(protein)

    if not pd.isna(row.get("Transmembrane")):
        for tm in row["Transmembrane"].split(";"):
            tm_terms[tm.strip()].append(protein)

    if not pd.isna(row.get("Signal peptide")):
        for signal in row["Signal peptide"].split(";"):
            signal_terms[signal.strip()].append(protein)

    if not pd.isna(row.get("Transit peptide")):
        for transit in row["Transit peptide"].split(";"):
            transit_terms[transit.strip()].append(protein)

#Upload (like Mitocarta)
def upload(text, proteins):
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
    print(text, "Status:", r.status_code)

for go_term, proteins in go_terms.items():
    upload(go_term, proteins)

for tm_term, proteins in tm_terms.items():
    upload(tm_term, proteins)

for signal_term, proteins in signal_terms.items():
    upload(signal_term, proteins)

for transit_term, proteins in transit_terms.items():
    upload(transit_term, proteins)
