

from typing import Tuple
import fastcluster 
from scipy.stats import zscore
import scipy.cluster.hierarchy as sch
from lib.data.clustering.ABCCluster import DatasetClustering
import pandas as pd

class HierarchicalClustering(DatasetClustering):
    
    def get_clusters(self, idcs : pd.Series = None, n_clusters : int = 8) -> Tuple[pd.DataFrame,pd.DataFrame]:
        """
        
        Returns
        -------
        pd.DataFrame
            Dataframe with feature index key and a single column called "cluster" containing integer indices for the cluster
        pd.DataFrame
            Dataframe with feature index and columns (sample names) containing the transformed values (likely Z-Score.)
        """
        datatable = self._datatable
        ##subset the data that should be clustered (likely significant)
        if idcs is not None:
            datatable =  datatable.loc[idcs,:]
        values = zscore(datatable.values,axis=1,nan_policy="omit") #fastcluster does not allow nans - TODO: change
        row_linkage = fastcluster.linkage(values, method = "complete", metric = "euclidean")  
        max_distance = 0.75*max(row_linkage[:,2])
        Z_row = sch.dendrogram(row_linkage, orientation='left', color_threshold=max_distance, 
                                 leaf_rotation=90, ax = None, no_plot=True)
        #use the maximum number of clusters and find them
        clusters = sch.fcluster(row_linkage,n_clusters,'maxclust')
        ##get indices for clusters
        
        return pd.DataFrame(data = clusters, 
                            index = datatable.index,
                            columns = ["cluster"]), pd.DataFrame(values, 
                                                            index=datatable.index,
                                                            columns = datatable.columns).iloc[Z_row['leaves']]