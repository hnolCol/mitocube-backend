from typing import Tuple, OrderedDict, List

import pandas as pd
import numpy as np 

from sklearn.decomposition import PCA

from lib.data.dataset.ABCDataset import MCDataset
from lib.data.transform.ABCTransform import DatasetTransform
from lib.data.annotate.samples.SampleAttributes import SampleAttributeAnnotation


class PCATransform(DatasetTransform):
    def __init__(self, dataset: MCDataset, n_components : int = 3, subset_index : pd.Index = None) -> None:
        """Principal Component Analysis for the datatable of a dataset. 

        Parameters
        ----------
        dataset : MCDataset
           The dataset from the dataset
        n_components : int, optional
            The number of components to be calculated by the PCA, by default 3
        subset_index : pd.Index, optional
            A pandas index to subset the data. A PCA does not allow missing values. 
            If the dataset contains missing values, provide the index that should be used (e.g. no missing data), by default None
        """
        super().__init__(dataset)
        self._n_components = n_components
        self._subset_index = subset_index 

    def transform(self) -> Tuple[pd.DataFrame,pd.DataFrame, np.ndarray, OrderedDict[str,List[str]]]:
        """Transforms the data into a lower dimensional dataset using a Principal Component Analysis.

        Returns
        -------
        Tuple[pd.DataFrame,pd.DataFrame, np.ndarray, OrderedDict[str,List[str]]]
            The projected data, the drivers, explained variance, and the samples attributes 
            TODO: Maybe change to a dict or pydantic model. 
        Raises
        ------
        Exception
            If the subsetting using the subset_index results in an empty dataframe. 
            If the dataset does not have any data yet (e.g. not active yet).
        """
        if not self._dataset.hasData(): raise Exception("No data were found for this dataset.")
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
        sample_names_annotaed ,samples_attributes = self._dataset.getSamplesAttributes()
        projected_data = projected_data.join(sample_names_annotaed)

        return projected_data, drivers, explained_variance, samples_attributes


