
import pandas as pd
from lib.data.annotate.samples.ABCSampleAnnotate import SampleAnnotation

from services.transforms import value_mapper_from_dict 

class SampleAttributeAnnotation(SampleAnnotation):

    def annotate(self) -> pd.DataFrame:
        """Annotates sample attributes"""
        sample_names_values = self._dataset.getDataTable().columns.to_numpy()
        sample_names = pd.DataFrame(index = sample_names_values)
        
        attributes_samples = self._dataset.getMetaJson()["attributes_samples"]
        if not isinstance(attributes_samples,dict): TypeError("attributes_samples must be a dictionary.")
        for attribute_tag, attributes  in  attributes_samples.items():
            attribute_mapper = value_mapper_from_dict(attributes)
            sample_names.loc[:,attribute_tag] = sample_names.index.map(attribute_mapper)
        return sample_names, attributes_samples