

import json 
import os 
from datetime import datetime
import time 
import numpy as np 
import pandas as pd 
from config.models.submissions.submissions import DatasetSubmissionModel
from config.models.submissions.states import SubmissionStates
from config.settings.metatexts import MetaTexts
from services.enums import get_inversed_enum_as_dict, get_enum_as_dict
from config.models.submissions.timeline import TimeLineEntryModel, TimeLineModel
from  collections import Counter
org = {
    "Saccharomyces cerevisiae (Baker's Yeast)" : "UP000002311", 
    "Homo sapiens (Human)" : "UP000005640", 
    "Mus musculus (Mouse)" : "UP000000589"
    }

metatextsSettings = MetaTexts()

def migrate_from_folder(submission_dir = "/Users/hnolte/Desktop/data/dynamic/submissions", user_label = "VpVff4sS", output_dir = "/Users/hnolte/Desktop/data/attribute_migration"):
    dirList = [l for l in os.listdir(submission_dir) if os.path.isdir(os.path.join(submission_dir,l))]
    states = get_enum_as_dict(enum=SubmissionStates)
    if not os.path.exists(output_dir):
        os.mkdir(output_dir )
    # "Organism": "Mus musculus (Mouse)",
    for submission_label in dirList:
        print(submission_label)
        jsonFile = json.load(open(os.path.join(submission_dir,submission_label,"params.json"),"r"))
        date = datetime.strptime(jsonFile["Creation Date"],"%Y%m%d")
        unixtime = date.timestamp()

        dataset_attributes = {
            "att_lysis_buffer": [
                "att_lysis_buffer:sds"
                ],
            "att_digestion_method": [
                "att_digestion_method:sp3"
            ],
            "att_protease": [
                "att_protease:trypsin"
            ],
            "att_experiment": [
                "att_experiment:expression_proteome"
            ]}

        dataset_attributes["att_organism"] = ["att_organism:"+org[jsonFile["Organism"]]]
        if "hela" in jsonFile["Material"].lower():
            dataset_attributes["att_cellline"] = ["att_celline:hela"]
        if "hek" in jsonFile["Material"].lower():
            dataset_attributes["att_cellline"] = ["att_celline:hel293T"]
        if "liver" in jsonFile["Material"].lower():
            dataset_attributes["att_organ"] = ["att_organ:liver"]
        if "brain" in jsonFile["Material"].lower():
            dataset_attributes["att_organ"] = ["att_organ:brain"]

        if "Whole proteome" in jsonFile["Type"]:
            dataset_attributes["att_experiment"] = ["att_experiment:expression_proteome"]
        elif "Pulse-SILAC" in jsonFile:
            dataset_attributes["att_experiment"] = ["att_experiment:pulse_silac"]
        elif "Immunoprecipitation" in jsonFile:
            dataset_attributes["att_experiment"] = ["att_experiment:interaction"]
        if "SampleNumber" in jsonFile:
            n_samples = jsonFile["SampleNumber"]
        else:
            n_samples = jsonFile["Number Samples"]
        
        groupings = jsonFile["groupings"]
        groupingNames = list(groupings.keys())
        sample_names = pd.Series(np.array([sampleName for groupName, groupItems in groupings[groupingNames[0]].items() for sampleName in groupItems]).flatten()).sort_values().unique().tolist()
        
       
        r={}
        samples_attributes = {}
        for groupingName, grouping in groupings.items():
            attName = f"att_{groupingName}"
            samples_attributes[attName] = {"name" : groupingName, "values" : {}}
            for groupName, groupItems in grouping.items():

                samples_attributes[attName]["values"][groupName] = [sample_names.index(sample_name) for sample_name in groupItems]

                for sample_name in groupItems:
                    if sample_name not in r:
                        r[sample_name] = []
                    r[sample_name].append(groupName)

        print(samples_attributes)


        
        
        
        metatexts  = dict([(metatextsSettings.tags["Experimental Procedure" if expInfo["title"] in ["Sample Preperation","Sample Preparation"] else expInfo["title"]],expInfo["details"]) for expInfo in jsonFile["Experimental Info"] if expInfo["title"] not in ["Comment","TMT Labelling"]])
        merged_groups = pd.DataFrame(["+".join(r[sample_name]) for sample_name in sample_names],columns=["g"])
        replicates = merged_groups.groupby("g").cumcount()+1

        
        if "updatedState" in jsonFile:
            timeLine = jsonFile["updatedState"]
            e = []
            for n, (stateName, timeString) in enumerate(timeLine.items()):
                if stateName.upper() == "DATA ANALYSIS":
                    stateName = "ANALYSIS"
                if stateName.upper() == "MEASURING PAUSED":
                    stateName = "PAUSED"
                e.append(TimeLineEntryModel(id = n,
                                            created_on=datetime.strptime(timeString,"%Y%m%d").timestamp(),
                                            user_label=user_label,
                                            state=states[stateName.upper()]))
                
                
            timeLineMolde = TimeLineModel(created_on=unixtime, modified_on= time.time(), entries=e)


        currentState = jsonFile["State"].upper() if jsonFile["State"].upper() not in ["MEASURING PAUSED","DATA ANALYSIS"] else jsonFile["State"].upper().split(" ")[-1]
        metadata = DatasetSubmissionModel(label=submission_label,
                             title=jsonFile["Title"],
                             state=states[currentState],
                             collaborators=[],
                            created_on=unixtime,
                            n_samples=n_samples,
                            sample_names=sample_names,
                            metatext=metatexts,
                            dataset_attributes=dataset_attributes,
                            samples_attributes=samples_attributes,
                            replicates=replicates.values.tolist(),
                            timeline=timeLineMolde,
                            user_label=user_label if isinstance(user_label,str) else user_label[jsonFile["Experimentator"]]
                            )
        submission_path = os.path.join(output_dir,submission_label)
        if not os.path.exists(submission_path):
            os.mkdir(submission_path)
        paramsFile = os.path.join(submission_path,"params.json")

        with open(paramsFile,"w", encoding ="utf-8") as f:
            json.dump(metadata.model_dump(exclude_none=True),f, indent=4, )










