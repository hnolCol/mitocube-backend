import io
import gzip
import time
import httpx
import pandas as pd

XLSX = "/Users/PParsa/Documents/GitHub/mitocube-backend/resources/external_resources/41467_2024_47569_MOESM4_ESM.xlsx"
SHEET = "Supp Data 1_Combined (DSSO)"
OUT = "/Users/PParsa/Documents/GitHub/mitocube-backend/resources/external_resources/clasp_crosslinks.txt"
DELIMITER = "#"


def parse_crosslinks(df):
    records, seen = [], set()
    for _, row in df.iterrows():
        for side in ["ab", "ba"]:
            links_raw = row.get(f"crosslinks_{side}")
            scores_raw = row.get(f"score_{side}")
            if pd.isna(links_raw) or pd.isna(scores_raw):
                continue
            links = str(links_raw).split(DELIMITER)
            scores = str(scores_raw).split(DELIMITER)
            for link, score in zip(links, scores):
                parts = link.split("-")
                if len(parts) != 4:
                    continue
                gene1, pos1, gene2, pos2 = parts
                key = tuple(sorted([(gene1, pos1), (gene2, pos2)]))
                if key in seen:
                    continue
                seen.add(key)
                try:
                    pos1, pos2, score = int(pos1), int(pos2), float(score)
                except ValueError:
                    continue
                records.append({"gene1": gene1, "pos1": pos1, "gene2": gene2, "pos2": pos2, "score": score})
    return records


def fetch_gene_to_uniprot(genes, batch_size=50):
    mapping = {}
    genes = list(genes)
    with httpx.Client(http2=True, timeout=60) as client:
        for i in range(0, len(genes), batch_size):
            batch = genes[i:i + batch_size]
            query = " OR ".join(f"gene_exact:{g}" for g in batch)
            params = {
                "query": f"({query}) AND organism_id:9606 AND reviewed:true",
                "fields": "accession,gene_names",
                "format": "tsv",
                "compressed": "true",
                "size": 500,
            }
            r = client.get("https://rest.uniprot.org/uniprotkb/search", params=params)
            r.raise_for_status()
            page = pd.read_csv(io.StringIO(gzip.decompress(r.content).decode()), sep="\t")
            for _, row in page.iterrows():
                for sym in str(row.get("Gene Names", "")).split():
                    mapping.setdefault(sym.upper(), str(row["Entry"]))
            while "Link" in r.headers:
                cursor = r.headers["link"].split("cursor=")[1].split("&")[0]
                params["cursor"] = cursor
                r = client.get("https://rest.uniprot.org/uniprotkb/search", params=params)
                r.raise_for_status()
                page = pd.read_csv(io.StringIO(gzip.decompress(r.content).decode()), sep="\t")
                for _, row in page.iterrows():
                    for sym in str(row.get("Gene Names", "")).split():
                        mapping.setdefault(sym.upper(), str(row["Entry"]))
            time.sleep(0.5)
            print(f"  {min(i + batch_size, len(genes))}/{len(genes)}", end="\r")
    print()
    return mapping


df = pd.read_excel(XLSX, sheet_name=SHEET)
records = parse_crosslinks(df)
print(f"Parsed {len(records)} crosslinks")

all_genes = {g for rec in records for g in (rec["gene1"], rec["gene2"])}
gene_to_uniprot = fetch_gene_to_uniprot(all_genes)
print(f"Resolved {len(gene_to_uniprot)} of {len(all_genes)} genes")

rows = []
for rec in records:
    tag_a = gene_to_uniprot.get(rec["gene1"].upper())
    tag_b = gene_to_uniprot.get(rec["gene2"].upper())
    if not tag_a or not tag_b:
        continue
    rows.append({"protein_tag_a": tag_a, "protein_tag_b": tag_b, "pos_a": rec["pos1"], "pos_b": rec["pos2"], "score": rec["score"]})

pd.DataFrame(rows).to_csv(OUT, sep="\t", index=False)
print(f"Wrote {len(rows)} rows to {OUT}")