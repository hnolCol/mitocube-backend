
from fastapi import APIRouter, Depends, HTTPException
from collections import OrderedDict

from lib.database.Database import Database
from lib.database.ABCDatabase import MCDatabase
from lib.data.annotations.ABCAnnotations import PandaFeatureDatabase

from lib.data.statistic.ANOVA import OneWayANOVA
from lib.data.clustering.HierarchicalClustering import HierarchicalClustering

from config.exceptions.HTTPExceptions import no_data_found_http_exception, filter_tag_does_not_exist_exception
from config.models.user import UserModel

from services.users import get_user_from_token
DB = Database.DB()

router = APIRouter(
    prefix="/api",
    tags=["Heatmap"]
)


@router.get("/datasets/{dataset_label}/heatmap",
            tags=["Heatmap"])
def get_dataset_heatmap(dataset_label : str, 
                        n_clusters : int = 8, 
                        filter_tag : str = None,
                        user : UserModel = Depends(get_user_from_token)):
    """
    Returns data to feed into a heatmap for visualization.
    
    Requires the definition of a statistical test to show a subset of the data. 

    """
    dataset_tag = dataset_label
    
    data_exist = DB.submission_has_dataset(tag=dataset_label)
    if not data_exist: return no_data_found_http_exception
    
    if filter_tag is not None:
        if not DB.filters.exists(tag = filter_tag):
            raise filter_tag_does_not_exist_exception
    
    datatable = DB.datasets.get_datatable(tag = dataset_tag, filter_tag = filter_tag)
    _, sample_map = DB.meta.get_sample_attributes_and_genotypes(dataset_tag)  
    
    try:
        stats = OneWayANOVA(datatable=datatable, sample_attribute_map=sample_map).get_stats(dropna=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error in one way anova " + str(e))
    
    if stats.empty or stats.index.size < 3: raise HTTPException(status_code=400, detail="No or less than 3 significant hits found using ANOVA. Please use a volcano plot.")
    #merge data and sort them after clusters.
    
    clusters, zscores = HierarchicalClustering(datatable).get_clusters(idcs=stats.index, n_clusters= n_clusters)
    stats_and_zscores = zscores.join([stats,clusters], how="left")
    clusters_for_group = clusters.loc[stats_and_zscores.index,:].reset_index() #index is now number, before keys
    grouped_clusters = clusters_for_group.groupby(by="cluster")
    cluster_indices = OrderedDict([(cluster_idx,cluster_data.index.to_list()) for cluster_idx, cluster_data in grouped_clusters])

    ##annotate features 
    #print(features)
    features = DB.features.get_protein_by_tags(stats_and_zscores.index.values.tolist())
    #join features to the stat results
    #consider adding the features as an extra -> may be used to select features from the heatmap to view the detailed proteomics
    #data in a feature-centric way. 
    stats_and_zscores = stats_and_zscores.join(features,how="left")
    return {
        "dataset_tag" : dataset_tag,
        "data" : stats_and_zscores.reset_index(names="Key").to_dict(orient="records"),
        "value_names" : datatable.columns.to_list(),
        "label_names" : ["gene_name"],
        "color_names" : [],
        "cluster_indices" : cluster_indices,
        "n_clusters" : n_clusters
    }
