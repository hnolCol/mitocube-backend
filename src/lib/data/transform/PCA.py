from typing import Tuple

import pandas as pd
import numpy as np 

from sklearn.decomposition import PCA

from lib.data.dataset.ABCDataset import MCDataset
from lib.data.transform.ABCTransform import DatasetTransform
from lib.data.annotate.samples.SampleAttributes import SampleAttributeAnnotation


class PCATransform(DatasetTransform):
    """
    Transforms the data by dimensional reduction (PCA)
    """
    def __init__(self, dataset: MCDataset, n_components : int = 3, subset_index : pd.Index = None) -> None:
        super().__init__(dataset)
        self._n_components = n_components
        self._subset_index = subset_index 

    def transform(self) -> Tuple[pd.DataFrame,pd.DataFrame]:
        data = self._dataset.getDataTable()
        if self._subset_index is not None:
            data = data.loc[self._subset_index,:]
        if data.empty : raise Exception("Subset index based subsetting resulted in an empty dataset or the dataset is empty.")      

        #TO DO: scale?
        X = data.to_numpy()

        pca = PCA(n_components=self._n_components)  
        pca.fit(X)
        projection : np.ndarray = pca.transform(X)

        explained_variance = pca.explained_variance_ratio_
        component_names = [f"Component {n} ({round(explained_variance[n] * 100,2)}%)" for n in range(projection.shape[1])]

        drivers = pd.DataFrame(projection, index=self._subset_index, columns=component_names)

        #get PCA plot with samples_attributes annotations
        projected_data = pd.DataFrame(pca.components_.T,columns=component_names, index=data.columns.to_numpy())
        sample_names_annotaed ,samples_attributes = SampleAttributeAnnotation(self._dataset).annotate()
        projected_data = projected_data.join(sample_names_annotaed)

        return projected_data, drivers, explained_variance, samples_attributes


