from fastapi import APIRouter , Depends 

from typing import List

from config.models.user import User
from config.models.attributes import Attribute, AttributeValue, AttributeResponse
from lib.data.database.ABCDatabase import MCDatabase

from services.users import get_user_from_token

import pandas as pd 

router = APIRouter(
    prefix="/api",
    tags=["Attributes"]
    )


##load fake features for testing!!! DELTE
A = pd.read_csv("/Users/hnolte/Documents/GitHub/mitocube-backend/resources/annotations/UP000000589/data.txt",sep="\t", index_col="Entry")
A = A.rename(columns={"Gene Names" : "gene_name","Protein names":"protein_name","Length" : "length","Organism":"organism"})
A.index.rename(name = "uniprot_id",inplace=True)

feature_attr = [AttributeValue(id = n,
                           tag = f"att_feature:{x['uniprot_id']}",
                           attribute_id= -1,
                           name = f"{x['gene_name']} - {x['uniprot_id']}", 
                           details=f"{x['organism']}-{x['protein_name']}") for n,x in enumerate(A.reset_index().to_dict(orient="records"))]


@router.get("/attributes", response_model=AttributeResponse)
def get_attributes(user : User = Depends(get_user_from_token)) -> AttributeResponse:
    """
    Returns the stored attributes 
    """
    db  = MCDatabase.getDatabase()
    attributes = db.attributes
    attribute_values = db.attribute_values 
    #print([Attribute(**x) for x in attributes.to_dict(orient="records")])
    return {"attributes" : [Attribute(**x) for x in attributes.to_dict(orient="records")], "attribute_values" : attribute_values.to_dict(orient="records")}

@router.post("/attributes")
def add_attribute(attribute : Attribute) -> List[Attribute]:
    """Adds an attribute and returns the updated list"""
    return []


@router.get("/attributes/{attribute_id}")
def get_attribute_by_id(attribute_id : str) -> Attribute:
    """
    Returns the attribute by its ID
    """
    return {}

@router.get("/attributes/{attribute_name}")
def get_attribute_by_name(attribute_name : str) -> Attribute:
    """
    Returns attribute by its name
    """
    return {}

@router.delete("/attributes/{attribute_id}")
def delete_attribute_by_id(attribute_id : str) -> dict:
    """Deletes an attribute by ID"""
    return {}


