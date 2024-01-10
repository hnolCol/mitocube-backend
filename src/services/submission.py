from datetime import datetime
from config.enums.states import SubmissionStates
from config.models.attributes import AttributeModel
from config.models.submissions.submissions import NewSubmissionModel
from config.models.submissions.timeline import TimeLineModel, TimeLineEntryModel
from config.models.user import UserModel
from typing import List 

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
        json["dataset_attributes"][datasetAttribute.tag] = [attr.tag for attr in submission.datasetAttributeValues[datasetAttribute.tag]]
    ## add sample names
    json["sample_names"] = submission.sampleNames
    ## add replicate ids 
    json["replicates"] = submission.replicates 
    ## add samples attributes and add the sample name index
    samplesAttributesJson = {}
    for samplesAttribute in submission.samplesAttributes:
        sampleAttrTag = samplesAttribute.attribute.tag
        samplesAttributesJson[sampleAttrTag] = {"name" : samplesAttribute.name, "values" : {}}
    
    for n,sampleAttributeRow in enumerate(submission.attributeTable):
        #sampleName = submission.sampleNames[n]
        for sampleAttrTag, attributeValues in sampleAttributeRow.items():
            for attributeValue in attributeValues:
                if attributeValue.tag not in samplesAttributesJson[sampleAttrTag]["values"]:
                    samplesAttributesJson[sampleAttrTag]["values"][attributeValue.tag] = []
                samplesAttributesJson[sampleAttrTag]["values"][attributeValue.tag].append(n)
    json["samples_attributes"] = samplesAttributesJson
    #create timeline
    #overwrite what ever the user cretaed, change? 
    json["timeline"] = TimeLineModel(entries=[TimeLineEntryModel(id=0,comment="Project created", state=SubmissionStates.SUBMITTED, user_label=user.label)])
    return json 
