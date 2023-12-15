
from fastapi import APIRouter , Depends 

from typing import List

# from lib.data.annotations.ABCAnnotations import AnnotationSettings

from config.models.user import BasicUserWithEmail
from config.models.annotations.feature import FeatureModel
from config.models.attributes import AttributeValueModel, AttributeModel
from lib.data.annotations.ABCAnnotations import PandaFeatureDatabase
from services.users import get_user_from_token

import pandas as pd 

router = APIRouter(
    prefix="/api/annotations",
    tags=["Attributes"]
    )


@router.get('/features',  # /api/annotations/features
            summary="Returns all features that are present in the database (uniprot downloaded for available organisms).",
            response_model=List[FeatureModel])
def get_features_in_database(organism : AttributeModel, user : BasicUserWithEmail = Depends(get_user_from_token)) :
    """Returns all features that are present in the database (uniprot downloaded for available organisms)."""

    db_features = PandaFeatureDatabase()
    features = db_features.get()

    # features = features[features["organism_id"] == ???]  # ToDo: Select for Organism if provided
    # features = features[features["organism"] == ???]

    # "entry": "uniprot_id", "organism": "organism", "mass": "mass", "organism_id": "organism_id",
    features.rename(columns={"key": "uniprot_id", "proteins": "protein_name", "genes": "gene_name", "aa_length": "length"},
                    inplace=True)  # Other Columns: "entry": "uniprot_id", "organism": "organism", "mass": "mass", "organism_id": "organism_id",

    features = features.to_dict(orient="records")  # [{'col1': 1, 'col2': 0.5}, {'col1': 2, 'col2': 0.75}]

    return [FeatureModel(**item) for item in features]


@router.post('/features/attributeValues',  # /api/annotations/features/attributeValues
             summary="Returns all features that are present in the database in the format for attribute value selection.",
             response_model=List[AttributeValueModel])
def get_features_in_database_as_values(organisms : List[AttributeModel], user : BasicUserWithEmail = Depends(get_user_from_token)) :
    """Returns all features that are present in the database in the format for attribute value selection."""
    ## add controls somewhere else!! -> in annotation datasets.
    CONTORLS = [AttributeValueModel(attribute_id=-1, tag=f"att_feature:GFP", name ="GFP", details="GFP Proteins (knock-down control)", id=-2),
                AttributeValueModel(attribute_id=-1, tag=f"att_feature:scr", name ="Scrambled", details="Scrambled Protein Sequence", id=-3),
                AttributeValueModel(attribute_id=-1, tag=f"att_feature:ctrl", name ="Control", details="Control sgRNA or siRNA", id=-4),
                AttributeValueModel(attribute_id=-1, tag=f"att_feature:fluc", name ="FLUC", details="FLUC Protein", id=-1),
                AttributeValueModel(attribute_id=-1, tag=f"att_feature:rluc", name ="RLUC", details="RLUC Protein as a control", id=-5)]
    # db = AnnotationSettings.get_annotation_db()

    # annotations = []
    # for organism in organisms:
    #     organism_id = organism.tag.split(":")[-1].upper()
    #     a = db.get_features_by_organism(organism_id)
    #     annotations.append(a)
    # A = pd.concat(annotations,axis=0,join="outer")
    return {}  # CONTORLS + [AttributeValue(id = n,
    #                       tag = f"att_feature:{x['uniprot_id']}",
    #                       attribute_id= -1,
    #                       name = f"{x['Gene Names']}",
    #                       details=f"{x['uniprot_id']}, {x['Organism']}, {x['Protein names']}") for n,x in enumerate(A.reset_index().to_dict(orient="records"))]
