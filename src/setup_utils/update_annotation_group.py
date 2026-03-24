import io
import gzip
import re
import requests
import pandas as pd
from collections import defaultdict
from config.models.annotations.annotations import AnnotationsModel

def get_cursor_from_header_link(link: str) -> str:
    """Gets the cursor from a header link when pagination is used"""
    cursor = re.search('cursor=(.*)&', link).group(0)[:-1]
    return cursor.split("=")[1]


def update_annotations_from_group_url(group, annotations_db):

    if not group.url:
        raise ValueError("Annotation group has no URL")

    params = {}   
    total_rows = 0

    while True:
        r = requests.get(
            group.url,
            params=params,
            headers={
                "Accept": "text/tab-separated-values",
            },
            timeout=60,
        )
        r.raise_for_status()

        content = r.content
        if r.headers.get("Content-Encoding") == "gzip":
            content = gzip.decompress(content)
        
        text = content.decode("utf-8")

        first_line = text.splitlines()[0]
        if "\t" not in first_line:
            raise ValueError(
                "URL did not return TSV.\n"
                f"First line:\n{first_line}"
            )

        df = pd.read_csv(io.StringIO(text), sep="\t")

        if df.shape[1] < 2:
            raise ValueError("URL must return at least two columns")

        protein_col = df.columns[0]
        annotation_col = df.columns[1]

        annotations = defaultdict(set)

        for _, row in df.iterrows():
            protein = row[protein_col]
            terms = row[annotation_col]

            if pd.isna(protein) or pd.isna(terms):
                continue

            for term in str(terms).split(";"):
                term = term.strip()
                if term:
                    annotations[term].add(protein)

        for text, proteins in annotations.items():
            if annotations_db.get_text(group.tag, text):
                continue

        annotations_db.insert(
                AnnotationsModel(
                    text=text,
                    description=text,
                    group_tag=group.tag,
                    protein_tags=list(proteins),
                    source=group.source,
                )
        )

        total_rows += df.shape[0]
        print(f"Processed {total_rows} rows")

        
        if "Link" not in r.headers:
            break

        cursor = get_cursor_from_header_link(r.headers["Link"])
        params["cursor"] = cursor

    return True
