from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from typing import List, Literal

# from lib.data.database_helper.ABCDatabaseHelper import MCDatabaseHelper
from lib.database.Database import Database
import pandas as pd 
from config.models.user import UserModel
# from config.models.attributes import AttributeValueModel
# from config.enums.states import SubmissionStatesEnums
from config.models.news.news import  NewsModel, NewsInsertModel
from config.models.parameter import APIParamString
from services.users import is_user_admin, get_user_from_token, is_user_at_least_curator
from config.enums.states import SubmissionStatesEnums 
from config.models.plots.stats import DistResponseModel
DB = Database.DB()


router = APIRouter(
    prefix="/api/stats/submissions",
    tags=["Submissions","Statistics"]
    )




@router.get("/{submission_tag}/views")
def get_submission_views(submission_tag : str, user: UserModel = Depends(get_user_from_token)) -> int:
    """
    Returns the view statistics for submissions.
    """
    return DB.submissions.get_views(tag=submission_tag)



@router.get("/durations")
def get_submission_durations(
    state_01: SubmissionStatesEnums = SubmissionStatesEnums.SUBMITTED,
    state_02: SubmissionStatesEnums = SubmissionStatesEnums.DONE,
    aggregate: Literal["mean", "sum", "std", "median", "min", "max", "dist"] = "mean",
    user: UserModel = Depends(get_user_from_token)
) -> float | DistResponseModel:
    """
    Returns the duration statistics for submissions. The durations are calculated as the difference between the timestamps of two states.
    The unit is in milliseconds.
    If aggregate is 'dist', returns a DistResponseModel with min, q1, median, q3, max.
    """
    durations = DB.submissions.get_durations_between_states(state_01=state_01, state_02=state_02)
    df = pd.DataFrame(columns=["submission_tag", "duration"]).from_dict(durations)

    if aggregate == "dist":
        desc = df["duration"].describe(percentiles=[0.25, 0.5, 0.75])
        print(desc)
        return DistResponseModel(
            min=desc["min"],
            q1=desc["25%"],
            median=desc["50%"],
            q3=desc["75%"],
            max=desc["max"],
            mean=desc["mean"],
            std=desc["std"],
            count=desc["count"]
        )
    else:
        agg_metric = df["duration"].agg(func=aggregate, skipna=True)
        return agg_metric