
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

@router.get("/{submission_tag}/pca",
            tags=["Dimensional reduction","PCA"])
def get_dataset_pca(submission_tag : str, annotation_tag : str = None, scale : bool = True, user : UserModel = Depends(get_user_from_token)):
    """
    Returns the result of a Principal component analysis (PCA).
    """
    if not DB.submissions.exists(tag = submission_tag): raise submission_tag_not_found
    if not DB.submissions.quantification_exists(tag = submission_tag, type = "proteins"): raise HTTPException(status_code=404, detail="No quantification data found for this submission.")


    data_table = DB.datasets.get_datatable(tag = submission_tag, annotation_tag = annotation_tag, use_sample_tags=True) #the data columns are the sample indices 
    projected_data, drivers, variance_explained = PCATransform(datatable=data_table,
                                        n_components=4,
                                        scale = scale).transform()
    projected_data.index = data_table.columns.values
    condition_applications = DB.samples.get_condition_applications_by_sample_for_submission(submission_tag=submission_tag, sort_ca_tags=True, return_sample_index=False)  #preload condition applications
    if DB.submissions.has_genotypes(tag = submission_tag):
        genotypes = DB.samples.get_genotypes_by_sample_for_submission(submission_tag=submission_tag, sort_ca_tags=True, return_sample_index=False)  #preload genotypes
        condition_applications = condition_applications.join(genotypes, how="outer")
        


    projected_data = projected_data.join(condition_applications, how="left")

    
    return DatasetPCAResponse(projection=projected_data.to_dict(orient="records"), 
                              drivers=drivers.reset_index(names="tag").to_dict(orient="records"), 
                              variance_explained=variance_explained.tolist())
    
    