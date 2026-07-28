import colorsys

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from lib.database.Database import Database
from config.models.user import UserModel
from config.models.submissions.quantifications import ProteinGroupQuantificationModel, PrecursorQuantificationModel, ProteinQuantificationBulkInsertModel
from config.exceptions.HTTPExceptions import submission_tag_not_found
from services.users import get_user_from_token, is_user_at_least_curator
from typing import Dict, List, Literal, Tuple
from collections import OrderedDict
import numpy as np
from config.models.calculations.quantile import QuantileModel

DB = Database.DB()

router = APIRouter(
    prefix="/api/submissions",
    tags=["Submission"],
    )

from pydantic import BaseModel

class ProteinGroupQuantificationListModel(BaseModel):
    quantifications: List[ProteinGroupQuantificationModel]
    
    
class ProteinGroupQuantificationCountModel(BaseModel):
    submission_tag: str
    count: int
    user_tag : str
    created_at : float
    
@router.get("/quantifications/protein_groups/count", summary="Get the number of protein group quantifications for a given submission.")
def get_protein_group_quantification_count(user : UserModel = Depends(get_user_from_token)) -> List[ProteinGroupQuantificationCountModel]:
    """
    Get the number of protein group quantifications for a given submission.

    Parameters
    ----------
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(get_user_from_token)
    Returns
    -------
    List[ProteinGroupQuantificationCountModel]
        A list of ProteinGroupQuantificationCountModel objects, each containing the submission tag, the number of protein group quantifications, and the user tag of the creator of the submission.
    """

    return [ProteinGroupQuantificationCountModel(**record) for record in DB.submissions.get_protein_group_quantification_count().to_dict(orient="records")]
    
    
@router.get("/{submission_tag}/quantifications/exists", summary="Checks if quantification data for this submission exists.")
def get_submission_quant_exists(submission_tag : str, quantification_type :  Literal["proteins","protein_groups","precursors","any"], user : UserModel = Depends(get_user_from_token)) -> bool:
    """
    Checks if quantification data for this submission exists.

    Parameters
    ----------
    submission_tag : str
        The tag of the submission.  
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(get_user_from_token)
    Returns
    -------
    bool
        True if quantification data exists, False otherwise.
    """

    if DB.submissions.exists(tag=submission_tag) is False:
        raise submission_tag_not_found

    return DB.submissions.quantification_exists(tag=submission_tag, type=quantification_type)




@router.post("/{submission_tag}/quantifications/proteins", summary="Insert protein quantifications for a given submission. Requires curator rights.")
def insert_protein_quantifications(
    submission_tag: str,
    quantifications: ProteinQuantificationBulkInsertModel,
    apply_statistics : bool = False,
    user: UserModel = Depends(is_user_at_least_curator)
) -> int:
    """
    Insert protein quantifications for a given submission. Requires curator rights.

    Parameters
    ----------
    submission_tag : str
        The tag of the submission.  
    quantification_list : ProteinQuantificationListModel
        Object containing a list of protein quantifications to insert.
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(get_user_from_token)
    Returns
    -------
    int
        Number of inserted protein quantifications.
    """

    if DB.submissions.exists(tag=submission_tag) is False:
        raise submission_tag_not_found

    ##first check if all proteins exist
    N = DB.protein_groups.insert_bulk(protein_groups=set([q.tag for q in quantifications.quantifications]))
    num_quantifications = DB.submissions.insert_protein_quantifications(tag=submission_tag, quantifications=[ProteinGroupQuantificationModel(**q) for q in quantifications.model_dump().get("quantifications", []) if np.isfinite(q["value"])])
    #if num_quantifications != len(quantifications.quantifications):
    
    if apply_statistics:
        print("Calculating statistics...")
        DB.submissions.calculate_multiple_comparison_metrices(tag = submission_tag)
        DB.submissions.transform_quantification_to_zscore_along_protein_groups(tag = submission_tag)
        DB.submissions.transform_quantification_to_zscore_along_samples(tag = submission_tag)
        DB.submissions.transform_quantification_to_log2(tag = submission_tag)
    return num_quantifications


@router.patch("/{submission_tag}/protein_groups/statistics", summary="Calculate and insert the statistics for the protein groups of a given submission. Requires curator rights.")
def calculate_protein_group_statistics(submission_tag : str, user : UserModel = Depends(is_user_at_least_curator)):
    """
    Calculate and insert the statistics for the protein groups of a given submission. Requires curator rights.

    Parameters
    ----------
    submission_tag : str
        The tag of the submission.  
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(get_user_from_token)
    Returns
    -------
    bool
        True if the statistics were calculated and inserted successfully, False otherwise.
    """
    if DB.submissions.exists(tag=submission_tag) is False:
        raise submission_tag_not_found
    
    ok = DB.submissions.remove_multiple_comparison_metrices(tag = submission_tag)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to remove existing statistics. Aborting calculation of new statistics.")
    DB.submissions.calculate_multiple_comparison_metrices(tag = submission_tag)
    DB.submissions.transform_quantification_to_zscore_along_protein_groups(tag = submission_tag)
    DB.submissions.transform_quantification_to_zscore_along_samples(tag = submission_tag)
    DB.submissions.transform_quantification_to_log2(tag = submission_tag)
    DB.submissions.clear_stats_outdated(tag = submission_tag)
    return True

@router.post("/{submission_tag}/quantifications/proteins/precursors", summary="Bulk insert of precursor quantifications for a given submission. Requires curator rights.")
def insert_precursor_quantifications(
    submission_tag: str,
    quantifications: List[PrecursorQuantificationModel],
    user: UserModel = Depends(is_user_at_least_curator)
) -> int:
    """
    Bulk insert of precursor quantifications for a given submission. Requires curator rights.

    Parameters
    ----------
    submission_tag : str
        The tag of the submission.  
    quantifications : List[PrecursorQuantificationModel]
        List of precursor quantifications to insert.
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(get_user_from_token)
    Returns
    -------
    int
        Number of inserted precursor quantifications.
    """

    if DB.submissions.exists(tag=submission_tag) is False:
        raise submission_tag_not_found

    return DB.submissions.insert_precursor_quantifications(submission_tag=submission_tag, quantifications=quantifications)




@router.get("/{submission_tag}/quantifications/distribution", summary="Get the distribution of quantification values for a given submission and quantification type.")
def get_quantification_distribution(submission_tag : str, quantification_type : Literal["protein_groups","precursors"] = "protein_groups", annotation_tag : str = None, user : UserModel = Depends(get_user_from_token)) -> QuantileModel:
    """     
    Get the distribution of quantification values for a given submission and quantification type.

    Parameters
    ----------
    submission_tag : str
        The tag of the submission.  
    quantification_type : Literal["proteins","protein_groups","precursors"]
        The type of quantifications to get the distribution for.
    annotation_tag : str, optional
        The tag of the annotation, by default None
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(get_user_from_token)
    Returns
    -------
    Dict[str, QuantileModel]
        A dictionary where the keys are quantification identifiers and the values are QuantileModel instances representing the distribution of quantification values.
    """
    
    if not DB.submission_exists(tag=submission_tag): 
        raise submission_tag_not_found
    if not DB.submissions.quantification_exists(tag=submission_tag, type=quantification_type):
        raise HTTPException(status_code=404, detail=f"No quantifications of type {quantification_type} found for this submission.")
    return DB.submissions.get_quantification_distribution(submission_tag=submission_tag, quantification_type=quantification_type, annotation_tag=annotation_tag)




@router.get("/{submission_tag}/quantifications/test/distribution", summary="Calculate the distribtion based on a test (e.g. log2FC)")
def calculate_test_quantification_distribution(submission_tag : str,  
                                               ca_left_tag : str,
                                               ca_right_tag : str,
                                               attribute_tag : str = None,
                                               within_ca_tags : str = None,
                                               within_attribute_tags : str = None, 
                                               quantification_type : Literal["protein_groups","precursors"] = "protein_groups", 
                                               annotation_tag : str = None,
                                               annotation_group_tag : str = None,
                                               user : UserModel = Depends(get_user_from_token)) -> Dict:
    """     
    Calculate the distribution of quantification values for a given submission and quantification type based on a test (e.g. log2FC). This can be used to calculate the distribution for specific subsets of the data (e.g. only for significantly regulated protein groups).

    Parameters
    ----------
    submission_tag : str
        The tag of the submission.  
    quantification_type : Literal["proteins","protein_groups","precursors"]
        The type of quantifications to get the distribution for.
    """
    #  submission_tag=submission_tag, 
    #             ca_tag_left=testParam["ca_tag_left"],
    #             ca_tag_right=testParam["ca_tag_right"], 
    #             within_attribute_tags=testParam.get("within_attribute_tags", None), 
    #             within_ca_tags=testParam.get("within_ca_tags", None), 
    #             annotation_tag=testParam.get("annotation_tag", None)
    
    if not DB.submission_exists(tag=submission_tag): 
        raise submission_tag_not_found
    if not DB.submissions.quantification_exists(tag=submission_tag, type=quantification_type):
        raise HTTPException(status_code=404, detail=f"No quantifications of type {quantification_type} found for this submission.")
    
    return DB.samples.calculate_test_quantification_distribution(
        submission_tag=submission_tag,
        attribute_tag=attribute_tag,
        ca_tag_left=ca_left_tag,
        ca_tag_right=ca_right_tag,
        within_attribute_tags=within_attribute_tags,
        within_ca_tags=within_ca_tags,
        quantification_type=quantification_type,
        annotation_tag=annotation_tag,
        annotation_group_tag=annotation_group_tag
    )

@router.get("/{submission_tag}/stats/outdated", summary="Checks if the cached statistics for this submission are outdated (e.g. after excluding/including samples).")
def get_stats_outdated(submission_tag: str, user: UserModel = Depends(get_user_from_token)) -> bool:
    if not DB.submissions.exists(tag=submission_tag):
        raise submission_tag_not_found
    return DB.submissions.get_stats_outdated(tag=submission_tag)



@router.get("/{submission_tag}/samples/quantifications/distribution", summary="Get the distribution of quantification values for a given submission and quantification type.")
def get_sample_quantification_distribution(submission_tag : str, quantification_type : Literal["protein_groups","precursors"] = "protein_groups", annotation_tag : str = None, user : UserModel = Depends(get_user_from_token)) -> List[Tuple[str, QuantileModel, str]]:
    """     
    Get the distribution of quantification values for a given submission and quantification type.

    Parameters
    ----------
    submission_tag : str
        The tag of the submission.  
    quantification_type : Literal["protein_groups","precursors"]
        The type of quantifications to get the distribution for.
    annotation_tag : str, optional
        The tag of the annotation, by default None
    user : UserModel, optional
        The user that is extracted by the token, by default Depends(get_user_from_token)        
        """   
    DB.submission_exists(tag=submission_tag) or submission_tag_not_found
    if not DB.submissions.quantification_exists(tag=submission_tag, type=quantification_type):
        raise HTTPException(status_code=404, detail=f"No quantifications of type {quantification_type} found for this submission.")
    sample_tags = DB.submissions.get_samples(tag=submission_tag)
    ca = DB.samples.get_condition_applications_by_sample_for_submission(submission_tag=submission_tag, return_sample_index = False)  # Preload condition applications for efficiency
    #unique_ca_tags = 
        
    # 1. Combine all columns into one "||"-joined key
    ca['combo'] = ca.astype(str).agg('||'.join, axis=1)

    # 2. Get unique combinations
    unique_combos = ca['combo'].unique()
    n = len(unique_combos)

    # 3. Generate n visually distinct hex colors (works for any n, not capped at 20)
    # 3. Generate n visually distinct hex colors (pure Python, no matplotlib)
    def generate_hex_colors(n):
        colors = []
        for i in range(n):
            hue = i / n
            r, g, b = colorsys.hsv_to_rgb(hue, 0.65, 0.90)
            hex_color = '#{:02x}{:02x}{:02x}'.format(
                round(r * 255), round(g * 255), round(b * 255)
            )
            colors.append(hex_color)
        return colors

    hex_colors = generate_hex_colors(n)

    # 4. Build the color mapper: combo -> hex color
    color_mapper = dict(zip(unique_combos, hex_colors))

    # 5. (optional) map colors back onto the dataframe
    ca['color'] = ca['combo'].map(color_mapper)
    qs = []
    for sample_tag in sample_tags:
        q = DB.samples.get_quantification_distribution(tag=sample_tag, quantification_type=quantification_type, annotation_tag=annotation_tag)
        qs.append((sample_tag, q, ca.loc[ca.index == sample_tag, 'color'].values[0] if sample_tag in ca.index else '#000000'))  # Default to black if not found
    return qs