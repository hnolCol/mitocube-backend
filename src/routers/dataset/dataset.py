from fastapi import APIRouter, Depends, HTTPException
import pandas as pd 
import numpy as np 
from typing import List, Dict 
from config.enums.users.roles import UserRolesEnum
from config.models.user import UserModel
from config.models.parameter import APIParamString
from config.models.dataset.data import DatasetPCAResponse
from config.models.submissions.submissions import DatasetSubmissionModel, DatasetSubmissionResponseModel, MinimalMetadataResponseModel
from config.models.submissions.runs import RunListModel, RunListRequestPropsModel
from config.models.annotations.feature import FeatureModel

from lib.data.database.ABCDatabase import MCDatabase, MCAttributes
from lib.data.database.Database import Database
from lib.data.annotations.ABCAnnotations import PandaFeatureDatabase
from lib.data.transform.PCA import PCATransform
from lib.data.transform.FeatureData import FeatureData
from lib.data.filter.NoMissingValues import NoNaNFilter

from config.exceptions.HTTPExceptions import no_data_found_http_exception

from services.users import get_user_from_token, is_user_at_least_curator
from services.submission import map_tags_to_attribute_in_metadata, get_dataset_from_database

DB = Database.DB()


router = APIRouter(
    prefix="/api",
    tags=["Dataset"]
    )

@router.get("/datasets/{dataset_tag}/data", response_model=[])
def get_dataset_data(dataset_tag : str, user : UserModel = Depends(get_user_from_token)) -> List[Dict[str,str|float]]:
    """Returns the datatable of dataset by its tag. 

    Parameters
    ----------
    dataset_tag : str
        The tag associated with the dataset 

    Returns
    -------
    List[Dict[str,str|float]]
        The data as dicts using {tag : <uniprot_id>, sample_index : float (log2 value)}
        
    """
    if not DB.dataset_has_data(tag = dataset_tag): no_data_found_http_exception
    data_table = DB.get_dataset_table(tag = dataset_tag)
    return data_table.reset_index().to_dict(orient="records")

# class QCResponse(BaseModel):


@router.get("/datasets/{dataset_tag}/qc", 
            response_model=[], 
            summary="Quality control of data set. Includes a statistic summary.")
def get_dataset_qc(dataset_tag : str):
    """
    Returns the summary statistic data for a specific dataset
    TO DO : Add response model.
    """
    poi_data = []
    
    datatable = DB.get_datatable(tag = dataset_tag)
    #db = MCDatabase.getDatabase()
    print(dataset_tag)
    #dataset = db.getDataset(dataset_label)
    dataset_attributes = DB.meta.get_dataset_attributes(tag = dataset_tag)
    print(dataset_attributes)
    

    
    #TODO Check if proteome/organism is there, otherwise cause error 
    if "att_proteome" not in dataset_attributes:
        raise HTTPException(status_code=400,detail="No organism defined for this dataset.")
    
    proteome_tags =  dataset_attributes["att_proteome"]
    applicable_filters = DB.filters.get(proteome_tags=proteome_tags)
    features_in_filters = [(f.tag, DB.filters.isin(tag = f.tag, feature_tags=datatable.index.to_list())) for f in applicable_filters]
    print(features_in_filters)
    print(applicable_filters)
    
    if datatable is None or datatable.empty:
        raise no_data_found_http_exception
    data_summary = datatable.describe()
    data_summary.loc["total",:] = datatable.index.size

    if "att_poi" in dataset_attributes: 
        pois = dataset_attributes["att_poi"]
        ids = [poi.split(":")[-1].upper() for poi in pois]
        
        # feature_db = PandaFeatureDatabase()
        # features = feature_db.get(keys=ids,proteome_ids=proteome_ids).reset_index(names="key")
        # feature_annotations = features.to_dict(orient="records")
        # poi_data = [FeatureData(dataset).transform(id, add_annotations=True) for id in ids if id in datatable.index]

    return {"stats" : data_summary.to_dict(), 
            "poi_data" : [] } 
    #[{
           # "feature_key" : ids[n],
           # "feature_annotations" : FeatureModel(**feature_annotations[n], tag=f"att_poi:{feature_annotations[n]['key']}"),
           # "annotations" : {},
           # "data" : data.to_dict(orient="records"),
           # "samples_attributes" : samples_attributes} for n,(data, samples_attributes, annotations) in enumerate(poi_data)]
            #}



#parameter endpoints 
@router.get("/datasets/{dataset_tag}/meta",
            response_model=List[MinimalMetadataResponseModel]|MinimalMetadataResponseModel,
            tags=["Parameters","Meta data"])
def get_dataset_params(dataset_tag : str, user : UserModel = Depends(get_user_from_token)):
    """
    Returns the metadata associated to the dataset
    """
    
    meta = DB.meta.get(tags = APIParamString(param=dataset_tag).param)
    #if only a single meta data is requested, return it, otherwise return a list.
    if len(meta) == 1: return meta[0]
    return meta
    
    # db = MCDatabase.getDatabase()
    # dataset = get_dataset_from_database(db,dataset_tag)
    # metadata : DatasetSubmissionModel = dataset.getMetaJson()
    
    # return map_tags_to_attribute_in_metadata(metadata)


@router.get("/datasets/{dataset_tag}/meta/samples")
def get_dataset_sample_info(dataset_tag : str):
    """Retrieve the meta data annotations for 
    each sample. This includes the sample attributes and
    the genotypes

    Parameters
    ----------
    dataset_tag : str
        _description_

    Returns
    -------
    _type_
        _description_
    """
    
    if not DB.datasets.exists(tag = dataset_tag): no_data_found_http_exception
    
    sample_attributes, sample_map = DB.meta.get_sample_attributes_and_genotypes(dataset_tag)
    has_genotype = "att_genotype" in sample_map.columns
    attribute_tags = [attribute_tag for attribute_tag in sample_map.columns if attribute_tag not in ["sample_text"]]
    attribute_value_tags = pd.Series(sample_map.values.flatten()).unique().tolist()
    attributes = DB.attributes.get(tags = attribute_tags)
    attribute_values = DB.attributes.get_values(submission_tag = dataset_tag, tags = attribute_value_tags)
    if has_genotype:
        genotypes = DB.genotypes.get(tags = sample_map.loc[:,"att_genotype"].to_list())
        attribute_values.extend(genotypes)
    
    
    return {
        "sample_text" : sample_map.loc[:,"sample_text"].to_list(),
        "has_genotype" : has_genotype,
        "attribute_values" : attribute_values,
        "attributes" : attributes,
        "sample_attributes" : sample_attributes
    }


#pca endpoints
@router.get("/datasets/{dataset_tag}/pca",
            response_model=DatasetPCAResponse,
            tags=["Dimensional reduction","PCA"])

def get_dataset_pca(dataset_tag : str, filter_tag : str = None, scale : bool = True): #user : UserModel = Depends(get_user_from_token))
    """
    Returns the result of a Principal component analysis (PCA).
    """
    if not DB.datasets.exists(tag = dataset_tag): raise no_data_found_http_exception


    #if not DB.dataset_has_data(tag = dataset_tag): raise no_data_found_http_exception
    data_table = DB.get_datatable(tag = dataset_tag, filter_tag = filter_tag)
    projected_data, drivers, variance_explained = PCATransform(datatable=data_table,
                                        n_components=4,
                                        scale = scale).transform()
   
    sample_attributes, sample_map = DB.meta.get_sample_attributes_and_genotypes(dataset_tag)     
    #match the sample attributes to the PCA projection.
    projected_data = projected_data.join(sample_map)
    projected_data_to_browser = projected_data.reset_index(names="index").to_dict(orient="records")    
    
    # add feature information to drivers
    feature_keys = drivers.index 
    features = DB.features.get_protein_by_tags(tags = feature_keys.tolist(), as_data_frame=True)
    #features = feature_db.get(keys=feature_keys.tolist(), proteome_ids=proteome_ids, ignoreMissing=True)
   
    drivers_with_feature_info = pd.concat([drivers,features],axis=1)
    drivers_with_feature_info.reset_index(names="index", inplace=True)
    drivers_to_browser = drivers_with_feature_info.to_dict(orient="records")
    return DatasetPCAResponse(
        projection = projected_data_to_browser,
        drivers = drivers_to_browser,
        variance_explained = variance_explained, 
        samples_attributes = sample_attributes
        )

