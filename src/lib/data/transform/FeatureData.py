
import pandas as pd
from typing import Tuple
from services.transforms import value_mapper_from_dict

from lib.data.dataset.ABCDataset import MCDataset
from lib.data.transform.ABCTransform import DatasetTransform
from lib.data.annotate.samples.SampleAttributes import SampleAttributeAnnotation
# from lib.data.annotations.ABCAnnotations import AnnotationSettings
 ##load fake features 
# A = pd.read_csv("/Users/hnolte/Documents/GitHub/mitocube-backend/resources/annotations/UP000000589/data.txt",sep="\t", index_col="Entry")
# A = A.rename(columns={"Gene Names" : "gene_name","Protein names":"protein_name","Length" : "length","Organism":"organism"})
# A.index.rename(name = "uniprot_id",inplace=True)




class FeatureData(DatasetTransform):
    """
    Transofmorms a dataset data by finding a
    feature key and returns a melted data frame (wide - long) when
    calling transform(). It attaches the grouping attributes. 
    """

    def transform(self, feature_id : str, add_sample_attributes : bool = True, add_annotations : bool = False) -> Tuple[pd.DataFrame,dict]:
        """
        Returns the transformed data in a pandas data frame.
        """
        ann = {}
        attributes_samples = {}
        data = self._dataset.getDataTable()
        metadata = self._dataset.getMetaJson()
        organism_id = metadata.dataset_attributes["att_organism"][0].split(":")[-1].upper() #should we allow more organism?
        if feature_id not in data.index:
            return pd.DataFrame(), {} #ValueError(f"Feature ID was not found in the dataset {self._dataset.getLabel()}.")
        sample_names = metadata.sample_names
        feature_data : pd.DataFrame = pd.DataFrame(data.loc[feature_id,sample_names].values, index = sample_names, columns=["value"]) #name is for the values in the pandas seeries return by loc 
        if add_sample_attributes:
            sample_names_annotated, attributes_samples = SampleAttributeAnnotation(self._dataset).annotate()
            feature_data = feature_data.join(sample_names_annotated)


        if add_annotations:
            annotation_db = Annotations.get_annotation_db()
            #get annotations!! 
            ann = {}
            ann = annotation_db.get_annotations_by_featureID(feature_id,organism_id)


            # if feature_id in A.index:
            #     ann = A.loc[feature_id,:].to_dict()
            #     ann["feature_id"] = feature_id
            
        return feature_data, attributes_samples, ann

        