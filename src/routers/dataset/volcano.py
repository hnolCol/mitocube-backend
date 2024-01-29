from fastapi import APIRouter, Depends, HTTPException
from collections import OrderedDict
from config.enums.users.roles import UserRolesEnum
from config.models.user import UserModel

from config.models.dataset.data import DatasetPCAResponse
from config.models.submissions.submissions import DatasetSubmissionModel, DatasetSubmissionResponseModel
from config.models.submissions.runs import RunListModel, RunListRequestPropsModel
from config.models.annotations.feature import FeatureModel

from lib.data.database.ABCDatabase import MCDatabase, MCAttributes
from lib.data.annotations.ABCAnnotations import PandaFeatureDatabase
from lib.data.transform.PCA import PCATransform
from lib.data.transform.FeatureData import FeatureData
from lib.data.filter.NoMissingValues import NoNaNFilter
from lib.data.statistic.Ttest import Ttest
from lib.data.clustering.HierarchicalClustering import HierarchicalClustering
from config.exceptions.HTTPExceptions import no_data_found

from services.users import get_user_from_token, is_user_at_least_curator
from services.submission import map_tags_to_attributes
import pandas as pd 


router = APIRouter(
    prefix="/api",
    tags=["Heatmap"]
)


#volcano plot
@router.get("/datasets/{dataset_label}/volcano")
def get_dataset_volcano(dataset_label : str, user : UserModel = Depends(get_user_from_token)):
    """
    Returns the result of a volcano plot
    """
    db = MCDatabase.getDatabase()
    dataset = db.getDataset(dataset_label)
    if dataset is None:
        raise HTTPException(status_code=400,detail="Data not found for given label.")
    if not dataset.hasData(): raise HTTPException(status_code=404,detail=f"No datatable found for the dataset {dataset_label}.")
    metadata = dataset.getMetaJson()
    proteome_id =  metadata.dataset_attributes["att_organism"][0].split(":")[1].upper()
    stats = Ttest(dataset).get_stats()
   
    feature_db = PandaFeatureDatabase()
    features = feature_db.get(stats.index,proteome_id,ignoreMissing=True)
    stats_and_feature_data = stats.join(features,how="left")
    return stats_and_feature_data.to_dict(orient="records")
    