from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException

from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC
from config.models.user import UserModel
from config.models.instruments import SampleMeasuringInsertModel, SampleMeasuringResponseModel
from services.pats import get_curator_or_submissions_read_pat, get_curator_or_sample_measuring_pat

router = APIRouter(
    prefix="/api/automation",
    tags=["Automation (PAT)"],
)


@router.get("/submissions/tags",
    summary="Returns the tags of submissions created at or after a timestamp. Requires at least curator rights or a personal access token with the submissions.read scope.")
def get_submission_tags_since(since : float = None, user : UserModel = Depends(get_curator_or_submissions_read_pat), db : DatabaseABC = Depends(get_db)) -> List[Dict]:
    """
    Returns the tags and created_at timestamps of all submissions that were
    created at or after the given timestamp. Intended for automation scripts,
    e.g. to create the folders of new submissions on a network attached storage
    since the last check.

    Parameters
    ----------
    since : float, optional
        The timestamp of the last check in epoch milliseconds. If None, all
        submissions are returned, by default None
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(get_curator_or_submissions_read_pat)

    Returns
    -------
    List[Dict]
        Dicts with keys 'tag' and 'created_at' ordered by creation time ascending.
    """
    return db.submissions.get_tags_since(since = since)


@router.post("/samples/measuring",
    summary="Marks a sample as currently being measured (live data). Requires at least curator rights or a personal access token with the sample.measuring scope.",
    response_model=SampleMeasuringResponseModel)
def set_sample_measuring(props : SampleMeasuringInsertModel, user : UserModel = Depends(get_curator_or_sample_measuring_pat), db : DatabaseABC = Depends(get_db)) -> SampleMeasuringResponseModel:
    """
    Creates or refreshes a LiveMeasurement node for the given sample, indicating
    that the sample is currently being measured on the given instruments. The
    node carries a timestamp and is connected to the sample and the instrument
    trait nodes. Calling it again refreshes the timestamp and the instruments.

    Parameters
    ----------
    props : SampleMeasuringInsertModel
        The sample tag and, optionally, the tags of the instruments the sample
        is being measured on.
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(get_curator_or_sample_measuring_pat)

    Returns
    -------
    SampleMeasuringResponseModel
        The live measurement of the sample.

    Raises
    ------
    HTTPException
        If the sample (404) or one of the instruments (404) does not exist.
    """
    if not db.samples.exists(tag = props.sample_tag):
        raise HTTPException(status_code=404, detail=f"No sample found for tag {props.sample_tag}")
    try:
        return db.instruments.set_sample_measuring(sample_tag = props.sample_tag, instrument_tags = props.instrument_tags, user_tag = user.tag)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/samples/measuring/{sample_tag}",
    summary="Returns the live measurement of a sample. Requires at least curator rights or a personal access token with the sample.measuring scope.",
    response_model=SampleMeasuringResponseModel)
def get_sample_measuring(sample_tag : str, user : UserModel = Depends(get_curator_or_sample_measuring_pat), db : DatabaseABC = Depends(get_db)) -> SampleMeasuringResponseModel:
    """
    Returns the LiveMeasurement node of the sample with its instruments, or 404
    if the sample exists but is not marked as being measured.

    Parameters
    ----------
    sample_tag : str
        The tag of the sample.
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(get_curator_or_sample_measuring_pat)

    Returns
    -------
    SampleMeasuringResponseModel
        The live measurement of the sample.

    Raises
    ------
    HTTPException
        If the sample (404) does not exist or is not being measured (404).
    """
    if not db.samples.exists(tag = sample_tag):
        raise HTTPException(status_code=404, detail=f"No sample found for tag {sample_tag}")
    measurement = db.instruments.get_sample_measuring(sample_tag = sample_tag)
    if measurement is None:
        raise HTTPException(status_code=404, detail=f"The sample {sample_tag} is not marked as being measured.")
    return measurement
