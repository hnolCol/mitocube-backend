
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from lib.database.Database import Database
from config.models.user import UserModel
from config.enums.states import SubmissionStatesEnums
from services.users import get_user_from_token
from config.exceptions.HTTPExceptions import submission_tag_not_found, no_data_found_http_exception

from lib.data.statistic.Ttest import Ttest
from scipy.stats import ttest_ind, false_discovery_control
from config.models.dataset.pca import DatasetPCAResponse
import pandas as pd 
import numpy as np 
import re
DB = Database.DB()

router = APIRouter(
    prefix="/api/submissions/analysis",
    tags=["Submission"],
    )



#pca endpoints
@router.get("/{submission_tag}/volcano",
            tags=["Dimensional reduction","Volcano"])
def get_dataset_volcano(submission_tag : str, 
                        # attribute_tag : str,
                        ca_tag_left : str, 
                        ca_tag_right : str,
                        within_attribute_tags : str = None,
                        within_ca_tags : str = None,      
                      #  attribute_value_tag_left : str, attribute_value_tag_right : str, sample_attribute_tag : str, within_attribute_tag : str = None,
                        within_trait_tag : str = None, 
                        impute : bool = True,
                        annotation_tag : str = None, 
                        equal_variance : bool = True,
                        fdr : float = 0.05,
                        user : UserModel = Depends(get_user_from_token)
                  ):# ):#) #
    """
    Returns the result for a volcano plot
    
    Parameters
    ----------
    submission_tag : str
        The submission tag associated with the dataset.
    attribute_tag : str
        The attribute tag to compare.
    ca_tag_left : str
        The condition application tag for the left side of the comparison. For multiple tags, separate by ";"
    ca_tag_right : str
        The condition application tag for the right side of the comparison. For multiple tags, separate by ";"
    within_trait_tag : str, optional
        The trait tag to use for within-sample comparison, by default None
    impute : bool, optional
        If True, missing values are imputed, by default True
    annotation_tag : str, optional
        The annotation tag to use for filtering samples, by default None    
    """

    
    
    data_exist = DB.submission_has_dataset(tag = submission_tag)
    if not data_exist:  return no_data_found_http_exception
        
    if ca_tag_left == ca_tag_right:
        raise HTTPException(status_code=400, detail="Left and right condition application tags must be different.")
    
    condition_applications = DB.samples.get_condition_applications_by_sample_for_submission(submission_tag=submission_tag, sort_ca_tags=True, return_sample_index=False)  #preload condition applications
    print(DB.submissions.has_genotypes(tag = submission_tag))
    print(condition_applications)
    if DB.submissions.has_genotypes(tag = submission_tag):
        genotypes = DB.samples.get_genotypes_by_sample_for_submission(submission_tag=submission_tag, sort_ca_tags=True, return_sample_index=False)  #preload genotypes
        condition_applications = condition_applications.join(genotypes, how="outer")
    
    print(condition_applications)
    if DB.genotypes.exists(tag = ca_tag_left):
        attribute_tag = "att_genotype"
    else:
        attribute_tag = DB.condition_applications.get_attribute(ca_tag_left)
        
    if attribute_tag not in condition_applications.columns:
        raise HTTPException(status_code=404, detail=f"Attribute tag {attribute_tag} not found in sample condition applications for submission {submission_tag}.")
    
    # if within_trait_tag is not None:
    sample_tags_left = condition_applications[condition_applications[attribute_tag] == ca_tag_left].index
    sample_tags_right = condition_applications[condition_applications[attribute_tag] == ca_tag_right].index
    print(attribute_tag)
    print("before within filter:", len(sample_tags_left), len(sample_tags_right))
    if within_attribute_tags and within_ca_tags:
        within_attr_list = within_attribute_tags.split(";")
        within_ca_list = within_ca_tags.split(";")
        for within_attr, within_ca in zip(within_attr_list, within_ca_list):
            if within_attr in condition_applications.columns:
                mask = condition_applications[within_attr] == within_ca
                sample_tags_left = sample_tags_left[sample_tags_left.isin(condition_applications[mask].index)]
                sample_tags_right = sample_tags_right[sample_tags_right.isin(condition_applications[mask].index)]
    print("after within filter:", len(sample_tags_left), len(sample_tags_right))
  
    if attribute_tag == "att_genotype":
        print("GENOTYPE texts")
        print(DB.genotypes.get_text(ca_tag_left), DB.genotypes.get_text(ca_tag_right))
    ca_left_text = DB.condition_applications.get_text(ca_tag_left) if attribute_tag != "att_genotype" else DB.genotypes.get_text(ca_tag_left)
    ca_right_text = DB.condition_applications.get_text(ca_tag_right) if attribute_tag != "att_genotype" else DB.genotypes.get_text(ca_tag_right)

    def clean_ca_text(text):
        if text is None:
            return text
        # remove parentheses containing empty values 
        cleaned = re.sub(r'\(\s*[^)]*\)', lambda m: m.group() if any(c.isdigit() for c in m.group()) else '', text)
        return cleaned.strip()

    ca_left_text = clean_ca_text(ca_left_text)
    ca_right_text = clean_ca_text(ca_right_text)
    sample_tags = sample_tags_left.to_list() + sample_tags_right.to_list()

    suffix = f"{ca_left_text} vs. {ca_right_text}"
    if within_ca_tags:
        within_texts = []
        for t in within_ca_tags.split(";"):
            if t and DB.genotypes.exists(tag=t):
                within_texts.append(DB.genotypes.get_text(t) or t)
            elif t:
                within_texts.append(DB.condition_applications.get_text(t) or t)
        if within_texts:
            suffix += f" (within {', '.join(within_texts)})"
   # add within ca tag text
    if annotation_tag is not None:
        annotation_text = DB.annotations.get_text(tag=annotation_tag)
        suffix += f" ({annotation_text if annotation_text else annotation_tag})"
        
    # check if sample tags not empty 

    dt = DB.get_datatable(tag = submission_tag, annotation_tag= annotation_tag, sample_tags=sample_tags, use_sample_tags=True)
    if dt.empty:
        raise HTTPException(status_code=404, detail="No data found for the given submission and annotation tag. Ensure that the annotation tag is correct and that there is data available. Double check the ca_tags please.") 
    if sample_tags_left.size < 2 or sample_tags_right.size < 2:
        raise HTTPException(status_code=400, detail="At least two samples are required in each group for t-test.")
    
    X = dt.loc[:,sample_tags_left]
    Y = dt.loc[:,sample_tags_right]

    T,p = ttest_ind(X, Y, nan_policy="omit", axis=1, equal_var=equal_variance)
    p_value_name = f"p-value"
        
    #create data frame with the t-test statistics 
    stats = pd.DataFrame(
            {f"t-value {suffix}" : T, 
             p_value_name : p, 
             "tag" : dt.index,
             f"log2FC {suffix}" : X.mean(axis=1) - Y.mean(axis=1)
            }, 
            columns=[f"t-value {suffix}",p_value_name,"tag", f"log2FC {suffix}"]
            ).dropna(subset=[p_value_name])
    stats.loc[:,f"-log10 p-value {suffix}"] = -np.log10(stats.loc[:,p_value_name])
    stats.loc[:,f"fdr {suffix}"] = false_discovery_control(stats[p_value_name].values)
    stats.loc[:,f"Significant {suffix}"] = stats.loc[:,f"fdr {suffix}"] <= fdr
    # stats.loc[:,f"log2 FC"] = X.mean(axis=1) - Y.mean(axis=1)
    
    print("returning suffix:", suffix)
    print("ca_left_text:", ca_left_text, "ca_right_text:", ca_right_text)
    
    return {"stats" : stats.to_dict(orient="records"), 
            "suffix" : suffix, 
            "ca_tag_left": ca_tag_left, 
            "ca_tag_right": ca_tag_right, 
            "attribute_tag": attribute_tag, 
            "impute" : impute,
            "annotation_tag" : annotation_tag}
    
    # within_attribute_tag = APIParamString(param=within_attribute_tag).param 
    # within_attribute_value_tag = APIParamString(param=within_attribute_value_tag).param 
    
    comparison_suffix = f"{attribute_value_tag_left} vs. {attribute_value_tag_right} ({within_attribute_value_tag}) ({filter_tag})"
    datatable = DB.datasets.get_datatable(tag = dataset_tag, filter_tag = filter_tag)
    stats = Ttest(datatable, sample_map).get_stats(sample_attribute_tag=sample_attribute_tag, 
                                     attribute_value_left=attribute_value_tag_left, 
                                     attribute_value_right=attribute_value_tag_right, 
                                     suffix = comparison_suffix, 
                                     impute = impute,
                                     within_attribute_tag=within_attribute_tag,
                                     within_attribute_value_tag=within_attribute_value_tag)

    
    #features = DB.features.get_protein_by_tags(tags = datatable.index.to_list(), as_data_frame=True)
    #join features to the stat results
    stats_and_feature_data = stats.join(features,how="left").reset_index()
    print(stats_and_feature_data)
    print(stats_and_feature_data.to_dict(orient="records")[0])
    return {"stats" : stats_and_feature_data.to_dict(orient="records"), "suffix" : comparison_suffix}
    

