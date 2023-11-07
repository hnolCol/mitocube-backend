
from fastapi import APIRouter , Depends 

from typing import List
from config.models.user import User
from config.models.annotations.feature import Feature 
from config.models.attributes import AttributeValue
from services.users import get_user_from_token

import pandas as pd 

router = APIRouter(
    prefix="/api/annotations",
    tags=["Attributes"]
    )

 ##load fake features 
A = pd.read_csv("/Users/hnolte/Documents/GitHub/mitocube-backend/resources/annotations/UP000000589/data.txt",sep="\t", index_col="Entry")
A = A.rename(columns={"Gene Names" : "gene_name","Protein names":"protein_name","Length" : "length","Organism":"organism"})
A.index.rename(name = "uniprot_id",inplace=True)

@router.get('/features', summary="Returns all features that are present in the database (uniprot downloaded for available organisms).", response_model=List[Feature])
def get_features_in_database(user : User =  Depends(get_user_from_token)) :
    """"""
    return [Feature(**x) for x in A.reset_index().to_dict(orient="records")]

@router.get('/features/attributeValues', summary="Returns all features that are present in the database in the format for attribute value selection.", response_model=List[AttributeValue])
def get_features_in_database_as_values(user : User =  Depends(get_user_from_token)) :
    """"""

    return [AttributeValue(id = n,
                           tag = f"att_feature:{x['uniprot_id']}",
                           attribute_id= -1,
                           name = f"{x['gene_name']}", 
                           details=f"{x['uniprot_id']}, {x['organism']}, {x['protein_name']}") for n,x in enumerate(A.reset_index().to_dict(orient="records"))]
