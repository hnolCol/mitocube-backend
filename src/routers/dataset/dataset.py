from fastapi import APIRouter, Depends, HTTPException
import pandas as pd 

from config.enums.users.roles import UserRolesEnum
from config.models.user import UserModel

from config.models.dataset.data import DatasetPCAResponse
from config.models.submissions.submissions import DatasetSubmissionModel, DatasetSubmissionResponseModel
from config.models.submissions.runs import RunListModel, RunListRequestPropsModel
from config.models.annotations.feature import FeatureModel

from lib.data.database.ABCDatabase import MCDatabase, MCAttributes
from lib.data.database.Database import Database
from lib.data.annotations.ABCAnnotations import PandaFeatureDatabase
from lib.data.transform.PCA import PCATransform
from lib.data.transform.FeatureData import FeatureData
from lib.data.filter.NoMissingValues import NoNaNFilter

from config.exceptions.HTTPExceptions import no_data_found

from services.users import get_user_from_token, is_user_at_least_curator
from services.submission import map_tags_to_attribute_in_metadata, get_dataset_from_database

DB = Database.DB()


router = APIRouter(
    prefix="/api",
    tags=["Dataset"]
    )

@router.get("/datasets/{dataset_label}/data", response_model=[])
def get_dataset_data(dataset_label : str):
    """
    Returns the data for a specific dataset
    
    NaN values are replace with null (e.g. undefined in JS)
    The format that is used to export the data is records (List[Dict]):
    ```
    data : [{colName1 : value1, colName2: value2, ...}, {colName1 : value1, colName2: value2, ..}]
    ```

    Validation Error 

    data_id not found in database. 
    """
    db = MCDatabase.getDatabase()
    dataset = db.getDataset(dataset_label)
    data_table = dataset.getDataTable()
    return data_table.to_numpy().tolist()

# class QCResponse(BaseModel):


@router.get("/datasets/{dataset_label}/qc", 
            response_model=[], 
            summary="Quality control of data set. Includes a statistic summary.")
def get_dataset_data(dataset_label : str):
    """
    Returns the summary statistcs data for a specific dataset
    TO DO : Add response model.
    """
    poi_data = []
    db = MCDatabase.getDatabase()

    dataset = db.getDataset(dataset_label)
    metadata : DatasetSubmissionModel = dataset.getMetaJson()
    #TODO Check if proteome/organism is there, otherwise cause error 
    if "att_organism" not in metadata.dataset_attributes:
        raise HTTPException(status_code=400,detail="No organism defined for this dataset.")
    proteome_ids =  [attrValueTag.split(":")[1] for attrValueTag in metadata.dataset_attributes["att_organism"]] 
    datatable = dataset.getDataTable()
    if datatable is None or datatable.empty:
        raise no_data_found
    data_summary = datatable.describe()
    data_summary.loc["total",:] = datatable.index.size

    if "att_poi" in metadata.dataset_attributes: 
        pois = metadata.dataset_attributes["att_poi"]
        ids = [poi.split(":")[-1].upper() for poi in pois]
        feature_db = PandaFeatureDatabase()
        features = feature_db.get(keys=ids,proteome_ids=proteome_ids).reset_index(names="key")
        feature_annotations = features.to_dict(orient="records")
        poi_data = [FeatureData(dataset).transform(id, add_annotations=True) for id in ids if id in datatable.index]

    return {"stats" : data_summary.to_dict(), 
            "poi_data" : [{
            "feature_key" : ids[n],
            "feature_annotations" : FeatureModel(**feature_annotations[n], tag=f"att_poi:{feature_annotations[n]['key']}"),
            "annotations" : {},
            "data" : data.to_dict(orient="records"),
            "samples_attributes" : samples_attributes} for n,(data, samples_attributes, annotations) in enumerate(poi_data)]
            }



#parameter endpoints 
@router.get("/datasets/{dataset_label}/meta",
            response_model=DatasetSubmissionResponseModel,
            tags=["Parameters","Meta data"])
def get_dataset_params(dataset_label : str, user : UserModel = Depends(get_user_from_token)):
    """
    Returns the metadata associated to the dataset
    """
    db = MCDatabase.getDatabase()
    dataset = get_dataset_from_database(db,dataset_label)
    metadata : DatasetSubmissionModel = dataset.getMetaJson()
    
    return map_tags_to_attribute_in_metadata(metadata)


#pca endpoints
@router.get("/datasets/{dataset_label}/pca",
            response_model=DatasetPCAResponse,
            tags=["Dimensional reduction","PCA"])

def get_dataset_pca(dataset_label : str, scale : bool = True, user : UserModel = Depends(get_user_from_token)):
    """
    Returns the result of a Principal component anaylsis (PCA).
    """
    db = MCDatabase.getDatabase()
    dataset = db.getDataset(dataset_label)
    if not dataset.hasData(): raise HTTPException(status_code=404,detail=f"No datatable found for the dataset {dataset_label}.")
    idcs = NoNaNFilter(dataset).get_indices()
    
    projected_data, drivers, variance_explained, samples_attributes = PCATransform(dataset=dataset,
                                        n_components=4,
                                        scale = scale,
                                        subset_index=idcs).transform()
    
    
    projected_data_to_browser = projected_data.reset_index(names="index").to_dict(orient="records")
    
    
    # add feature information to drivers
    feature_keys = drivers.index 
    features = DB.feature.get_protein_by_tags(tags = feature_keys.tolist(), as_data_frame=True)
    #features = feature_db.get(keys=feature_keys.tolist(), proteome_ids=proteome_ids, ignoreMissing=True)
   
    drivers_with_feature_info = pd.concat([drivers,features],axis=1)
    drivers_with_feature_info.reset_index(names="index", inplace=True)
    drivers_to_browser = drivers_with_feature_info.to_dict(orient="records")
    return DatasetPCAResponse(
        projection=projected_data_to_browser,
        drivers=drivers_to_browser,
        variance_explained=variance_explained, 
        samples_attributes=samples_attributes
        )

