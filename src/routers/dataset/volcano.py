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
from services.submission import map_tags_to_attribute_in_metadata
import pandas as pd 


router = APIRouter(
    prefix="/api",
    tags=["Heatmap"]
)


#volcano plot
@router.get("/datasets/{dataset_label}/volcano")
def get_dataset_volcano(dataset_label : str, attribute_left_tag : str, attribute_right_tag : str, sample_attribute_tag : str, user : UserModel = Depends(get_user_from_token)):#)
    """
    Returns the result for a volcano plot
    """
    db = MCDatabase.getDatabase()
    db_attributes = MCAttributes.getAttributeDatabase()
    dataset = db.getDataset(dataset_label)
    if dataset is None:
        raise HTTPException(status_code=400,detail="Data not found for given label.")
    if not dataset.hasData(): raise HTTPException(status_code=404,detail=f"No datatable found for the dataset {dataset_label}.")
    metadata = dataset.getMetaJson()
    #adjust proteome_id extraction
       
    attribute_values = db_attributes.getAttributeValues(tags=[attribute_left_tag,attribute_right_tag]).set_index("tag", drop=False)
    attribute = db_attributes.getAttributes(tags=[sample_attribute_tag])
    comparison_suffix = f"{attribute_values.loc[attribute_left_tag,'text']} vs {attribute_values.loc[attribute_right_tag,'text']}"
    
    proteome_ids =  [organism.split(":")[1] for organism in metadata.dataset_attributes["att_organism"]]
    stats = Ttest(dataset).get_stats(sample_attribute_tag=sample_attribute_tag, 
                                     attribute_value_left=attribute_left_tag, 
                                     attribute_value_right=attribute_right_tag, suffix = comparison_suffix )

    print(stats)
    print(comparison_suffix)
    feature_db = PandaFeatureDatabase()
    features = feature_db.get(stats.index,proteome_ids,ignoreMissing=True)
    #join features to the stat results
    stats_and_feature_data = stats.join(features,how="left").reset_index()
    stats_and_feature_data.rename(columns={"Key":"key"}, inplace=True)
    return {"stats" : stats_and_feature_data.to_dict(orient="records"), "suffix" : comparison_suffix}
    