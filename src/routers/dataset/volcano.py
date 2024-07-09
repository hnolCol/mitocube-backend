from fastapi import APIRouter, Depends, HTTPException
from collections import OrderedDict
from config.enums.users.roles import UserRolesEnum
from config.models.user import UserModel

from config.models.parameter import APIParamString
from config.models.dataset.data import DatasetPCAResponse
from config.models.submissions.submissions import DatasetSubmissionModel, DatasetSubmissionResponseModel
from config.models.submissions.runs import RunListModel, RunListRequestPropsModel
from config.models.annotations.feature import FeatureModel



from lib.data.database.Database import Database 
from lib.data.database.ABCDatabase import MCDatabase, MCAttributes
from lib.data.genotype.ABCGenotypeDatabase import MCGenotypes
from lib.data.annotations.ABCAnnotations import PandaFeatureDatabase
from lib.data.transform.PCA import PCATransform
from lib.data.transform.FeatureData import FeatureData
from lib.data.filter.NoMissingValues import NoNaNFilter
from lib.data.statistic.Ttest import Ttest
from lib.data.clustering.HierarchicalClustering import HierarchicalClustering
from lib.data.imputation.StandardImputation import StandardImputation
from config.exceptions.HTTPExceptions import no_data_found_http_exception

from services.users import get_user_from_token, is_user_at_least_curator
from services.submission import map_tags_to_attribute_in_metadata
from services.attributes import get_suffix_from_attributes_and_attribute_tags

DB = Database.DB()

router = APIRouter(
    prefix="/api",
    tags=["Heatmap"]
)


#volcano plot
@router.get("/datasets/{dataset_tag}/volcano")
def get_dataset_volcano(dataset_tag : str, attribute_value_tag_left : str, attribute_value_tag_right : str, sample_attribute_tag : str, within_attribute_tag : str = None,
                  within_attribute_value_tag : str = None, impute : bool = True,
                  filter_tag : str = None, 
                  ):# ):#) #user : UserModel = Depends(get_user_from_token)
    """
    Returns the result for a volcano plot
    """
    
    data_exist = DB.dataset_has_data(tag = dataset_tag)
    if not data_exist: return no_data_found_http_exception

    
    # db = MCDatabase.getDatabase()
    # attributes_db = MCAttributes.getAttributeDatabase()
    # feature_db = PandaFeatureDatabase()
    # genotype_db = MCGenotypes.getGenotypeDatabase()
    
    within_attribute_tag = APIParamString(param=within_attribute_tag).param 
    within_attribute_value_tag = APIParamString(param=within_attribute_value_tag).param 
    
    comparison_suffix = "" #get_suffix_from_attributes_and_attribute_tags(sample_attribute_tag,attribute_value_tag_left,attribute_value_tag_right,attributes_db,genotype_db,feature_db,within_attribute_tag=within_attribute_tag,within_attribute_value_tag=within_attribute_value_tag)
    datatable = DB.get_dataset_table(tag = dataset_tag)
    sample_attributes, sample_map = DB.meta.get_sample_attributes_and_genotypes(dataset_tag)     
    stats = Ttest(datatable,sample_map).get_stats(sample_attribute_tag=sample_attribute_tag, 
                                     attribute_value_left=attribute_value_tag_left, 
                                     attribute_value_right=attribute_value_tag_right, suffix = comparison_suffix, 
                                     impute = impute,
                                     within_attribute_tag=within_attribute_tag,
                                     within_attribute_value_tag=within_attribute_value_tag)

    
    features = DB.features.get_protein_by_tags(tags = datatable.index.to_list(), as_data_frame=True)
    #join features to the stat results
    stats_and_feature_data = stats.join(features,how="left").reset_index()
    stats_and_feature_data.rename(columns={"Key":"key"}, inplace=True)
    return {"stats" : stats_and_feature_data.to_dict(orient="records"), "suffix" : comparison_suffix}
    