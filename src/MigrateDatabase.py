


import os
from typing import List, OrderedDict


from lib.database.Database import Database
from config.models.submissions.submissions import NewSubmissionModel
from config.models.submissions.states import SubmissionStatesEnums
from services.json import read_json
import numpy as np
from config.settings.metatexts import MetaTexts 


genotype_labels_path = "/Users/PParsa/Documents/GitHub/mitocube-backend/label_to_tag.json"
genotype_labels_to_tags = read_json(genotype_labels_path)

fall_back_user = "WX9r5zQJ"

proteom_mapper = {
    "att_organism:UP000005640" : "att_proteome:UP000005640",
    "att_organism:controls" : "att_proteome:ctrl"
}

protein_tag_mapper = {
    "att_organism:UP000005640" : "UP000005640",
    "att_organism:controls" : "ctrl"
}
DB = Database.DB()


attr_update = {
    "att_organism" : "att_proteome"
}


def handle_knockdown(tags : List[str]):
    "" 
    r = [] 
    protein_tag = tags.split(":")[1]
    proteome_tag = DB.proteomes.get_proteome_by_protein_tag(protein_tag = protein_tag)
    r = build_tree(attribute_tag = "att_knockdown_technique", trait_tags=["att_knockdown_technique:esirna"]) 
    r["children"][0]["children"].append(build_tree(attribute_tag="att_protein", trait_tags=[proteome_tag], value = protein_tag))
    return r 


# genotype_mapping = { 
            
#         } #genotype tags have changed, since the tag is not generate based on the data inserted. 


def build_tree(attribute_tag, trait_tags : List[str], value = None):
        if attribute_tag in attr_update:
            attribute_tag = attr_update[attribute_tag]
        return {"type" : "attribute", "tag" : attribute_tag, "children" : [{"type" : "trait", "tag" : trait_tag, "children" : [], "value" : value} for trait_tag in trait_tags]}

def get_tags_by_sample(samples_attrs : dict): 
    
   
    samples_idcs = np.sort(np.unique(np.concatenate([np.array(indices) for indices in samples_attrs.values()])))
    return [[genotype_tag for genotype_tag, indices in samples_attrs.items() if sample_idx in indices] for sample_idx in samples_idcs]
   
   
def map_genotype_labels_to_tags(samples_genotypes: dict):
    """Convert old genotype labels per sample into new genotype tags."""
    if not samples_genotypes:
        return []
    labels_by_sample = get_tags_by_sample(samples_genotypes)
    tags_by_sample = []
    for sample_labels in labels_by_sample:
        sample_tags = []
        for label in sample_labels:
            if label in genotype_labels_to_tags:
                sample_tags.append(genotype_labels_to_tags[label])
            else:
                print(f"WARNING: no genotype tag mapping for label '{label}'")
        tags_by_sample.append(sample_tags)
    return tags_by_sample


def build_sample_attributes(sample_attrs_input : dict):
    
    r = OrderedDict()
    for attribute_tag, sample_attrs in sample_attrs_input.items():
        if len(r) == 0:
            
            samples_idcs = np.sort(np.unique(np.concatenate([np.array(indices) for indices in sample_attrs.values()])))
            for idx in samples_idcs:
                r[idx] = []
                
        tags_by_sample_idcs = [(sample_idx, [sample_attribute for sample_attribute, idcs in sample_attrs.items() if sample_idx in idcs]) for sample_idx in samples_idcs]
        for sampleIdx, sample_attribute_tags in tags_by_sample_idcs:
            if attribute_tag == "att_knockdown":
                for tag in sample_attribute_tags:
                    r[sampleIdx].append(handle_knockdown(tag)) 
            else: 
                t = build_tree(attribute_tag=attribute_tag, trait_tags=sample_attribute_tags)
                r[sampleIdx].append(t)
    

    return list(r.values())
        
        
    #samples_idcs = np.sort(np.unique(np.array([list(samples_attrs.values())]).flatten()))
   
def build_dataset_condition_applications(dataset_attributes : dict): 
    "" 
    
    
    
    r = []
    for attribute_tag, trait_tags in dataset_attributes.items():
        r.append(build_tree(attribute_tag, trait_tags))
    return r


class MigrateData:
    
    def __init__(self, ):
        

        PATH_TO_SUBMISSION_FOLDER = "/Users/PParsa/Documents/GitHub/mitocube-backend/resources/data"
        dirList = [l for l in os.listdir(PATH_TO_SUBMISSION_FOLDER) if os.path.isdir(os.path.join(PATH_TO_SUBMISSION_FOLDER,l)) if l == "BuXOSlIl6G"] # only migrate one submission for testing, remove the if condition to migrate all submissions."]

        print(dirList)

   

        for submission_tag in dirList:
            print(submission_tag)
            jsonFile = read_json(os.path.join(PATH_TO_SUBMISSION_FOLDER,submission_tag,"params.json"))
            #user_tag = jsonFile["user_label"] if DB.users.exists(tag=jsonFile["user_label"]) else fall_back_user
            user_tag = jsonFile.get("user_tag") or jsonFile.get("user_label")
            if not user_tag or not DB.users.exists(tag=user_tag):
                user_tag = fall_back_user
            sample_names = jsonFile["sample_names"]
            sample_names = jsonFile["sample_names"]
            metatext = jsonFile["metatext"]
            meta_text = {k: v for k, v in jsonFile["metatext"].items() if k != "research_aim"}
            print(meta_text)
            #genotype_tags = get_tags_by_sample(jsonFile["samples_genotypes"]) if len(jsonFile["samples_genotypes"]) > 0 else []
            genotype_tags = map_genotype_labels_to_tags(jsonFile["samples_genotypes"])
            dataset_attributes = build_dataset_condition_applications(jsonFile["dataset_attributes"])
            
    
            sample_attributes = build_sample_attributes(jsonFile["samples_attributes"])
            print(sample_attributes)
            timeline = jsonFile.get("timeline", {})
            timeline_to_insert = [{"created_at" : t["created_on"] * 1000, "user_tag": t.get("user_tag") or t.get("user_label"), "state": t["state"]} for t in timeline.get("entries", [])] #timeline was previous in python timestamp, but in js frontend we use milliseconds, so we need to convert it by multiplying with 1000.
            if not DB.submission_exists(tag = submission_tag):
                submission_insert_model = NewSubmissionModel(tag = submission_tag,
                                                             user_tag= user_tag,
                                                            title=jsonFile.get("title", ""), 
                                                            replicates= jsonFile["replicates"],
                                                            metatext=meta_text, 
                                                            sample_names=sample_names, 
                                                            research_aim=metatext.get("metatext:research_aim", ""),
                                                            collaborators=jsonFile.get("collaborators", []),
                                                            genotypes=genotype_tags, 
                                                            samples_attributes=sample_attributes,
                                                            dataset_attributes=dataset_attributes)
        
                ok = DB.submissions.insert(tag = submission_insert_model.tag,
                        title = submission_insert_model.title,
                        user_tag = submission_insert_model.user_tag,
                        collaborators = submission_insert_model.collaborators)
                if ok: 
                    print("Submission inserted successfully.")
                DB.submissions.insert_attributes(tag = submission_insert_model.tag, traits = submission_insert_model.dataset_attributes) 
                 ## add meta text 
                DB.submissions.insert_research_aim(tag = submission_insert_model.tag, research_aim = submission_insert_model.research_aim, user_tag = submission_insert_model.user_tag)
                for tag, text in submission_insert_model.metatext.items():
                    if text is None or text.strip() == "":
                        continue
                    if tag in MetaTexts().names:
                        title = MetaTexts().names[tag]
                    else:
                        title = tag
                    
                    ok = DB.metatexts.insert(submission_tag= submission_insert_model.tag, title = title, text = text, user_tag = submission_insert_model.user_tag, ignore_exists_error=True)
             
                DB.submissions.set_state(tag = submission_insert_model.tag, state = jsonFile["state"], user_tag = submission_insert_model.user_tag) 
                DB.submissions.insert_state_history(tag = submission_insert_model.tag, state_history=timeline_to_insert)
                
                for idx,sample_name in enumerate(submission_insert_model.sample_names):
                 
                    sample_tag = DB.samples.insert(submission_tag = submission_insert_model.tag, sample_name = sample_name, sample_index = idx, return_tag_if_exists=True, connect_if_exists=True)
                    if idx < len(submission_insert_model.samples_attributes):
                        sample_attributes = submission_insert_model.samples_attributes[idx] 
                        DB.samples.insert_condition_application(sample_tag = sample_tag, sample_data = sample_attributes)

                    #connect sample to genotype_mapping
            
                    if idx < len(submission_insert_model.genotypes):
                        for genotype_tag in submission_insert_model.genotypes[idx]:
                            if DB.genotypes.exists(genotype_tag):
                                DB.samples.insert_genotype(
                                    sample_tags=[sample_tag],
                                    genotype_tag=genotype_tag,
                                )
                            else:
                                print(f"WARNING: genotype tag '{genotype_tag}' not found in DB, skipping for sample {sample_tag}")

                ### upoad quantification data. 
          
            else:
                print(f"Submission {submission_tag} already exists. Skipping.")
        # class DatasetSubmissionModel(BaseModel):
        #     ""
#     created_on : float
#     modified_on : Optional[float] = None
#     state : SubmissionStatesEnums
#     label : Optional[str] = None
#     tag : str
#     title : str
#     user_tag : str
#     collaborators : List[str]
#     replicates : List[int]
#     sample_names : List[str]
#     n_samples : int
#     metatext : Dict[str,str] = {}
#     dataset_attributes : Dict[str,List[str]]
#     samples_attributes : Dict[str,Dict[str,List[int]]]
#     samples_genotypes : Optional[Dict[str,List[int]]] = Field(...,default_factory=dict)
#     links : List[SubmissionLink] = []
#     timeline : TimeLineModel = Field(...,default_factory=TimeLineModel)
#     runlist : Optional[RunListModel] = None 
#     #samples_attributes_input : Optional[Dict[str,List[SampleAttributeInput]]] = None #input in terms of 'by the user' If input is allowed, it is defined in the attributes.
#     class Config:
#         use_enum_values = True 

    
    #DB.submissions.insert(submission_insert_model.dict())
    
    
    # if DB.submission_exists(tag = submission.tag):
    #     raise HTTPException(status_code=409, detail="Submission tag exists already. Use the update function to update the submission or use a different tag (/api/submissions/tag).")
    # DB.submissions.insert(tag = submission.tag,
    #                       title = submission.title,
    #                       user_tag = user.tag,
    #                       collaborators = submission.collaborators)
    # #set the state to submitted
    # DB.submissions.set_state(tag = submission.tag, state = SubmissionStatesEnums.SUBMITTED, user_tag = user.tag) 
    # DB.submissions.insert_attributes(tag = submission.tag, traits = submission.dataset_attributes) 
    # #insert samples and sample conditions (attributes/traits)
    # for idx,sample_name in enumerate(submission.sample_names):
    #         sample_tag = DB.samples.insert(submission_tag = submission.tag, sample_name = sample_name, sample_index = idx)
    #         sample_attributes = submission.samples_attributes[idx] 
    #         DB.samples.insert_condition_application(sample_tag = sample_tag, sample_data = sample_attributes)
            
    #         if submission.genotypes and idx < len(submission.genotypes):
    #             genotype_tags = submission.genotypes[idx] 
    #             if isinstance(genotype_tags, list):
    #                 for genotype_tag in genotype_tags: 
    #                     if DB.genotypes.exists(genotype_tag):  
    #                         DB.samples.insert_genotype(
    #                             sample_tags=[sample_tag],
    #                             genotype_tag=genotype_tag
    #                         )
    # ## add meta text 
    # DB.submissions.insert_research_aim(tag = submission.tag, research_aim = submission.research_aim, user_tag = user.tag)
    # for title, text in submission.metatext.items():
    #     DB.metatexts.insert(submission_tag= submission.tag, title = title, text = text, user_tag = user.tag)
    



MigrateData()