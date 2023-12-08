from fastapi import APIRouter, Depends

import pandas as pd 

from config.models.user import User 
from config.models.feature import FeatureDataResponse
from services.users import get_user_from_token

from lib.data.database.ABCDatabase import MCDatabase
from lib.data.transform.FeatureData import FeatureData


router = APIRouter(
    prefix="/api/features",
    tags=["Features"]
    )

@router.get("/{feature_id}/data", response_model=FeatureDataResponse)
def get_dataset_data(feature_id : str, user : User = Depends(get_user_from_token)):
    """
    Returns the data for a specific feature.
    """

    db = MCDatabase.getDatabase()
    dataset_labels = db.getAllDataLabels()
    feature_data_by_dataset_label = {}
    attributes_sample_by_dataset_label = {}

    for label in dataset_labels:
        dataset = db.getDataset(label=label)
        feature_data, attributes_samples = FeatureData(dataset).transform(feature_id)
        if not feature_data.empty:
            feature_data_by_dataset_label[label] = feature_data
            attributes_sample_by_dataset_label[label] = attributes_samples

    return {"feature_id": feature_id,
            "dataset_labels" : list(feature_data_by_dataset_label.keys()),
            "data" : feature_data_by_dataset_label,
            "attributes_samples" : attributes_sample_by_dataset_label}


@router.get("/{feature_id}/annotation", summary="Returns the stored annotations in the annotation database.")
def get_feature_annotation(user : User = Depends(get_user_from_token)):
    """
    Returns the annotation for a specific feature.
    Please use the api endpoint /annotations to submit a list of feature_ids to 
    retrieve annotations efficiently. 
    """
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