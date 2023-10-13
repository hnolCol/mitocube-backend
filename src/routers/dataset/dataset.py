from fastapi import APIRouter, Depends 

from config.enums.users.roles import UserRolesEnum
from config.models.user import User
from config.models.dataset.data import API_DatasetData

from config.models.dataset.data import DatasetPCAResponse

from lib.data.database.ABCDatabase import MCDatabase 
from lib.data.transform.PCA import PCATransform
from lib.data.filter.NoMissingValues import NoNaNFilter
from services.users import get_user_from_token, is_user_at_least_curator



#print(DB)



router = APIRouter(
    prefix="/api",
    tags=["Dataset"]
    )


@router.get("/dataset/{data_id}/data", response_model=API_DatasetData)
def get_dataset_data(data_id : str):
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
    API_DatasetData("1231",[],{})
    return {}

#parameter endpoints 
@router.get("/dataset/{dataset_label}/meta",
            tags=["Parameters"])
def get_dataset_params(dataset_label : str, user : User = Depends(get_user_from_token)):
    """
    Returns the metadata associated to the dataset
    """
    db = MCDatabase.getDatabase()
    dataset = db.getDataset(dataset_label)
    return dataset.getMetaJson()

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