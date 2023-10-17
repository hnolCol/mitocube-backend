
import pandas as pd
from typing import Tuple
from services.transforms import value_mapper_from_dict

from lib.data.dataset.ABCDataset import MCDataset
from lib.data.transform.ABCTransform import DatasetTransform
from lib.data.annotate.samples.SampleAttributes import SampleAttributeAnnotation
class FeatureData(DatasetTransform):
    """
    Transofmorms a dataset data by finding a
    feature key and returns a melted data frame (wide - long) when
    calling transform(). It attaches the grouping attributes. 
    """

    def transform(self, feature_id : str, add_sample_attributes : bool = True) -> Tuple[pd.DataFrame,dict]:
        """
        Returns the transformed data in a pandas data frame.
        """
        data = self._dataset.getDataTable()
        if feature_id not in data.index:
            return pd.DataFrame(), {} #ValueError(f"Feature ID was not found in the dataset {self._dataset.getLabel()}.")
        sample_names = data.columns.to_numpy()
        feature_data : pd.DataFrame = pd.DataFrame(data.loc[feature_id,sample_names].values, index = sample_names, columns=["value"]) #name is for the values in the pandas seeries return by loc 
        print(feature_data)
        if add_sample_attributes:
            sample_names_annotated, attributes_samples = SampleAttributeAnnotation(self._dataset).annotate()
            feature_data = feature_data.join(sample_names_annotated)
            print(feature_data)
            print(attributes_samples)
            
            return feature_data, attributes_samples
        return feature_data, {}

        