
import pandas as pd
from typing import Tuple

from lib.data.annotations.ABCAnnotations import AnnotationDatabase
from services.transforms import value_mapper_from_dict

from lib.data.dataset.ABCDataset import MCDataset
from lib.data.transform.ABCTransform import DatasetTransform
from lib.data.annotate.samples.SampleAttributes import SampleAttributeAnnotation


class FeatureData(DatasetTransform):
    """
    Transoforms a dataset data by finding a
    feature key and returns a melted data frame (wide - long) when
    calling transform(). It attaches the grouping attributes. 
    """

    def transform(self, feature_key : str, add_sample_attributes : bool = True, add_annotations : bool = False) -> Tuple[pd.DataFrame,dict]:
        """
        Returns the transformed data in a pandas data frame.
        """
        annotations = {}
        attributes_samples = {}
        data = self._dataset.getDataTable()
        metadata = self._dataset.getMetaJson()
        #TODO: move this somewhere else.. 
        proteome_id =  metadata.dataset_attributes["att_organism"][0].split(":")[-1].upper()  # should we allow more organism?

        if feature_key not in data.index:
            return pd.DataFrame(), {}  # ValueError(f"Feature ID was not found in the dataset {self._dataset.getLabel()}.")

        sample_names = metadata.sample_names
        feature_data : pd.DataFrame = pd.DataFrame(data.loc[feature_key,sample_names].values, index = sample_names, columns=["value"])  # name is for the values in the pandas seeries return by loc

        if add_sample_attributes:
            sample_names_annotated, attributes_samples = SampleAttributeAnnotation(self._dataset).annotate()  # ToDo: What is it supposed to do here?
            feature_data = feature_data.join(sample_names_annotated)

        if add_annotations:
            # annotation_db = Annotations.get_annotation_db()  # ToDo: where does that comes from?
            db_annotations = AnnotationDatabase()
            print(proteome_id,feature_key)
            annotations[feature_key] = db_annotations.getAnnotations(feature_key=feature_key, proteome_id=proteome_id, subset=["GOAnnotation"])
        print(annotations)
        return feature_data, attributes_samples, annotations

        