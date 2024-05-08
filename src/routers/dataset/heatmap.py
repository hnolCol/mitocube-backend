
from fastapi import APIRouter, Depends, HTTPException
from collections import OrderedDict

from lib.data.database.Database import Database
from lib.data.database.ABCDatabase import MCDatabase
from lib.data.annotations.ABCAnnotations import PandaFeatureDatabase

from lib.data.statistic.ANOVA import OneWayANOVA
from lib.data.clustering.HierarchicalClustering import HierarchicalClustering

from config.exceptions.HTTPExceptions import no_data_found
from config.models.user import UserModel

from services.users import get_user_from_token, is_user_at_least_curator
from services.submission import map_tags_to_attribute_in_metadata
DB = Database.DB()



router = APIRouter(
    prefix="/api",
    tags=["Heatmap"]
)
#heatmap endpoints 
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
    db = MCDatabase.getDatabase()
    dataset = db.getDataset(dataset_label)
    if dataset is None:
        raise HTTPException(status_code=400,detail="Data not found for given label.")
    if not dataset.hasData(): raise HTTPException(status_code=404,detail=f"No datatable found for the dataset {dataset_label}.")
    try:
        stats = OneWayANOVA(dataset).get_stats(dropna=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error in one way anova " + str(e))
    metadata = dataset.getMetaJson()
    if stats.empty or stats.index.size < 3: raise HTTPException(status_code=400, detail="No or less than 3 significant hits found using ANOVA. Please use a volcano plot.")
    #merge data and sort them after clusters.
    clusters, zscores = HierarchicalClustering(dataset).get_clusters(idcs = stats.index, n_clusters= n_clusters)
    stats_and_zscores = zscores.join([stats,clusters], how="left")
    clusters_for_group = clusters.loc[stats_and_zscores.index,:].reset_index() #index is now number, before keys
    grouped_clusters = clusters_for_group.groupby(by="cluster")
    cluster_indices = OrderedDict([(cluster_idx,cluster_data.index.to_list()) for cluster_idx, cluster_data in grouped_clusters])

    ##annotate features 
    #adjust proteome_id extraction TODO : ADJUST THIS!!
    #check if organism is defined
    proteome_ids =  [organism.split(":")[1] for organism in metadata.dataset_attributes["att_organism"]]
    feature_db = PandaFeatureDatabase()
   # features = feature_db.get(stats_and_zscores.index,proteome_ids,ignoreMissing=True)
    #print(features)
    features = DB.feature.get_protein_by_tags(stats_and_zscores.index.values.tolist())
    print(features,"NEO4J")
    #join features to the stat results
    #consider adding the features as an extra -> may be used to select features from the heatmap to view the detailed proteomics
    #data in a feature-centric way. 
    stats_and_zscores = stats_and_zscores.join(features,how="left")
    print(stats_and_zscores)
    return {
        "dataset_label" : dataset_label,
        "data" : stats_and_zscores.reset_index(names="Key").to_dict(orient="records"),
        "value_names" : metadata.sample_names,
        "label_names" : ["gene_name"],
        "color_names" : [],
        "cluster_indices" : cluster_indices,
        "n_clusters" : n_clusters
    }
