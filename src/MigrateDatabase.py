

import os
import time 
from typing import List, OrderedDict


from lib.database.Database import Database
from config.models.submissions.submissions import NewSubmissionModel
from config.models.submissions.states import SubmissionStatesEnums
from config.models.submissions.quantifications import ProteinGroupQuantificationModel
from config.models.submissions.runs import AnalyticRunModel, RunListModel

from services.json import read_json
import numpy as np
from config.settings.metatexts import MetaTexts 
import pandas as pd


proteom_mapper = {
    "att_organism:UP000000589" : "proteome:UP000000589", #mouse 
    "att_organism:UP000005640" : "att_proteome:UP000005640", #human
    "att_organism:controls" : "att_proteome:ctrl" #ctrl proteins
}

protein_tag_mapper = {
    "att_organism:UP000005640" : "UP000005640",
    "att_organism:controls" : "ctrl"
}
DB = Database.DB()


attr_update = {
    "att_organism" : "att_proteome"
}

time_to_att_duration = {
    "s":   "att_duration:s",   # Seconds
    "min": "att_duration:min", # Minutes
    "h":   "att_duration:h",   # Hours
    "d":   "att_duration:d",   # Days 
    "w":   "att_duration:w",   # Weeks
    "a":   "att_duration:a",   # A Year
}

def handle_knockdown(tags : List[str], technique_trait_tag : str = "att_knockdown_technique:esirna"):
    "" 
    r = [] 
    protein_tags = [t.split(":")[1] for t in tags]
   # print(f"Handling knockdown for protein tags: {protein_tags}")
    proteome_tag = DB.proteomes.get_proteome_by_protein_tag(protein_tag = protein_tags[0])
    r = build_tree(attribute_tag = "att_knockdown_technique", trait_tags=[technique_trait_tag]) 
    r["children"][0]["children"].append(build_tree(attribute_tag="att_protein", trait_tags=[proteome_tag], value = "||".join(protein_tags)))
    return r 

def handle_batch(tags : List[str]):
    "" 
    values = [t.split(":")[1] for t in tags] 
    tree =  build_tree(attribute_tag="att_batch_type", trait_tags=["att_batch_type:quant"])
    tree["children"][0]["children"].extend([build_tree(attribute_tag="att_batch", trait_tags=["att_batch:string"], value=v) for v in values])
    return tree 

def handle_clone_id(tags : List[str]):
    "" 
    values = [t.split(":")[1] for t in tags] 
    tree =  build_tree(attribute_tag="att_batch_type", trait_tags=["att_batch_type:clone"])
    tree["children"][0]["children"].extend([build_tree(attribute_tag="att_batch", trait_tags=["att_batch:string"], value=v) for v in values])
    return tree 

def build_tree(attribute_tag, trait_tags : List[str], value = None):
        if attribute_tag in attr_update:
            attribute_tag = attr_update[attribute_tag]
            
        return {"type" : "attribute", "tag" : attribute_tag, "children" : 
            [{"type" : "trait", "tag" : trait_tag, "children" : [], "value" : value[idx] if isinstance(value, list) else value } for idx, trait_tag in enumerate(trait_tags)]}


def handle_centrifugation_pellet(tags : List[str]):
    
    tree = build_tree(attribute_tag="att_centrifugation", trait_tags=["att_centrifugation:pellet"])
    for t in tags:
        tree["children"][0]["children"].append(build_tree(attribute_tag="att_cent_acc", trait_tags=["att_cent_acc"], value=t.split(":")[1]))
    print(f"Handling centrifugation with tags {tags}, resulting tree: {tree}")
    return tree

def handle_centrifugation_supernatant(tags : List[str]):
    
    tree = build_tree(attribute_tag="att_centrifugation", trait_tags=["att_centrifugation:supernatant"])
    for t in tags:
        tree["children"][0]["children"].append(build_tree(attribute_tag="att_cent_acc", trait_tags=["att_cent_acc"], value=t.split(":")[1]))
    print(f"Handling centrifugation with tags {tags}, resulting tree: {tree}")
    return tree

def get_tags_by_sample(samples_attrs : dict): 
    
   
    samples_idcs = np.sort(np.unique(np.concatenate([np.array(indices) for indices in samples_attrs.values()])))
    return [[tag for tag, indices in samples_attrs.items() if sample_idx in indices] for sample_idx in samples_idcs]
   
   
def map_genotype_labels_to_tags(samples_genotypes: dict, genotype_labels_to_tags: dict):
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


def _build_duration_child_for_sample(sample_idx: int, time_data_by_key: dict):
    """time_data_by_key maps {att_time_<unit>: {trait_tag: [indices]}} for this submission.
    Returns an att_duration subtree for whichever time entry covers this sample, or None."""
    for time_key, sample_attrs in time_data_by_key.items():
        unit = time_key.replace("att_time_", "")
        trait_tag = time_to_att_duration.get(unit)
        if trait_tag is None:
            print(f"WARNING: unknown time unit '{unit}' from key '{time_key}'")
            continue
        for legacy_trait, indices in sample_attrs.items():
            if sample_idx in indices:
                try:
                    value = float(legacy_trait.split(":")[1])
                except (IndexError, ValueError):
                    print(f"WARNING: could not parse value from '{legacy_trait}'")
                    return None
                return {
                    "type": "attribute",
                    "tag": "att_duration",
                    "children": [
                        {"type": "trait", "tag": trait_tag, "value": value, "children": []}
                    ],
                }
    return None

def build_sample_attributes(sample_attrs_input: dict, dataset_attributes: dict):
    r = OrderedDict()
    
    time_data_by_key = {
        k: sample_attrs_input.pop(k)
        for k in list(sample_attrs_input.keys())
        if k.startswith("att_time_")
    }
    
    for attribute_tag, sample_attrs in sample_attrs_input.items():
        if len(r) == 0:
            samples_idcs = np.sort(np.unique(np.concatenate([np.array(indices) for indices in sample_attrs.values()])))
            for idx in samples_idcs:
                r[idx] = []
        
        tags_by_sample_idcs = [(sample_idx, [sample_attribute for sample_attribute, idcs in sample_attrs.items() if sample_idx in idcs]) for sample_idx in samples_idcs]
        for sampleIdx, sample_attribute_tags in tags_by_sample_idcs:
            if attribute_tag == "att_knockdown":                
                technique_trait_tag = dataset_attributes["att_knockdown_technique"][0] if "att_knockdown_technique" in dataset_attributes else "att_knockdown_technique:esirna"
                r[sampleIdx].append(handle_knockdown(sample_attribute_tags, technique_trait_tag=technique_trait_tag))
            elif attribute_tag == "att_batch":
                r[sampleIdx].append(handle_batch(sample_attribute_tags))    
            elif attribute_tag == "att_clone_id":
                r[sampleIdx].append(handle_clone_id(sample_attribute_tags))
            elif attribute_tag == "att_centr_pellet":
                r[sampleIdx].append(handle_centrifugation_pellet(sample_attribute_tags))
            elif attribute_tag == "att_centr_supernatant":
                r[sampleIdx].append(handle_centrifugation_supernatant(sample_attribute_tags))
            elif attribute_tag == "att_compound" and time_data_by_key:
                duration_child = _build_duration_child_for_sample(sampleIdx, time_data_by_key)
                tree = {
                    "type": "attribute",
                    "tag": "att_compound",
                    "children": [
                        {
                            "type": "trait",
                            "tag": trait_tag,
                            "value": None,
                            "children": [duration_child] if duration_child else [],
                        }
                        for trait_tag in sample_attribute_tags
                    ],
                }
                r[sampleIdx].append(tree)
            else:
                t = build_tree(attribute_tag=attribute_tag, trait_tags=sample_attribute_tags)
                r[sampleIdx].append(t)
    
    return list(r.values())
   
def build_dataset_condition_applications(dataset_attributes : dict): 
    "" 
    r = []
    for attribute_tag, trait_tags in dataset_attributes.items():
        
        if attribute_tag == "att_batch":
            r.append(handle_batch(trait_tags))    
        elif attribute_tag == "att_clone_id":
            r.append(handle_clone_id(trait_tags))
        elif attribute_tag == "att_centr_pellet":
            r.append(handle_centrifugation_pellet(trait_tags))
        elif attribute_tag == "att_centr_supernatant":
            r.append(handle_centrifugation_supernatant(trait_tags))
        else:
            r.append(build_tree(attribute_tag, trait_tags))
    return r
        
class MigrateData:
    
    def __init__(self, path_to_submission_folder : str = None, genotype_labels_path : str = None, fallback_user_tag : str = None):
        
        if not os.path.exists(path_to_submission_folder):
            raise ValueError(f"Path to submission folder does not exist: {path_to_submission_folder}")
        
        if not os.path.exists(genotype_labels_path):
            raise ValueError(f"Path to genotype labels file does not exist: {genotype_labels_path}")
        
        self.path_to_folder = path_to_submission_folder  #or "/Users/PParsa/Documents/GitHub/mitocube-backend/resources/data"
        self.dirList = [l for l in os.listdir(self.path_to_folder) if os.path.isdir(os.path.join(self.path_to_folder,l)) ] # only migrate one submission for testing, remove the if condition to migrate all submissions."]
        self.fallback_user_tag = fallback_user_tag # "user_lead" # if the user specified in the submission json file does not exist in the database, the submission will be assigned to this user. This should be the tag of an existing user in the database, ideally the lead user.
        self.genotype_labels_path = genotype_labels_path #or "/Users/PParsa/Documents/GitHub/mitocube-backend/label_to_tag.json"

        self.genotype_labels_to_tags = read_json(genotype_labels_path)

        print(f"Found submission folders: {self.dirList}")
        print("Execute run() to start the migration.")
        
    def run(self):

        for submission_tag in self.dirList:
            df = None
            jsonFile = read_json(os.path.join(self.path_to_folder,submission_tag,"params.json"))
            path_to_quant = os.path.join(self.path_to_folder,submission_tag,"data.txt") 
            path_to_quant_exists = os.path.exists(path_to_quant)
            if path_to_quant_exists:
                df = pd.read_csv(path_to_quant, sep="\t").set_index("Key")
                df.columns = [f"{submission_tag}|{col}" for col in df.columns]
            #user_tag = jsonFile["user_label"] if DB.users.exists(tag=jsonFile["user_label"]) else fall_back_user
            user_tag = jsonFile.get("user_tag") or jsonFile.get("user_label")
            if not user_tag or not DB.users.exists(tag=user_tag):
                user_tag = self.fallback_user_tag       
            sample_names = jsonFile["sample_names"]
            metatext = jsonFile["metatext"]
            meta_text = {k: v for k, v in jsonFile["metatext"].items() if k != "research_aim"}
            #genotype_tags = get_tags_by_sample(jsonFile["samples_genotypes"]) if len(jsonFile["samples_genotypes"]) > 0 else []
            genotype_tags = map_genotype_labels_to_tags(jsonFile["samples_genotypes"], self.genotype_labels_to_tags)
            dataset_attributes = build_dataset_condition_applications(jsonFile["dataset_attributes"])

            sample_attributes = build_sample_attributes(jsonFile["samples_attributes"], jsonFile["dataset_attributes"])
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
                 
                    sample_tag = DB.samples.insert(submission_tag = submission_insert_model.tag, sample_name = sample_name, replicate= submission_insert_model.replicates[idx],  sample_index = idx, return_tag_if_exists=True, connect_if_exists=True)
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
                if df is not None:
                    df_melt = df.reset_index(names="tag").melt(id_vars=["tag"], var_name="sample_tag", value_name="value").dropna(subset=["value"])
                    print(df_melt)
                    df_melt = df_melt.dropna(subset=["tag","value"])
                    df_melt["value"] = pd.to_numeric(df_melt["value"], errors="coerce")
                    df_melt = df_melt[
                        df_melt["value"].notna() & np.isfinite(df_melt["value"])
                    ]
                    N = DB.protein_groups.insert_bulk(protein_groups=df_melt["tag"].unique().tolist())
                    DB.submissions.insert_protein_quantifications(tag=submission_tag, quantifications=[ProteinGroupQuantificationModel(**x) for x in df_melt.to_dict(orient="records") ]) 
                    DB.submissions.transform_quantification_to_zscore_along_protein_groups(tag = submission_tag)
                    DB.submissions.transform_quantification_to_zscore_along_samples(tag = submission_tag)
                    DB.submissions.calculate_multiple_comparison_metrices(tag = submission_tag)
                    time.sleep(1) # to avoid overwhelming the database with too many requests in a short time, especially when migrating multiple submissions. Adjust the sleep duration as needed based on the size of the data and the performance of the database.
                    print(f"Quantification data for submission {submission_tag} inserted and processed successfully.")

                ### migrate runlist if exists
                if "runlist" in jsonFile and jsonFile["runlist"]:
                    old_runlist = jsonFile["runlist"]
                    runs = [AnalyticRunModel(**old_run) for old_run in old_runlist.get("runs", [])]
                    
                    # Check for instrument in runlist first, then fall back to dataset attributes
                    instrument_tag = old_runlist.get("instrument_tag", None)
                    
                    if instrument_tag is None:
                        # Check dataset attributes for instrument (att_ms)
                        dataset_attributes = jsonFile.get("dataset_attributes", {})
                        ms_instruments = dataset_attributes.get("att_ms", [])
                        if ms_instruments and len(ms_instruments) > 0:
                            # Use the first MS instrument found
                            instrument_tag = ms_instruments[0]
                    
                    runlist_model = RunListModel(
                        user_tag=old_runlist["user_tag"],
                        dataset_label=old_runlist["dataset_label"],
                        n_runs=old_runlist["n_runs"],
                        n_plates=old_runlist["n_plates"],
                        fractionated=old_runlist["fractionated"],
                        n_fractions=old_runlist.get("n_fractions", 0),
                        scrambled=old_runlist["scrambled"],
                        scrambled_across_plates=old_runlist["scrambled_across_plates"],
                        instrument_tag=instrument_tag,  # Can be None
                        aggregated_on=old_runlist.get("aggregated_on", None),
                        runs=runs
                    )
                    
                    DB.submissions.insert_runlist(
                        submission_tag=submission_tag,
                        runlist=runlist_model,
                        user_tag=self.fallback_user_tag
                    )
                    print(f"Runlist for submission {submission_tag} migrated successfully ({runlist_model.n_runs} runs).")
            else:
                print(f"Submission {submission_tag} already exists. Skipping.")
      


