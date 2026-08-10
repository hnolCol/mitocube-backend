from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from typing import List, Literal
import httpx
# 
from lib.database.Database import Database
import pandas as pd 
from config.models.user import UserModel
# from config.models.attributes import AttributeValueModel
# from config.enums.states import SubmissionStatesEnums
from config.models.news.news import  NewsModel, NewsInsertModel
from config.models.parameter import APIParamString
from services.users import is_user_admin, get_user_from_token, is_user_at_least_curator
from config.enums.states import SubmissionStatesEnums 
from config.models.plots.stats import DistResponseModel
from config.models.feature import FeatureNeoModel
DB = Database.DB()


router = APIRouter(
    prefix="/api/features/proteins",
    tags=["Features", "Proteins"]
    )


@router.get("/{tag}", summary="Returns the protein information model.")
def get_protein_features(tag: str, user: UserModel = Depends(get_user_from_token)) -> FeatureNeoModel:
    """
    Returns the protein information model.
    
    Parameters
    ----------
    tag : str
        The tag of the protein to retrieve.
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(get_user_from_token)
    Returns
    -------
    FeatureNeoModel
        The protein information model.
    """
    if not DB.proteins.exists(tag = tag):
        raise HTTPException(status_code=404, detail=f"No protein found for tag {tag}")
    return DB.proteins.get(tag = tag)
    

@router.get("/{tag}/interpro")
def get_protein_interpro_features(tag: str, user: UserModel = Depends(get_user_from_token)) -> list:
    """Fetches domain/feature annotations for a UniProt accession from InterPro."""
    try:
        with httpx.Client(http2=True, timeout=20) as client:
            r = client.get(
                f"https://www.ebi.ac.uk/interpro/api/entry/all/protein/uniprot/{tag}/",
                params={"format": "json", "page_size": 200},
                headers={"Accept": "application/json"},
            )
            if r.status_code != 200:
                return []

            features = []
            for entry in r.json().get("results", []):
                meta = entry.get("metadata", {})
                name = meta.get("name", "")
                entry_type = meta.get("type", "")
                source_db = meta.get("source_database", "")
                for protein in entry.get("proteins", []):
                    for location in protein.get("entry_protein_locations", []):
                        for fragment in location.get("fragments", []):
                            start = fragment.get("start")
                            end = fragment.get("end")
                            if start is None or end is None:
                                continue
                            features.append({
                                "source": source_db,
                                "type": entry_type,
                                "name": name,
                                "start": int(start),
                                "end": int(end),
                            })
            return features

    except Exception as e:
        print(f"Error fetching InterPro features for {tag}: {e}")
        return []
    

@router.get("/{tag}/topology")
def get_protein_topology(tag: str, user: UserModel = Depends(get_user_from_token)) -> dict:
    """Fetches transmembrane and topological domain annotations for a UniProt accession."""
    try:
        with httpx.Client(http2=True, timeout=20) as client:
            r = client.get(
                f"https://rest.uniprot.org/uniprotkb/{tag}.json",
                headers={"Accept": "application/json"},
            )
            if r.status_code != 200:
                return {"length": None, "tm_segments": [], "topological_domains": []}

            data = r.json()

        features = data.get("features", [])

        tm_segments = []
        topological_domains = []
        for f in features:
            f_type = f.get("type")
            location = f.get("location", {})
            start = location.get("start", {}).get("value")
            end = location.get("end", {}).get("value")
            if start is None or end is None:
                continue

            if f_type == "Transmembrane":
                tm_segments.append({
                    "start": int(start),
                    "end": int(end),
                    "description": f.get("description"),
                })
            elif f_type == "Topological domain":
                topological_domains.append({
                    "start": int(start),
                    "end": int(end),
                    "label": f.get("description"),
                })

        return {
            "length": data.get("sequence", {}).get("length"),
            "tm_segments": tm_segments,
            "topological_domains": topological_domains,
        }

    except Exception as e:
        print(f"Error fetching UniProt topology for {tag}: {e}")
        return {"length": None, "tm_segments": [], "topological_domains": []}
    

@router.get("/{tag}/structure")
def get_protein_structure(tag: str, user: UserModel = Depends(get_user_from_token)) -> dict:
    """Fetches AlphaFold structure metadata (model URL, confidence) for a UniProt accession."""
    try:
        with httpx.Client(http2=True, timeout=20) as client:
            r = client.get(f"https://alphafold.ebi.ac.uk/api/prediction/{tag}")
            if r.status_code != 200:
                return {"available": False}

            results = r.json()
            if not results:
                return {"available": False}

            entry = results[0]
            return {
                "available": True,
                "cif_url": entry.get("cifUrl"),
                "pdb_url": entry.get("pdbUrl"),
                "model_version": entry.get("modelCreatedDate"),
            }

    except Exception as e:
        print(f"Error fetching AlphaFold structure for {tag}: {e}")
        return {"available": False}