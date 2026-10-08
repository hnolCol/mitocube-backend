from fastapi import APIRouter, Depends, HTTPException
from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC
from typing import List
from config.models.user import UserModel
from config.models.ptms import PTMSiteInsertModel, PTMSiteResponseModel
from services.users import is_user_at_least_curator, get_user_from_token
from services.submission import check_submission_access, check_submission_tags_access


router = APIRouter(dependencies=[Depends(get_user_from_token)],
    prefix="/api/features/ptms",
    tags=["Features", "PTMSites"])


@router.get("/q", summary="Finds PTM sites by search query.")
def find_ptm_sites_by_query(search_string : str, limit : int = 50, submission_tags : str = None, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[str]:
    """
    Finds PTM sites by their tag. The tag is derived from the protein tag (or the
    protein group tag for group level identifications), the position and the modification,
    e.g. P12345_S473_PHOSPHO.

    Parameters
    ----------
    search_string : str
        The search string to match against the PTM site tags.
    limit : int, optional
        The limit of PTM sites to return, by default 50
    submission_tags : str, optional
        Semicolon separated submission tags to filter the search (e.g. PTM sites quantified in specific submissions), by default None
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(get_user_from_token)

    Returns
    -------
    List[str]
        PTM site tags.
    """
    check_submission_tags_access(submission_tags = submission_tags, user = user, db = db)
    submission_tags = submission_tags.split(";") if submission_tags else None
    return db.ptm_sites.find(search_string = search_string, submission_tag = submission_tags[0] if submission_tags else None, limit = limit)


@router.get("/count", summary="Counts the PTM sites.")
def count_ptm_sites(submission_tag : str = None, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> int:
    """
    Counts the PTM sites, optionally within a submission.

    Parameters
    ----------
    submission_tag : str, optional
        The tag of the submission to count PTM sites for, by default None
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(get_user_from_token)

    Returns
    -------
    int
        The number of PTM sites.
    """
    if submission_tag is not None:
        check_submission_access(submission_tag = submission_tag, user = user, db = db)
    return db.ptm_sites.count(submission_tag = submission_tag)


@router.post("/insert", summary="Inserts a PTM site into the database. Requires at least curator rights.")
def insert_ptm_site(ptm_site : PTMSiteInsertModel, user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> bool:
    """
    Inserts a PTM site into the database. The tag is derived and validated from the
    protein tag (or protein group tag), the position and the modification. The site is
    linked to the protein group via [:OF_PROTEIN_GROUP] and to the supporting modified
    precursors via [:SUPPORTED_BY].

    Parameters
    ----------
    ptm_site : PTMSiteInsertModel
        The PTM site to insert.
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(is_user_at_least_curator)

    Returns
    -------
    bool
        True if the insertion was successful.

    Raises
    ------
    HTTPException
        If the protein group or one of the supporting precursors does not exist.
    """
    if not db.protein_groups.exists(tag = ptm_site.protein_group_tag):
        raise HTTPException(status_code=404, detail=f"Protein group with tag {ptm_site.protein_group_tag} not found.")
    for precursor_tag in ptm_site.precursor_tags:
        if not db.precursors.exists(tag = precursor_tag):
            raise HTTPException(status_code=404, detail=f"Precursor with tag {precursor_tag} not found.")
    return db.ptm_sites.insert(ptm_site = ptm_site)


@router.post("/insert/bulk", summary="Bulk inserts PTM sites into the database. Requires at least curator rights.")
def bulk_insert_ptm_sites(ptm_sites : List[PTMSiteInsertModel], batch_size : int = 1000, transaction_batch_size : int = 400, user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> dict:
    """
    Bulk inserts PTM sites into the database. Existing tags are merged. This is a library
    level entity insert like the precursor bulk insert; the per submission/sample
    quantification is inserted separately. Sites whose protein group does not exist are
    skipped and reported. Supporting precursors that do not exist are skipped and reported.

    Parameters
    ----------
    ptm_sites : List[PTMSiteInsertModel]
        The PTM sites to insert.
    batch_size : int, optional
        The number of sites sent to the database per query, by default 1000
    transaction_batch_size : int, optional
        The number of rows per internal transaction, by default 400
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(is_user_at_least_curator)

    Returns
    -------
    dict
        A report with the number of inserted sites (valid), the number of skipped
        sites whose protein group does not exist (not_found) including their tags and
        the precursor links that could not be created because the precursor does
        not exist (precursor_links_not_created), so that callers can combine the results.

    Raises
    ------
    HTTPException
        If the request body is empty or the batch sizes are invalid.
    """
    if len(ptm_sites) == 0:
        raise HTTPException(status_code=400, detail="No PTM sites provided.")
    if batch_size < 1:
        raise HTTPException(status_code=400, detail="batch_size must be at least 1.")
    if transaction_batch_size < 1:
        raise HTTPException(status_code=400, detail="transaction_batch_size must be at least 1.")
    return db.ptm_sites.bulk_insert(ptm_sites = ptm_sites, batch_size = batch_size, transaction_batch_size = transaction_batch_size)


@router.get("/{ptm_site_tag}", summary="Retrieves a PTM site by its tag.")
def get_ptm_site_by_tag(ptm_site_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> PTMSiteResponseModel:
    """
    Retrieves a PTM site by its tag.

    Parameters
    ----------
    ptm_site_tag : str
        The tag of the PTM site (e.g. P12345_S473_PHOSPHO).
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(get_user_from_token)

    Returns
    -------
    PTMSiteResponseModel
        The PTM site data.

    Raises
    ------
    HTTPException
        If the PTM site with the given tag does not exist.
    """
    if not db.ptm_sites.exists(tag = ptm_site_tag): raise HTTPException(status_code=404, detail="PTM site not found.")
    return db.ptm_sites.get(tag = ptm_site_tag)


@router.get("/{ptm_site_tag}/abundance", summary="Retrieves the abundance of a PTM site by its tag.")
def get_ptm_site_abundance_by_tag(ptm_site_tag : str, submission_tags : str = None, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)):
    """
    Retrieves the abundance of a PTM site by its tag.

    Parameters
    ----------
    ptm_site_tag : str
        The tag of the PTM site to retrieve.
    submission_tags : str, optional
        Semicolon separated submission tags to filter the abundance data, by default None (all submissions)
    user : UserModel, optional
        The user making the request, by default Depends(get_user_from_token)

    Returns
    -------
    pd.DataFrame
        The abundance data of the PTM site.

    Raises
    ------
    HTTPException
        If the PTM site with the given tag does not exist.
    """
    if not db.ptm_sites.exists(tag = ptm_site_tag): raise HTTPException(status_code=404, detail="PTM site not found.")
    check_submission_tags_access(submission_tags = submission_tags, user = user, db = db)
    return db.ptm_sites.get_abundance(tag = ptm_site_tag, submission_tags = submission_tags.split(";") if submission_tags else None)


@router.get("/{ptm_site_tag}/is_quantified", summary="Checks if a PTM site is quantified.")
def get_ptm_site_is_quantified(ptm_site_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> bool:
    """
    Checks if a PTM site is quantified.

    Parameters
    ----------
    ptm_site_tag : str
        The tag of the PTM site to check.
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(get_user_from_token)

    Returns
    -------
    bool
        True if the PTM site is quantified, False otherwise.

    Raises
    ------
    HTTPException
        If the PTM site with the given tag does not exist.
    """
    if not db.ptm_sites.exists(tag = ptm_site_tag): raise HTTPException(status_code=404, detail="PTM site not found.")
    return db.ptm_sites.is_quantified(tag = ptm_site_tag)
