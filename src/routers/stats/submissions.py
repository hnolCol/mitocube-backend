from fastapi import APIRouter, Depends
from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC
from typing import List, Literal

# 
import pandas as pd 
from config.models.user import UserModel
# from config.models.attributes import AttributeValueModel
# from config.enums.states import SubmissionStatesEnums
from services.users import get_user_from_token
from services.submission import check_submission_access
from config.enums.states import SubmissionStatesEnums 
from config.models.plots.stats import DistResponseModel, GroupedCountResponseModel
import pandas as pd


def parse_semicolon_list(value : str = None) -> List[str] | None:
    if value is None or len(value) == 0:
        return None
    return [v.strip() for v in value.split(";") if len(v.strip()) > 0]

def parse_semicolon_ints(value : str = None) -> List[int] | None:
    parsed = parse_semicolon_list(value)
    if parsed is None:
        return None
    return [int(v) for v in parsed]

router = APIRouter(dependencies=[Depends(get_user_from_token)],
    prefix="/api/stats/submissions",
    tags=["Submissions","Statistics"]
    )




@router.get("/{submission_tag}/views")
def get_submission_views(submission_tag : str, user: UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> int:
    """
    Returns the view statistics for submissions.
    """
    check_submission_access(submission_tag = submission_tag, user = user, db = db)
    return db.submissions.get_views(tag=submission_tag)



@router.get("/durations")
def get_submission_durations(
    state_01: SubmissionStatesEnums = SubmissionStatesEnums.SUBMITTED,
    state_02: SubmissionStatesEnums = SubmissionStatesEnums.DONE,
    aggregate: Literal["mean", "sum", "std", "median", "min", "max", "dist"] = "mean",
    user: UserModel = Depends(get_user_from_token)
, db : DatabaseABC = Depends(get_db)) -> float | DistResponseModel:
    """
    Returns the duration statistics for submissions. The durations are calculated as the difference between the timestamps of two states.
    The unit is in milliseconds.
    If aggregate is 'dist', returns a DistResponseModel with min, q1, median, q3, max. 
    The results are transformed to days. 
    """
    durations = db.submissions.get_durations_between_states(state_01=state_01, state_02=state_02)
    df = pd.DataFrame(columns=["submission_tag", "duration"]).from_dict(durations)
    df.loc[:,"duration"] = df["duration"] / (1000 * 60 * 60 * 24) #transform to days
    if aggregate == "dist":
        desc = df["duration"].describe(percentiles=[0.25, 0.5, 0.75])
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
    
    



@router.get("/counts/submissions")
def get_submission_counts(
    group_by: Literal["research_group", "trait"] = "research_group",
    years: str = None,
    state: str = None,
    attribute_tag: str = None,
    group_by_entity: Literal["trait", "condition_application"] = "trait",
    user: UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)
) -> List[GroupedCountResponseModel]:
    """
    Returns the number of submissions per research group or trait and year.
    For group_by = "trait", submissions are grouped by the trait tags of their condition applications
    ((Submission)-[:HAS_APPLICATION]->(ConditionApplication)-[:INSTANCE_OF]->(Trait)) or, with
    group_by_entity = "condition_application", by the condition application tags. attribute_tag restricts
    the counted condition applications to the given attribute (e.g. att_proteome).
    Each submission is counted at most once per trait and year, even if it has several condition applications
    for the same trait; a submission with multiple distinct traits contributes one count to each of its traits.
    Rows are flat: [{ group, year, value }]. Missing (group, year) combinations are absent.
    """
    df = db.submission_filter.get_counts_by_year(
        by=group_by,
        entity="submission",
        years=parse_semicolon_ints(years),
        states=parse_semicolon_list(state),
        attribute_tag=attribute_tag,
        group_entity=group_by_entity,
    )
    return [GroupedCountResponseModel(**row) for row in df.to_dict(orient="records")]

@router.get("/counts/samples")
def get_sample_counts_by_research_group(
    group_by: Literal["research_group"] = "research_group",
    years: str = None,
    state: str = None,
    user: UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)
) -> List[GroupedCountResponseModel]:
    """
    Returns the number of samples per research group and year.
    Rows are flat: [{ group, year, value }]. Missing (group, year) combinations are absent.
    """
    df = db.submission_filter.get_counts_by_year(
        by=group_by,
        entity="sample",
        years=parse_semicolon_ints(years),
        states=parse_semicolon_list(state),
    )
    return [GroupedCountResponseModel(**row) for row in df.to_dict(orient="records")]

@router.get("/counts/users")
def get_submission_counts_by_user(
    years: str = None,
    state: str = None,
    research_group_tags: str = None,
    user: UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)
) -> List[GroupedCountResponseModel]:
    """
    Returns the number of submissions per user and year, optionally restricted to research groups.
    Rows are flat: [{ group, year, value }]. Missing (group, year) combinations are absent.
    """
    df = db.submission_filter.get_counts_by_year(
        by="user",
        entity="submission",
        years=parse_semicolon_ints(years),
        states=parse_semicolon_list(state),
        research_group_tags=parse_semicolon_list(research_group_tags),
    )
    return [GroupedCountResponseModel(**row) for row in df.to_dict(orient="records")]
