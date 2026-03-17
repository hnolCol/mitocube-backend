import requests
from typing import List, Literal

def get_pubmed_ids_by_query(query, limit=5, field: str = "title_abstract", sort : Literal["pub_date", "relevance", "author"] = "pub_date"):
    params = {
        "retmode": "json",
        "sort": sort,
        "retmax": limit,
        "db": "pubmed",
        "term": f"{query}[{field}]" if field is not None else query,
    }


    resp = requests.get(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
        params=params
    )
    resp.raise_for_status()
    return resp.json()




def get_pubmed_article_text_by_id(pubmedids : List[str]):
    resp = requests.get(
        # "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
        params={"db": "pubmed", "id": ",".join(pubmedids), "retmode": "text", "rettype": "abstract"},
    )
    resp.raise_for_status()
    return resp.text


def get_pubmed_publications(pubmedids : List[str]):
    """
    Thin wrapper kept for API compatibility with the previous frontend hook.
    """
    return get_pubmed_article_text_by_id(pubmedids)