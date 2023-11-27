
from collections import OrderedDict
import pandas as pd
from lib.data.annotate.samples.ABCSampleAnnotate import SampleAnnotation

from services.transforms import value_mapper_from_dict 

class SampleAttributeAnnotation(SampleAnnotation):

    def annotate(self) -> pd.DataFrame:
        """Annotates sample attributes"""
        #sample_names_values = self._dataset.getDataTable().columns.to_numpy()
        #sample_names = pd.DataFrame(index = sample_names_values)
        meta_data = self._dataset.getMetaJson()
        sample_names = meta_data.sample_names #mabe change to runnames
        attributes_samples = meta_data.samples_attributes #attributeTag -> sampleName Index
        sample_name_index_mapper  = dict([(idx,sample_name) for idx, sample_name in enumerate(meta_data.sample_names)])
    
        sample_idces = pd.DataFrame(index = list(range(meta_data.n_samples)))
        sample_attribute_by_name = OrderedDict()
        if not isinstance(attributes_samples,dict): TypeError("attributes_samples must be a dictionary.")
        for attributes  in  attributes_samples.values():
            sample_attribute_name = attributes.name 
            sample_attribute_values = attributes.values 
            attribute_mapper = value_mapper_from_dict(sample_attribute_values) 
            print(attribute_mapper)
            sample_idces.loc[:,sample_attribute_name] = sample_idces.index.map(attribute_mapper)
            sample_attribute_by_name[sample_attribute_name] = list(sample_attribute_values.keys())
        #replace indices with sample names
        sample_idces.index = sample_names
        return sample_idces, sample_attribute_by_name