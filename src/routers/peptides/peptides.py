from fastapi import APIRouter, Depends, HTTPException

from config.models.user import UserModel
from services.users import get_user_from_token
from lib.database.Database import Database
from config.models.parameter import APIParamString

DB = Database.DB()

router = APIRouter(
    prefix="/api/peptides",
    tags=["Peptides"]
    )


@router.get("/{peptide_tag}")
def get_peptide_by_tag(peptide_tag : str):
    """Retrieves a peptide by its tag.

    Parameters
    ----------
    peptide_tag : str
        The tag of the peptide to retrieve.

    Returns
    -------
    FeatureNeoModel
        The peptide data.
    
    Raises
    ------
    HTTPException
        If the peptide with the given tag does not exist.
    """
    if not DB.peptides.exists(tag = peptide_tag): raise HTTPException(status_code=404, detail="Peptide not found.")
    return DB.peptides.get(tag = peptide_tag)


@router.get("/{peptide_tag}/abundance")
def get_peptide_abundance_by_tag(peptide_tag : str, submission_tags : str  = None, user : UserModel = Depends(get_user_from_token)):
    """Retrieves the abundance of a peptide by its tag.

    Parameters
    ----------
    peptide_tag : str
        The tag of the peptide to retrieve.
    user : UserModel, optional
        The user making the request, by default Depends(get_user_from_token)

    Returns
    -------
    pd.DataFrame
        The abundance data of the peptide.

    Raises
    ------
    HTTPException
        If the peptide with the given tag does not exist.
    """

    if not DB.peptides.exists(tag = peptide_tag): raise HTTPException(status_code=404, detail="Peptide not found.")
    return DB.peptides.get_abundance(tag = peptide_tag, submission_tags = APIParamString(submission_tags).param) 





@router.get("/{peptide_tag}/correlations")
def get_peptide_by_tag(peptide_tag : str, 
                       min_size : int = 4, 
                       filter_tag : str = None,
                       exclude_within_protein_correlation : bool = True, 
                       limit : int = None,
                       user : UserModel = Depends(get_user_from_token)):
    """Retrieves correlations for a peptide by its tag correlating to other peptides.
    Filter the proteins by the filter tag if required.

    Parameters
    ----------
    peptide_tag : str
        The tag of the peptide to retrieve.        
    min_size : int, optional
        The minimum size of the peptides to retrieve, by default 4.
    filter_tag : str, optional
        A tag to filter the peptides by, by default None.
    exclude_within_protein_correlation : bool, optional
        Whether to exclude correlations within the same protein, by default True.
    limit : int, optional
        The maximum number of results to return, by default None.
    user : UserModel, optional
        The user making the request, by default Depends(get_user_from_token)

    Returns
    -------
    _type_
        _description_

    Raises
    ------
    HTTPException
        If the peptide with the given tag does not exist.
    """

    if not DB.peptides.exists(tag = peptide_tag): raise HTTPException(status_code=404, detail=f"Peptide with tag {peptide_tag}not found.")
    df = DB.peptides.correlate_to(tag=peptide_tag, limit = limit, min_size = min_size, exclude_within_protein_correlation = exclude_within_protein_correlation, filter_tag = filter_tag)
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"No correlations found for peptide {peptide_tag} with the given parameters." )
    return df.to_dict(orient="records") if df is not None else []
