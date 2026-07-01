# Import Proximity Labeling data 
import io
import gzip
import time
import requests
import pandas as pd
from collections import defaultdict

S3 = "/Users/PParsa/Documents/GitHub/mitocube-backend/resources/annotations/MitoCarta/1-s2.0-S1550413120304125-mmc4.xlsx"
S4 = "/Users/PParsa/Documents/GitHub/mitocube-backend/resources/annotations/MitoCarta/1-s2.0-S1550413120304125-mmc5.xlsx"
BFDR = 0.01

# Load & filter 
df_baits = pd.read_excel(S3, sheet_name="TabA_bait list")
df_int   = pd.read_excel(S4, sheet_name="TabA_SAINT_ID3963")
df_hc    = df_int[df_int["BFDR"] <= BFDR]
df_hc    = df_hc[df_hc["PreyGene"].apply(lambda x: isinstance(x, str))]

# Bait -> UniProt (from S3, no API needed) 
bait_to_uniprot = {}
for _, row in df_baits.iterrows():
    name = str(row["Bait Name"])
    bait_to_uniprot[name] = str(row["Uniprot ID"])
    base = name.replace("-C-ter", "").replace("-N-ter", "")
    if base not in bait_to_uniprot:
        bait_to_uniprot[base] = str(row["Uniprot ID"])

# Prey gene -> UniProt 
def fetch_gene_to_uniprot(genes, batch_size=50):
    mapping = {}
    genes = list(genes)
    for i in range(0, len(genes), batch_size):
        batch = genes[i:i+batch_size]
        query = " OR ".join(f"gene_exact:{g}" for g in batch)
        params = {
            "query": f"({query}) AND organism_id:9606 AND reviewed:true",
            "fields": "accession,gene_names",
            "format": "tsv",
            "compressed": "true",
            "size": 500,
        }
        r = requests.get("https://rest.uniprot.org/uniprotkb/search", params=params, timeout=60)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(gzip.decompress(r.content).decode()), sep="\t")
        for _, row in df.iterrows():
            for sym in str(row.get("Gene Names", "")).split():
                mapping.setdefault(sym.upper(), str(row["Entry"]))

        while "Link" in r.headers:
            cursor = r.headers["link"].split("cursor=")[1].split("&")[0]
            params["cursor"] = cursor
            r = requests.get("https://rest.uniprot.org/uniprotkb/search", params=params, timeout=60)
            r.raise_for_status()
            df = pd.read_csv(io.StringIO(gzip.decompress(r.content).decode()), sep="\t")
            for _, row in df.iterrows():
                for sym in str(row.get("Gene Names", "")).split():
                    mapping.setdefault(sym.upper(), str(row["Entry"]))

        time.sleep(0.5)
        print(f"  {min(i+batch_size, len(genes))}/{len(genes)}", end="\r")
    print()
    return mapping

print("Fetching UniProt for prey genes...")
gene_to_uniprot = fetch_gene_to_uniprot(df_hc["PreyGene"].unique())

# Build interactions.txt 
rows = []
for _, row in df_hc.iterrows():
    prey_up = gene_to_uniprot.get(str(row["PreyGene"]).upper())
    if prey_up:
        rows.append({"bait_name": str(row["Bait"]), "UniProt": prey_up})

pd.DataFrame(rows).to_csv("/Users/PParsa/Documents/GitHub/mitocube-backend/resources/annotations/MitoCarta/interactions.txt", sep="\t", index=False)
print(f"Done -> interactions.txt ({len(rows)} rows)")