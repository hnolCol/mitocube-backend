from datetime import datetime
from config.enums.states import SubmissionStates
from config.models.attributes import Attribute
from config.models.submissions.submissions import NewSubmission
from config.models.user import User
from typing import List 

def check_for_missing_mandatory_attribute(submission : NewSubmission, attributes : List[Attribute]) -> List[Attribute]:
    """
    Checks if attributes are present in the submission
    : submission . Submission Model from a post request 
    : attributes . list of mandatory attributes 
    """
    datasetAttributeTags = [attribute.tag for attribute in submission.datasetAttributes]
    attrsNotInDatasetAttributes = [attribute for attribute in attributes if attribute.tag not in datasetAttributeTags]

    if len(attrsNotInDatasetAttributes) > 0:
        #missing mandatory attributes
        #they could still be in the sample attributes
        sampleAttributesTags = [sampleAttrDict["attribute"].tag for sampleAttrDict in  NewSubmission.samplesAttributes]
        attrNotInSamplteAttr = [attribute for attribute in attrsNotInDatasetAttributes if attribute.tag not in sampleAttributesTags]
        return attrNotInSamplteAttr 
    
    return []

def submission_to_json(submission : NewSubmission, user : User):
    """Returns a json object and extracts all the data from a new submission"""

    json = {}
    json["created_on"] = submission.created_on
    json["created_on_dt"] = datetime.fromtimestamp(submission.created_on).strftime("%m/%d/%Y, %H:%M:%S")
    json["state"] = SubmissionStates.SUBIMITTED
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
        #json["samples_attributes"][datasetAttribute.tag] = [attr.tag for attr in submission.datasetAttributeValues[datasetAttribute.tag]]
    return json 
