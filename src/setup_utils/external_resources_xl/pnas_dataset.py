import pandas as pd

df = pd.read_excel("/Users/PParsa/Documents/GitHub/mitocube-backend/resources/external_resources/pnas_2219418120_sd01.xlsx", sheet_name="All URPs")

out = df.rename(columns={
    "Protein 1": "protein_tag_a",
    "Protein 2": "protein_tag_b",
    "Protein Position 1": "pos_a",
    "Protein Position 2": "pos_b",
    "Total number of CSMs (cross-link spectral matches)": "score",
})[["protein_tag_a", "protein_tag_b", "pos_a", "pos_b", "score"]]

out.to_csv("/Users/PParsa/Documents/GitHub/mitocube-backend/resources/external_resources/pnas_crosslinks.txt", sep="\t", index=False)
print(f"Wrote {len(out)} rows")