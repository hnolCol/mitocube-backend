from typing import Dict, List
import warnings

import lib.data.sql.postgresql as psql

from fastapi import APIRouter, Depends, HTTPException

from lib.rest.security import rest_verify_user_token, RestSessionInformation


router = APIRouter(prefix="/api/features",
                   tags=["Features"])

def deprecated_api(message):  # ToDo: Replace with from warnings import deprecated; @deprecated with python 3.13
    warnings.warn(message, DeprecationWarning, stacklevel=2)



@router.get("/{feature_key}/data", deprecated=True)  # ToDo Implement PRM, response_model=FeatureDataResponseModel)
def rest_get_dataset_data_by_feature(feature_key: str,  # Deprecated, implement /api/datasets/data/{feature_key}
                                     max_datasets: int = 200,
                                     session: RestSessionInformation = Depends(rest_verify_user_token)):
    # ToDo: Get datasets with feature feature_key

    # ToDo: Foreach dataset:
    # ToDo: 1)

    # db = MCDatabase.getDatabase()
    # db_helper = MCDatabaseHelper.getDatabaseHelper()
    # # dataset labels that contain the feature
    # dataset_labels = db_helper.get_labels_by_feature(feature_key)
    # # dataset_labels = db.getDataLabels()
    #
    # feature_data_by_dataset_label: Dict[str, pd.DataFrame] = {}
    # attributes_sample_by_dataset_label: Dict[str, Dict] = {}
    # attribute_samples_by_sample_collection = {}
    # attribute_values_by_tag_collection = {}
    # attributes_collection = {}
    # genotypes_by_dataset_label = {}
    # title_by_label = {}
    # for label in dataset_labels:
    #     dataset = db.getDataset(label=label)
    #     metadata = dataset.getMetaJson()
    #
    #     if dataset.hasData() and metadata.state == SubmissionStates.PUBLISHED:
    #         feature_data, attributes_samples, annotations = FeatureData(dataset).transform(feature_key,
    #                                                                                        add_annotations=True)
    #
    #         if not feature_data.empty and isinstance(feature_data, pd.DataFrame):
    #             updated_metadata = map_tags_to_attribute_in_metadata(metadata)
    #             # TODO this is something we could cash as as well? Mapping the tags from the DB to the actual attributes
    #             feature_data_by_dataset_label[label] = feature_data
    #             attributes_sample_by_dataset_label[label] = attributes_samples
    #             genotypes_by_dataset_label[label] = updated_metadata.genotypes
    #             ##update the attribute/attribute_value details to get the complete set of attributes required
    #             attribute_samples_by_sample_collection.update(updated_metadata.samples_attributes_by_sample)
    #             attribute_values_by_tag_collection.update(updated_metadata.attribute_values_by_tag)
    #             attributes_collection.update(updated_metadata.attributes)
    #             title_by_label[label] = metadata.title

    # FeatureDataResponseModel
    # AttributeModel
    # AttributeValueModel
    # FeatureModel
    return {"feature_key": feature_key,
            "samples_attributes": {},  # attributes_sample_by_dataset_label,  # Dict[str, Dict[str,List[str]]]
            "title_by_label": {},  # title_by_label  Dict[str, str]  # the title of the dataset
            "dataset_labels": {},  # List[str] list(feature_data_by_dataset_label.keys()),
            "samples_attributes_by_sample": {},  # attribute_samples_by_sample_collection, Dict[str, Dict[str,List[Union[AttributeValueModel,FeatureModel]]]]
            "attributes": {},  # attributes_collection Dict[str,AttributeModel] #The attributes by tags
            "attribute_values_by_tag": {},  # attribute_values_by_tag_collection Dict[str,Union[AttributeValueModel,FeatureModel]]
            "genotypes_by_label": {},  # genotypes_by_dataset_label Dict | None = None
            "data": {}  # dict([(data_label, data_frame.reset_index(names="index").to_dict(orient="records")) for data_label, data_frame in feature_data_by_dataset_label.items()])  # Dict[str, List[Dict]]
            }
