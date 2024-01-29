from datetime import datetime
from collections import OrderedDict
from lib.data.database.ABCDatabase import MCAttributes
from lib.data.annotations.ABCAnnotations import PandaFeatureDatabase
from config.enums.states import SubmissionStates
from config.models.attributes import AttributeModel, AttributeValueModel
from config.models.annotations.feature import FeatureModel
from config.models.submissions.submissions import NewSubmissionModel, DatasetSubmissionModel, DatasetSubmissionResponseModel
from config.models.submissions.timeline import TimeLineModel, TimeLineEntryModel
from config.models.user import UserModel
from typing import List, Dict
import pandas as pd 


def map_tags(
             attribute : AttributeModel, 
             attr_value_tags : List[str], 
             proteome_id : str, 
             attribute_values : pd.DataFrame, 
             db_features : PandaFeatureDatabase ) -> List[AttributeValueModel]:
    """_summary_

    Parameters
    ----------
    mapped_dataset_attributes : _type_
        _description_
    """

    if not attribute.has_features_value and not attribute.has_numeric_input:
            return [AttributeValueModel(**attribute_values.loc[attr_value_tag,:].to_dict(), tag=attr_value_tag) for attr_value_tag in attr_value_tags]
    elif attribute.has_features_value:
            #if it is a feature, then add feature model 
            feature_keys = [attribute_value_tag.split(":")[1].upper() for attribute_value_tag in attr_value_tags]
            return [FeatureModel(**f, tag = f"{attribute.tag}:{f['key']}") for f in db_features.get(keys=feature_keys, proteome_id=proteome_id).reset_index().to_dict(orient="records")]
            
    elif attribute.has_numeric_input:
            #if a numeric input is there then first check if they are in the attribute_values and if not then extract the value from the tag 
            #and create an AttributeValueModel 
            attribute_value_tags_found = [attr_value_tag for attr_value_tag in attr_value_tags if attr_value_tag in attribute_values.index]
            attr_values_in_attribute_values = [AttributeValueModel( **attribute_values.loc[attr_value_tag,:].to_dict(), 
                tag=attr_value_tag) for attr_value_tag in attribute_value_tags_found]
            if len(attr_values_in_attribute_values) != len(attr_value_tags):
                attr_value_tags_with_numeric_input = [attr_value_tag for attr_value_tag in attr_value_tags if attr_value_tag not in attr_values_in_attribute_values]
                for attr_value_tag in attr_value_tags_with_numeric_input:
                    numeric_value = attr_value_tag.split(":")[1]
                    attr_values_in_attribute_values.append(AttributeValueModel(id=-1, 
                                                                               tag=f"{attribute.tag}:{numeric_value}",
                                                                               attribute_id=attribute.id,
                                                                               text=str(numeric_value),
                                                                               value=numeric_value, 
                                                                               description=f"{numeric_value} (user input)"))
            return attr_values_in_attribute_values    
    return []   

def map_tags_to_attributes(submission : DatasetSubmissionModel):
    """

    Parameters
    ----------
    submission : _type_
        _description_
    """
    dataset_attributes = submission.dataset_attributes
    db_attributes = MCAttributes.getAttributeDatabase()
    db_features = PandaFeatureDatabase()
    attributes= db_attributes.getAttributes().set_index("tag")
    print(attributes)
    proteome_id = dataset_attributes["att_organism"][0].split(":")[-1]
    attribute_values= db_attributes.getAttributeValues().set_index("tag")
    mapped_dataset_attributes = OrderedDict()
    mapped_attributes = dict()
    #map dataset attributes
    for attribute_tag, attr_value_tags in dataset_attributes.items():
        attribute = AttributeModel(**attributes.loc[attribute_tag,:].to_dict(), tag=attribute_tag)
        mapped_attributes[attribute_tag] = attribute
        mapped_attribute_values = map_tags(attribute,attr_value_tags,proteome_id,attribute_values,db_features)    
        mapped_dataset_attributes[attribute_tag] = mapped_attribute_values
    #map sample attributes 
    mapped_sample_attributes = OrderedDict()
    sample_attributes = submission.samples_attributes
    for attribute_tag, sample_attributes in sample_attributes.items():
        attribute = AttributeModel(**attributes.loc[attribute_tag,:].to_dict(), tag=attribute_tag)
        mapped_attributes[attribute_tag] = attribute
        attr_value_tags = sample_attributes.values.keys() 
        mapped_sample_attributes[attribute_tag] = {
            "name" : sample_attributes.name,
            "values" : sample_attributes.values,
            "attribute_values" : {}
        }
        mapped_attribute_values = map_tags(attribute,attr_value_tags,proteome_id,attribute_values,db_features)
        for attr_value_tag, mapped_attr_values in zip(attr_value_tags,mapped_attribute_values):
            mapped_sample_attributes[attribute_tag]["attribute_values"][attr_value_tag] = mapped_attr_values
                
    metadata = submission.model_dump()     
    metadata["dataset_attributes"] = mapped_dataset_attributes 
    metadata["samples_attributes"] = mapped_sample_attributes 
    metadata["attributes"] = mapped_attributes
                            
    return DatasetSubmissionResponseModel(**metadata)

    # return AttributeResponseModel(attributes=db_attributes.getAttributes().to_dict(orient="records"),
    #                               attribute_values=db_attributes.getAttributeValues().to_dict(orient="records"))
    

def check_for_missing_mandatory_attribute(submission : NewSubmissionModel, attributes : List[AttributeModel]) -> List[AttributeModel]:
    """
    Checks if attributes are present in the submission and takes the 
    dataset attributes as well as the sample attributes into account. 

    Parameters
    ----------
    submission : NewSubmissionModel
        The submission to check for missing attributes
   
    attributes : List[AttributeModel]
        The mandatory attributes.

    Returns 
    -------
        List[AttributeModel]
            The list of attributes that are misssing in the submission. 
            If the list is empty, all attributes were found. 
    """
    datasetAttributeTags = [attribute.tag for attribute in submission.datasetAttributes]
    # check dataset attributes first, then sample attributes. 
    attrsNotInDatasetAttributes = [attribute for attribute in attributes if attribute.tag not in datasetAttributeTags]

    if len(attrsNotInDatasetAttributes) > 0:
        #missing mandatory attributes
        #they could still be in the sample attributes
        sampleAttributesTags = [sampleAttrDict["attribute"].tag for sampleAttrDict in  NewSubmissionModel.samplesAttributes]
        attrNotInSamplteAttr = [attribute for attribute in attrsNotInDatasetAttributes if attribute.tag not in sampleAttributesTags]
        return attrNotInSamplteAttr 
    
    return []

def submission_to_json(submission : NewSubmissionModel, user : UserModel) -> dict:
    """
    Returns a json object and extracts all the data from a new submission. 
    Should exclusively be used when a new submission is created and not to save a json file. 

    Parameters
    ----------
    submission : NewSubmissionModel 
        The submission to create a JSON file from. 
    user : UserModel 
        The user that posted the new submission. 

    Returns
    -------
    dict
        Submission data in a dict format. 
    """

    json = {}
    json["created_on"] = submission.created_on
    json["created_on_dt"] = datetime.fromtimestamp(submission.created_on).strftime("%m/%d/%Y, %H:%M:%S")
    json["state"] = SubmissionStates.SUBMITTED
    json["label"] = submission.label 
    json["title"] = submission.title 
    json["user_label"] = user.label 
    json["collaborators"] = [user.label for user in submission.collaborators]
    json["n_samples"] = len(submission.sampleNames) 
    json["links"] = [link.model_dump() for link in  submission.links]
    
    ## add metatext 
    json["metatext"] = {}
    for metatext_tag, metatext in submission.metatext.items():
        json["metatext"][metatext_tag] = metatext

    ## add dataset attributes
    json["dataset_attributes"] = {}
    for datasetAttribute in submission.datasetAttributes:
        json["dataset_attributes"][datasetAttribute.tag] = [attr.tag if isinstance(attr,AttributeValueModel) else f"{datasetAttribute.tag}:{attr.key}" for attr in submission.datasetAttributeValues[datasetAttribute.tag]]
    ## add sample names
    json["sample_names"] = submission.sampleNames
    ## add replicate ids 
    json["replicates"] = submission.replicates 
    ## add samples attributes and add the sample name index
    ##genotype samples
    if submission.genotypes is not None:
        samples_genotypes = OrderedDict()
        for n,selected_genotypes in enumerate(submission.genotypes):
            for genotype in selected_genotypes:
                if genotype.label not in samples_genotypes:
                    samples_genotypes[genotype.label] = []
                samples_genotypes[genotype.label].append(n)
                
        json["samples_genotypes"] = samples_genotypes
    
    samplesAttributesJson = {}
    for samplesAttribute in submission.samplesAttributes:
        sampleAttrTag = samplesAttribute.attribute.tag
        samplesAttributesJson[sampleAttrTag] = {"name" : samplesAttribute.name, "values" : {}}
    for n,sampleAttributeRow in enumerate(submission.attributeTable):
        #sampleName = submission.sampleNames[n]
        for sampleAttrTag, attributeValues in sampleAttributeRow.items():        
            for attributeValue in attributeValues:
                if isinstance(attributeValue,FeatureModel) and attributeValue.tag is None:
                    #add tag for feature values
                    attributeValuesDict = attributeValue.model_dump(exclude_none=True)
                    attributeValue = FeatureModel(**attributeValuesDict, tag = f"{sampleAttrTag}:{attributeValue.key}")
                
                if attributeValue.tag not in samplesAttributesJson[sampleAttrTag]["values"]:
                    samplesAttributesJson[sampleAttrTag]["values"][attributeValue.tag] = []
                samplesAttributesJson[sampleAttrTag]["values"][attributeValue.tag].append(n)
    json["samples_attributes"] = samplesAttributesJson
    #create timeline
    #overwrite what ever the user cretaed, change? 
    json["timeline"] = TimeLineModel(entries=[TimeLineEntryModel(id=0,comment="Project created", state=SubmissionStates.SUBMITTED, user_label=user.label)])
    return json 
