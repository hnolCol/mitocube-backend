import pandas as pd
import requests

Base_URL = "http://localhost:5002/api/annotations"

Token =  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0YWciOiJXWDlyNXpRSiIsInZlcmlmaWVkIjp0cnVlLCJ2ZXJpZmllZF9hdCI6MTc2ODQ3NjkxMDk3NS45MTQsImV4cCI6MTc2ODY0OTcxMH0.0MeUtEgr29e_KqO7gi3eWDrmnOSXFqodYXuBNW7Jtpg"

Headers = {"Authorization": f"Bearer {Token}"}

Annotation_file = "/Users/PParsa/Downloads/Human.MitoCarta3.0-2.xls"

df = pd.read_excel( Annotation_file, sheet_name="A Human MitoCarta3.0")


def explode(value):
    if pd.isna(value):
        return []
    return [v.strip() for v in str(value).split("|") if v.strip()]


annotations = requests.get(Base_URL, headers=Headers).json()



for i, row in df.iterrows():
    # if i > 1:   
    #     break

    uniprot = row["UniProt"]
    if pd.isna(uniprot):
        continue

    for pathway in explode(row["MitoCarta3.0_MitoPathways"]):
        r = requests.post(
            Base_URL,
            headers=Headers,
            json={
                "text": pathway,
                "description": pathway,
                "group_tag": "bgsLD",
                "protein_tags": [str(uniprot).strip()]
            }
        )


