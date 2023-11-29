from fastapi import APIRouter, Depends 

from config.enums.users.roles import UserRolesEnum
from config.models.user import User
from config.models.dataset.data import API_DatasetData

from config.models.dataset.data import DatasetPCAResponse
from config.models.submissions.submissions import DatasetSubmissionModel
from lib.data.database.ABCDatabase import MCDatabase 
from lib.data.transform.PCA import PCATransform
from lib.data.transform.FeatureData import FeatureData
from lib.data.filter.NoMissingValues import NoNaNFilter
from config.exceptions.HTTPExceptions import no_data_found

from services.users import get_user_from_token, is_user_at_least_curator

import pandas as pd 

#print(DB)



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
    """
    db = MCDatabase.getDatabase()
    dataset = db.getDataset(dataset_label)
    metadata : DatasetSubmissionModel = db.getJSONDatasets(labels=[dataset_label])[dataset_label]
    datatable = dataset.getDataTable()
    if datatable is None or datatable.empty:
        raise no_data_found
    data_summary = datatable.describe()
    data_summary.loc["total",:] = datatable.index.size

    
    if "att_poi" in metadata.dataset_attributes: 
        pois = metadata.dataset_attributes["att_poi"]
        ids = [poi.split(":")[-1].upper() for poi in pois]
        poi_data = [FeatureData(dataset).transform(id, add_annotations=True) for id in ids if id in datatable.index]

    return {"stats" : data_summary.to_dict(), 
            "poi_data" : [{
                "annotations" : annotations.to_dict(),
                "data" : data.to_dict(orient="records"),
                "samples_attributes" : samples_attributes} for data, samples_attributes, annotations in poi_data]
            }



#parameter endpoints 
@router.get("/datasets/{dataset_label}/meta",
            response_model=DatasetSubmissionModel,
            tags=["Parameters","Meta data"])
def get_dataset_params(dataset_label : str, user : User = Depends(get_user_from_token)):
    """
    Returns the metadata associated to the dataset
    """
    db = MCDatabase.getDatabase()
    metadata : DatasetSubmissionModel = db.getJSONDatasets(labels=[dataset_label])[dataset_label]
    return metadata

#volcano plot
@router.get("/dataset/{data_id}/volcano")
def get_dataset_volcano(data_id : str, test_details : dict):
    """
    Returns the result of a Principal component anaylsis (PCA)

    """
    return {}



#heatmap endpoints 
@router.get("/dataset/{data_id}/heatmap",
            tags=["Heatmap"])
def get_dataset_heatmap(data_id : str, test_details : dict):
    """
    Returns data to feed into a heatmap for visualization.
    
    Requires the definition of a statistical test to show a subset of the data. 

    """
    return {}

#pca endpoints

@router.get("/dataset/{dataset_label}/pca",
            response_model=DatasetPCAResponse,
            tags=["Dimensional reduction","PCA"])
def get_dataset_pca(dataset_label : str, user : User = Depends(get_user_from_token)):
    """
    Returns the result of a Principal component anaylsis (PCA)
    """
    db = MCDatabase.getDatabase()
    dataset = db.getDataset(dataset_label)
    idcs = NoNaNFilter(dataset).get_indices()
    
    projected_data, drivers, variance_explained = PCATransform(dataset=dataset,
                                        n_components=4, #get from settings!
                                        subset_index=idcs).transform()
    
    return DatasetPCAResponse(projection=projected_data,drivers=drivers,variance_explained=variance_explained)