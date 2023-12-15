from fastapi import APIRouter, Depends

import pandas as pd 
from typing import Dict 
from config.models.user import BasicUserWithEmail
from config.models.annotations.feature import FeatureDataResponseModel
from lib.data.annotations.ABCAnnotations import AnnotationDatabase
from services.users import get_user_from_token

from lib.data.database.ABCDatabase import MCDatabase
from lib.data.transform.FeatureData import FeatureData


router = APIRouter(
    prefix="/api/features",
    tags=["Features"]
    )

@router.get("/{feature_id}/data",
            response_model=FeatureDataResponseModel)
def get_dataset_data(feature_id : str, user : BasicUserWithEmail = Depends(get_user_from_token)):
    """
    Returns the data for a specific feature.
    """

    db = MCDatabase.getDatabase()
    dataset_labels = db.getDataLabels()
    feature_data_by_dataset_label : Dict[str,pd.DataFrame] = {}
    attributes_sample_by_dataset_label : Dict[str,Dict] = {}

    for label in dataset_labels:
        dataset = db.getDataset(label=label)
        feature_data, attributes_samples = FeatureData(dataset).transform(feature_id)
        if not feature_data.empty and isinstance(feature_data,pd.DataFrame):
            feature_data_by_dataset_label[label] = feature_data
            attributes_sample_by_dataset_label[label] = attributes_samples

    return {"feature_id": feature_id,
            "dataset_labels" : list(feature_data_by_dataset_label.keys()),
            "data" : dict([(data_label,data_frame.reset_index(names="index").to_dict(orient="records")) for data_label, data_frame in feature_data_by_dataset_label.items()]),
            "attributes_samples" : attributes_sample_by_dataset_label}


@router.get("/{feature_id}/annotation",
            summary="Returns the stored annotations in the annotation database.")
def get_feature_annotation(feature_id : str, user : BasicUserWithEmail = Depends(get_user_from_token)):
    """
    Returns the annotation for a specific feature.
    Please use the api endpoint /annotations to submit a list of feature_ids to 
    retrieve annotations efficiently. 
    """

    db_annotations = AnnotationDatabase()
    annotations = db_annotations.getAnnotations(feature_key=feature_id)  # ToDo: What return Model is needed by GUI?
    # ToDo: Request particular Annotation
    # {'KeywordAnnotation_9606': ['3D-structure', 'Alternative splicing', ...],
    #  'GOAnnotation_9606': ['Bcl-2 family protein complex [GO:0097136]', 'centrosome [GO:0005813]', ...]}

    return {"feature_id" : "Q9Y4W6", "aa_sequence" : """MAHRCLRLWGRGGCWPRGLQQLLVPGGVGPGEQPCLRTLYRFVTTQARASRNSLLTDIIAAYQRFCSRPPKGFEKYFPNGKNGKKASEPKEVMGEKKESKPAATTRSSGGGGGGGGKRGG
KKDDSHWWSRFQKGDIPWDDKDFRMFFLWTALFWGGVMFYLLLKRSGREITWKDFVNNYL
SKGVVDRLEVVNKRFVRVTFTPGKTPVDGQYVWFNIGSVDTFERNLETLQQELGIEGENR
VPVVYIAESDGSFLLSMLPTVLIIAFLLYTIRRGPAGIGRTGRGMGGLFSVGETTAKVLK
DEIDVKFKDVAGCEEAKLEIMEFVNFLKNPKQYQDLGAKIPKGAILTGPPGTGKTLLAKA
TAGEANVPFITVSGSEFLEMFVGVGPARVRDLFALARKNAPCILFIDEIDAVGRKRGRGN
FGGQSEQENTLNQLLVEMDGFNTTTNVVILAGTNRPDILDPALLRPGRFDRQIFIGPPDI
KGRASIFKVHLRPLKLDSTLEKDKLARKLASLTPGFSGADVANVCNEAALIAARHLSDSI
NQKHFEQAIERVIGGLEKKTQVLQPEEKKTVAYHEAGHAVAGWYLEHADPLLKVSIIPRG
KGLGYAQYLPKEQYLYTKEQLLDRMCMTLGGRVSEEIFFGRITTGAQDDLRKVTQSAYAQ
IVQFGMNEKVGQISFDLPRQGDMVLEKPYSEATARLIDDEVRILINDAYKRTVALLTEKK
ADVEKVALLLLEKEVLDKNDMVELLGPRPFAEKSTYEEFVEGTGSLDEDTSLPEGLKDWN
KEREKEKEEPPGEKVAN"""}