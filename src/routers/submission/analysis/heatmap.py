
from fastapi import APIRouter, Depends, HTTPException
from collections import OrderedDict

from lib.database.Database import Database

from lib.data.statistic.ANOVA import OneWayANOVA
from lib.data.clustering.HierarchicalClustering import HierarchicalClustering

from config.exceptions.HTTPExceptions import no_data_found_http_exception, filter_tag_does_not_exist_exception
from config.models.user import UserModel
from config.exceptions.HTTPExceptions import submission_tag_not_found
from services.users import get_user_from_token
DB = Database.DB()

router = APIRouter(
    prefix="/api/submissions/analysis",
    tags=["Submission","Analysis","Heatmap"],
)


@router.get("/{submission_tag}/heatmap")
def get_heatmap(submission_tag : str, attribute_tag : str = None, annotation_tag : str = None, fdr : float = 0.05, n_clusters : int = 8, user : UserModel = Depends(get_user_from_token)):
    
    if not DB.submissions.exists(tag = submission_tag): raise submission_tag_not_found 
    if not DB.submissions.quantification_exists(tag = submission_tag, type = "proteins"): raise HTTPException(status_code=404, detail="No quantification data found for this submission.")
    
    condition_applications = DB.samples.get_condition_applications_by_sample_for_submission(submission_tag=submission_tag, sort_ca_tags=True, return_sample_index=False)  # already excludes excluded samples
    if DB.submissions.has_genotypes(tag = submission_tag):
        genotypes = DB.samples.get_genotypes_by_sample_for_submission(submission_tag=submission_tag, sort_ca_tags=True, return_sample_index=False)  #preload genotypes
        condition_applications = condition_applications.join(genotypes, how="outer")

    sample_tags = condition_applications.index.tolist()
    data_table = DB.get_datatable(tag = submission_tag, annotation_tag = annotation_tag, sample_tags = sample_tags, use_sample_tags=True)

    try:
        stats = OneWayANOVA(datatable=data_table, sample_attribute_map=condition_applications).get_stats(fdr= fdr, dropna=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error in one way anova " + str(e))
    if stats.empty or stats.index.size < 3: raise HTTPException(status_code=400, detail="No or less than 3 significant hits found using ANOVA. Please use a volcano plot.")
    clusters, zscores = HierarchicalClustering(data_table).get_clusters(idcs=stats.index, n_clusters= n_clusters)
    stats_and_zscores = zscores.join([stats,clusters], how="left")
    clusters_for_group = clusters.loc[stats_and_zscores.index,:].reset_index() #index is now number, before keys
    grouped_clusters = clusters_for_group.groupby(by="cluster")
    cluster_indices = OrderedDict([(cluster_idx,cluster_data.index.to_list()) for cluster_idx, cluster_data in grouped_clusters])
        
        
    return {
        "submission_tag" : submission_tag,
        "attribute_tag" : attribute_tag,
        "data" : stats_and_zscores.reset_index(names="tag").to_dict(orient="records"),
        "value_names" : data_table.columns.to_list(),
        "label_names" : ["tag"],
        "color_names" : [],
        "cluster_indices" : cluster_indices,
        "n_clusters" : n_clusters,
        "fdr" : fdr
    }