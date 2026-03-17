
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from lib.database.Database import Database
from config.models.user import UserModel
from config.enums.states import SubmissionStatesEnums
from services.users import get_user_from_token
from config.exceptions.HTTPExceptions import submission_tag_not_found

from lib.data.transform.PCA import PCATransform
from config.models.dataset.pca import DatasetPCAResponse

DB = Database.DB()

router = APIRouter(
    prefix="/api/submissions/analysis",
    tags=["Submission","Analysis"],
    )



#pca endpoints
@router.get("/{submission_tag}/pca",
            tags=["Dimensional reduction","PCA"])

def get_dataset_pca(submission_tag : str, annotation_tag : str = None, scale : bool = True, user : UserModel = Depends(get_user_from_token)):
    """
    Returns the result of a Principal component analysis (PCA).
    """
    if not DB.submissions.exists(tag = submission_tag): raise submission_tag_not_found
    if not DB.submissions.quantification_exists(tag = submission_tag, type = "proteins"): raise HTTPException(status_code=404, detail="No quantification data found for this submission.")


    data_table = DB.datasets.get_datatable(tag = submission_tag, annotation_tag = annotation_tag) #the data columns are the sample indices 
    projected_data, drivers, variance_explained = PCATransform(datatable=data_table,
                                        n_components=4,
                                        scale = scale).transform()

    condition_procedures = DB.samples.get_condition_applications_by_sample_for_submission(submission_tag=submission_tag)
    print(condition_procedures)
    
    projected_data = projected_data.join(condition_procedures, how="left")
    print(projected_data)
    return DatasetPCAResponse(projection=projected_data.to_dict(orient="records"), 
                              drivers=drivers.reset_index(names="tag").to_dict(orient="records"), 
                              variance_explained=variance_explained.tolist())
    
    
    
    # #if not DB.dataset_has_data(tag = dataset_tag): raise no_data_found_http_exception
    # data_table = DB.get_datatable(tag = submission_tag, filter_tag = filter_tag)
    # projected_data, drivers, variance_explained = PCATransform(datatable=data_table,
    #                                     n_components=4,
    #                                     scale = scale).transform()
   
    # sample_attributes, sample_map = DB.meta.get_sample_attributes_and_genotypes(dataset_tag)     
    # #match the sample attributes to the PCA projection.
    # projected_data = projected_data.join(sample_map)
    # projected_data_to_browser = projected_data.reset_index(names="index").to_dict(orient="records")    
    
    # # add feature information to drivers
    # feature_keys = drivers.index 
    # features = DB.features.get_protein_by_tags(tags = feature_keys.tolist(), as_data_frame=True)
    # #features = feature_db.get(keys=feature_keys.tolist(), proteome_ids=proteome_ids, ignoreMissing=True)
   
    # drivers_with_feature_info = pd.concat([drivers,features],axis=1)
    # drivers_with_feature_info.reset_index(names="index", inplace=True)
    # drivers_to_browser = drivers_with_feature_info.to_dict(orient="records")
    # return DatasetPCAResponse(
    #     projection = projected_data_to_browser,
    #     drivers = drivers_to_browser,
    #     variance_explained = variance_explained, 
    #     samples_attributes = sample_attributes
    #     )

