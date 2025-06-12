from datetime import datetime
from collections import OrderedDict
from lib.database.ABCDatabase import MCAttributes, MCDatabase
from lib.data.annotations.ABCAnnotations import PandaFeatureDatabase
from lib.data.genotype.PandaGenotype import PandaFileGenotype

from config.exceptions.HTTPExceptions import tag_not_found

from config.enums.states import SubmissionStatesEnums
from config.models.attributes import AttributeModel, AttributeValueModel
from config.models.annotations.feature import FeatureModel
from config.models.submissions.submissions import NewSubmissionModel, DatasetSubmissionModel, DatasetSubmissionResponseModel
from config.models.submissions.timeline import TimeLineModel, TimeLineEntryModel
from config.models.user import UserModel
from config.models.prefix import PrefixModel

from config.enums.units import TimeUnitToSecondsEnum, PrefixEnum

from typing import List, Dict, Literal
import pandas as pd 


def add_timeline_entry_to_metadata(metadata : dict, timelineEntry : TimeLineEntryModel):
    """Adds a timeline to the timeline. 
    Importantly, it is required to call .dump_model() before on the metadata

    Parameters
    ----------
    metadata : dict
        _description_
    timelineEntry : TimeLineEntryModel
        _description_
    """
    time_line = metadata["timeline"].copy()
    updated_entries = time_line["entries"] + [timelineEntry.model_dump()]
    time_line["entries"] = updated_entries
    metadata["timeline"] = TimeLineModel(**time_line)
    return metadata

def get_dataset_from_database(db : MCDatabase, label : str, force_reload : bool = False):
    """_summary_

    Parameters
    ----------
    db : MCDatabase
        _description_
    label : str
        _description_
    """
    try:
        dataset = db.getDataset(label)
        if dataset is None:
            raise tag_not_found
    except:
        raise tag_not_found
    
    return dataset

def map_tags(
             attribute : AttributeModel, 
             attr_value_tags : List[str], 
             proteome_ids : List[str], 
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
            return [FeatureModel(**f, tag = f"{attribute.tag}:{f['key']}") for f in db_features.get(keys=feature_keys, proteome_ids=proteome_ids).reset_index().to_dict(orient="records")]
            
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

def map_tags_to_attribute_in_metadata(submission : DatasetSubmissionModel):
    """

    Parameters
    ----------
    submission : _type_
        _description_
    """
    dataset_attributes = submission.dataset_attributes
    db_attributes = MCAttributes.getAttributeDatabase()
    db_features = PandaFeatureDatabase()
    db_genotypes = PandaFileGenotype()
    attributes= db_attributes.getAttributes().set_index("tag")
    #get the proteome ids as a list (multiple proteome_id possible)
    prot_id = dataset_attributes["att_organism"] if "att_organism" in dataset_attributes else dataset_attributes["att_proteome"]
    print(dataset_attributes)
    proteome_ids = [organism.split(":")[1] for organism in prot_id]
    attribute_values= db_attributes.getAttributeValues().set_index("tag")
    mapped_dataset_attributes = OrderedDict()
    mapped_attributes = dict()
    #map dataset attributes
    for attribute_tag, attr_value_tags in dataset_attributes.items():
        if attribute_tag == "att_organism":
            attribute_tag = "att_proteome"
        attribute = AttributeModel(**attributes.loc[attribute_tag,:].to_dict(), tag=attribute_tag)
        mapped_attributes[attribute_tag] = attribute
        mapped_attribute_values = map_tags(attribute,attr_value_tags,proteome_ids,attribute_values,db_features)    
        mapped_dataset_attributes[attribute_tag] = mapped_attribute_values
    #map sample attributes 
    
    sample_attributes = submission.samples_attributes
   
    sample_names = submission.sample_names
    sample_attribute_by_sample_name = OrderedDict([(sample_name, {}) for sample_name in sample_names])
    attribute_values_by_tag = {}
    
    for attribute_tag, sample_attribute in sample_attributes.items():
        if attribute_tag == "att_organism":
            attribute_tag = "att_proteome"
        attribute = AttributeModel(**attributes.loc[attribute_tag,:].to_dict(), tag=attribute_tag)
        if attribute_tag not in mapped_attributes:
            mapped_attributes[attribute_tag] = attribute
        
        attr_value_tags = sample_attribute.keys() 
       # mapped_sample_attributes[attribute_tag] = {}
        mapped_attribute_values = map_tags(attribute,attr_value_tags,proteome_ids,attribute_values,db_features)
        for attr_value_tag, mapped_attr_value in zip(attr_value_tags,mapped_attribute_values):
           # mapped_sample_attributes[attribute_tag]["attribute_values"][attr_value_tag] = mapped_attr_value
            if attr_value_tag not in attribute_values_by_tag:
                attribute_values_by_tag[attr_value_tag] = mapped_attr_value
            
        for attribute_value_tag, sampleIndices in sample_attribute.items():
            for sampleIdx in sampleIndices:
                sample_name = sample_names[sampleIdx]
                if attribute_tag not in sample_attribute_by_sample_name[sample_name]:
                    sample_attribute_by_sample_name[sample_name][attribute_tag] = []
                attribute_value = attribute_values_by_tag[attribute_value_tag]
                sample_attribute_by_sample_name[sample_name][attribute_tag].append(attribute_value)
    
    samples_genotypes = submission.samples_genotypes
    genotypes = {}
    if len(samples_genotypes) > 0:
        ##map genotypes by the keys
        genotypes_by_label = [(label,db_genotypes.get(label, ignore_missing=True)) for label in samples_genotypes.keys()] #missing genotypes will be none 
        genotypes = dict([(label,genotype) for label,genotype in genotypes_by_label if genotype is not None])
        mapped_attributes["att_genotype"] = AttributeModel(**attributes.loc["att_genotype",:].to_dict(), tag="att_genotype")
        

    metadata = submission.model_dump()     
    metadata["dataset_attributes"] = mapped_dataset_attributes 
    metadata["samples_attributes_by_sample"] = sample_attribute_by_sample_name
    metadata["attribute_values_by_tag"] = attribute_values_by_tag
    metadata["attributes"] = mapped_attributes
    metadata["genotypes"] = genotypes
   
                            
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
    datasetAttributeTags = submission.datasetAttributes
    # check dataset attributes first, then sample attributes. 
    attrsNotInDatasetAttributes = [attribute for attribute in attributes if attribute.tag not in datasetAttributeTags]

    # if len(attrsNotInDatasetAttributes) > 0:
    #     #missing mandatory attributes
    #     #they could still be in the sample attributes
    #     sampleAttributesTags = list(submission.samplesAttributes[0].keys()) #extract sample attributes from first item, all samples have the same 
    #     attrNotInSamplteAttr = [attribute for attribute in attrsNotInDatasetAttributes if attribute.tag not in sampleAttributesTags]
    #     return attrNotInSamplteAttr 
    
    return attrsNotInDatasetAttributes

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
    #json["created_on_dt"] = datetime.fromtimestamp(submission.created_on).strftime("%m/%d/%Y, %H:%M:%S")
    json["state"] = SubmissionStatesEnums.SUBMITTED
    json["tag"] = submission.tag
    json["title"] = submission.title 
    json["user_tag"] = user.tag
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
                genotype_tag = genotype.tag 
                if genotype_tag not in samples_genotypes:
                    samples_genotypes[genotype_tag] = []
                samples_genotypes[genotype_tag].append(n)
                
        json["samples_genotypes"] = samples_genotypes
    ## sample attributes 
    samplesAttributesJson = {}
    for samplesAttribute in submission.samplesAttributes:
        sampleAttrTag = samplesAttribute.tag
        samplesAttributesJson[sampleAttrTag] = {}
        
    for n,sampleAttributeRow in enumerate(submission.attributeTable):
        #sampleName = submission.sampleNames[n]
        for sampleAttrTag, attributeValues in sampleAttributeRow.items():        
            for attributeValue in attributeValues:
                if isinstance(attributeValue,FeatureModel) and attributeValue.tag is None:
                    #add tag for feature values
                    attributeValuesDict = attributeValue.model_dump(exclude_none=True)
                    attributeValue = FeatureModel(**attributeValuesDict, tag = f"{sampleAttrTag}:{attributeValue.key}")
                
                if attributeValue.tag not in samplesAttributesJson[sampleAttrTag]:
                    #add a list if not yet added, the list is filled with sample indices
                    samplesAttributesJson[sampleAttrTag][attributeValue.tag] = []
                    
                samplesAttributesJson[sampleAttrTag][attributeValue.tag].append(n)
    json["samples_attributes"] = samplesAttributesJson
    ## sample attribute input 
    user_input = {}
    # if submission.samplesAttributesInput is not None:
        
    #     for attribute_tag, sample_attr_input in submission.samplesAttributesInput.items():
    #         if attribute_tag not in samplesAttributesJson: continue
    #         user_input[attribute_tag] = []
    #         for sample_index,i in enumerate(sample_attr_input):
    #             for attribute_value_tag, sample_attr_value_input in i.items():
    #                 #check if the unit matches a given sample attribute, otherwise simply continue and ignore
    #                 if attribute_value_tag not in samplesAttributesJson[attribute_tag] or sample_index not in samplesAttributesJson[attribute_tag][attribute_value_tag]: continue
    #                 props = [{
    #                     "unit_tag" : unit_tag, 
    #                     "value" : input_value_to_standard_unit(value = float(input["value"]), 
    #                                                            prefix = input["prefix"] if "prefix" in input else "NA", 
    #                                                            is_time=unit_tag == "time", 
    #                                                            time_unit = input["time_unit"]),
    #                    } for unit_tag, input in sample_attr_value_input.items()] 
                    
    #                 user_input[attribute_tag].append(
    #                     {
    #                     "attribute_value_tag" : attribute_value_tag,
    #                     "sample_index" : sample_index,
    #                     "input" : props
    #                 })  
    
    # print(submission.samplesAttributesInput)
    # print(user_input)
    # json["samples_attributes_input"] = user_input

    
    
    
    #create timeline
    #overwrite what ever the user cretaed, change? 
    json["timeline"] = TimeLineModel(entries=[TimeLineEntryModel(id=0,comment="Project created", state=SubmissionStatesEnums.SUBMITTED, user_tag=user.tag)])
    return json 



def input_value_to_standard_unit(value, prefix = "NA", is_time : bool = False, time_unit : Literal["s","min","h","d","w","a"] = None):
    ""
    #get the multiplier from Prefix Model 
    
    prefix_multiplier = PrefixEnum[prefix].value
    print(prefix_multiplier)
    if not is_time:
        return value * prefix_multiplier
    else:
        time_unit_multiplier = TimeUnitToSecondsEnum[time_unit].value
        print(time_unit_multiplier)
        return value * prefix_multiplier * time_unit_multiplier