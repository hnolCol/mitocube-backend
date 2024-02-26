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
from lib.data.imputation.StandardImputation import StandardImputation
from config.exceptions.HTTPExceptions import no_data_found

from services.users import get_user_from_token, is_user_at_least_curator
from services.submission import map_tags_to_attribute_in_metadata



router = APIRouter(
    prefix="/api",
    tags=["Heatmap"]
)


#volcano plot
@router.get("/datasets/{dataset_label}/volcano")
def get_dataset_volcano(dataset_label : str, attribute_left_tag : str, attribute_right_tag : str, sample_attribute_tag : str, within_sample_attribute_tag : str = None,
                  within_sample_attribute_value_tag : str = None, impute : bool = True):# user : UserModel = Depends(get_user_from_token)):#)
    """
    Returns the result for a volcano plot
    """
    db = MCDatabase.getDatabase()
    db_attributes = MCAttributes.getAttributeDatabase()
    feature_db = PandaFeatureDatabase()
    dataset = db.getDataset(dataset_label)
    if dataset is None:
        raise HTTPException(status_code=400,detail="Data not found for given label.")
    if not dataset.hasData(): raise HTTPException(status_code=404,detail=f"No datatable found for the dataset {dataset_label}.")
    metadata = dataset.getMetaJson()
    #adjust proteome_id extraction
    proteome_ids =  [organism.split(":")[1] for organism in metadata.dataset_attributes["att_organism"]]
    attribute_values = db_attributes.getAttributeValues(tags=[attribute_left_tag,attribute_right_tag,within_sample_attribute_value_tag]).set_index("tag", drop=False)
    attribute = db_attributes.getAttributes(tags=[sample_attribute_tag,within_sample_attribute_tag]).set_index("tag")
    
    if attribute_left_tag not in attribute_values.index or attribute_right_tag not in attribute_values.index:
        comparison_suffix = f"{attribute_left_tag} vs {attribute_right_tag}"
    else:
        comparison_suffix = f"{attribute_values.loc[attribute_left_tag,'text']} vs {attribute_values.loc[attribute_right_tag,'text']}"
    
    if within_sample_attribute_tag is not None and within_sample_attribute_value_tag is not None:
        within_attribute_text = ""
        within_attribute_value_text = ""
        if within_sample_attribute_tag not in attribute.index: raise HTTPException(status_code=404,detail="Within attribute tag not found")
        
        within_attribute_text = attribute.loc[within_sample_attribute_tag,"text"]
        if attribute.loc[within_sample_attribute_tag,"has_features_value"]:
            feature = feature_db.get(keys=[within_sample_attribute_value_tag.split(":")[1]],ignoreMissing=True)
            within_attribute_value_text = feature.loc[:,"genes"].values[0].split(" ")[0]
        elif attribute.loc[within_sample_attribute_tag,"has_numeric_value"]:
            within_attribute_value_text = within_sample_attribute_tag.split(":")[-1]
        elif within_sample_attribute_value_tag in attribute_values.index:
            within_attribute_value_text = attribute_values.loc[within_sample_attribute_value_tag,"text"]
        
        comparison_suffix += f"({within_attribute_text}:{within_attribute_value_text})"
        
    stats = Ttest(dataset).get_stats(sample_attribute_tag=sample_attribute_tag, 
                                     attribute_value_left=attribute_left_tag, 
                                     attribute_value_right=attribute_right_tag, suffix = comparison_suffix, 
                                     impute = impute,
                                     within_sample_attribute_tag=within_sample_attribute_tag,
                                     within_sample_attribute_value_tag=within_sample_attribute_value_tag)

    
    features = feature_db.get(stats.index,proteome_ids,ignoreMissing=True)
    #join features to the stat results
    stats_and_feature_data = stats.join(features,how="left").reset_index()
    stats_and_feature_data.rename(columns={"Key":"key"}, inplace=True)
    return {"stats" : stats_and_feature_data.to_dict(orient="records"), "suffix" : comparison_suffix}
    