from fastapi import APIRouter, Depends, HTTPException
from collections import OrderedDict
from config.enums.users.roles import UserRolesEnum
from config.models.user import UserModel

from config.models.dataset.data import DatasetPCAResponse
from config.models.submissions.submissions import DatasetSubmissionModel, DatasetSubmissionResponseModel
from config.models.submissions.runs import RunListModel, RunListRequestPropsModel
from config.models.annotations.feature import FeatureModel

from lib.data.database.ABCDatabase import MCDatabase, MCAttributes
from lib.data.genotype.ABCGenotypeDatabase import MCGenotypes
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
from services.attributes import get_suffix_from_attributes_and_attribute_tags


router = APIRouter(
    prefix="/api",
    tags=["Heatmap"]
)


#volcano plot
@router.get("/datasets/{dataset_label}/volcano")
def get_dataset_volcano(dataset_label : str, attribute_value_tag_left : str, attribute_value_tag_right : str, sample_attribute_tag : str, within_attribute_tag : str = None,
                  within_attribute_value_tag : str = None, impute : bool = True, split_string : str = ";"):# user : UserModel = Depends(get_user_from_token)):#)
    """
    Returns the result for a volcano plot
    """
    db = MCDatabase.getDatabase()
    attributes_db = MCAttributes.getAttributeDatabase()
    feature_db = PandaFeatureDatabase()
    genotype_db = MCGenotypes.getGenotypeDatabase()
    
    within_attribute_tag = within_attribute_tag.split(split_string) if within_attribute_tag is not None else []
    within_attribute_value_tag = within_attribute_value_tag.split(split_string) if within_attribute_value_tag is not None else []
    
    
    dataset = db.getDataset(dataset_label)
    if dataset is None:
        raise HTTPException(status_code=400,detail="Data not found for given label.")
    if not dataset.hasData(): raise HTTPException(status_code=404,detail=f"No datatable found for the dataset {dataset_label}.")
    metadata = dataset.getMetaJson()
    #adjust proteome_id extraction
    proteome_ids =  [organism.split(":")[1] for organism in metadata.dataset_attributes["att_organism"]]
    
    comparison_suffix = get_suffix_from_attributes_and_attribute_tags(sample_attribute_tag,attribute_value_tag_left,attribute_value_tag_right,attributes_db,genotype_db,feature_db,within_attribute_tag=within_attribute_tag,within_attribute_value_tag=within_attribute_value_tag)
            
    stats = Ttest(dataset).get_stats(sample_attribute_tag=sample_attribute_tag, 
                                     attribute_value_left=attribute_value_tag_left, 
                                     attribute_value_right=attribute_value_tag_right, suffix = comparison_suffix, 
                                     impute = impute,
                                     within_attribute_tag=within_attribute_tag,
                                     within_attribute_value_tag=within_attribute_value_tag)

    
    features = feature_db.get(stats.index,proteome_ids,ignoreMissing=True)
    #join features to the stat results
    stats_and_feature_data = stats.join(features,how="left").reset_index()
    stats_and_feature_data.rename(columns={"Key":"key"}, inplace=True)
    return {"stats" : stats_and_feature_data.to_dict(orient="records"), "suffix" : comparison_suffix}
    