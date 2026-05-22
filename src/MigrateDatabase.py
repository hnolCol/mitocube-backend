

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
    "att_organism" : "att_proteome",
    "att_gender" : "att_sex",
    "att_ms_name" : "att_ms",
    "att_ms" : "att_ms_type",
    'att_lc_system' : "att_lc_system_type",
    'att_lc_system_name' : "att_lc",
    'att_fraction' : 'att_centrifugation_fraction'
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

def handle_gender(tags : List[str]):
    "" 
    
    return build_tree(attribute_tag="att_sex", trait_tags=[t.replace("att_gender:", "att_sex:") for t in tags])

def handle_protein_treatment(tags : List[str]):
    "" 
    r = [] 
    protein_tags = [t.split(":")[1] for t in tags]
    proteome_tag = DB.proteomes.get_proteome_by_protein_tag(protein_tag = protein_tags[0])
    r = build_tree(attribute_tag = "att_protein_treatment", trait_tags=["att_protein_treatment:in_vivo"]) 
    r["children"][0]["children"].append(build_tree(attribute_tag="att_protein", trait_tags=[proteome_tag], value = "||".join(protein_tags)))
    return r 

def handle_mouse_id(tags : List[str]):
    values = [t.split(":")[1] for t in tags] 
    tree =  build_tree(attribute_tag="att_batch_type", trait_tags=["att_batch_type:mouseid"])
    tree["children"][0]["children"].extend([build_tree(attribute_tag="att_batch", trait_tags=["att_batch:id"], value=v) for v in values])
    return tree 

def handle_pulldown(tags : List[str]):
    "" 
    r = [] 
    protein_tags = [t.split(":")[1] for t in tags]
    print(f"Handling pulldown for protein tags: {protein_tags}")
    proteome_tag = DB.proteomes.get_proteome_by_protein_tag(protein_tag = protein_tags[0])
    r = build_tree(attribute_tag = "att_pulldown", trait_tags=["att_pulldown:endog"]) 
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
        update_attr = False
        if attribute_tag in attr_update:
            attribute_tag_old = attribute_tag
            attribute_tag = attr_update[attribute_tag]
            
            if attribute_tag == "att_proteome":
                trait_tags = [t.split(":")[-1] for t in trait_tags]
            else:
                [trait_tag.replace(attribute_tag_old, attribute_tag) if update_attr else trait_tag for trait_tag in trait_tags]
        
        return {"type" : "attribute", "tag" : attribute_tag, "children" : 
            [{"type" : "trait", "tag" : trait_tag, "children" : [], "value" : value[idx] if isinstance(value, list) else value } for idx, trait_tag in enumerate(trait_tags) if isinstance(trait_tag,str)]}



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

def handle_poi(tags : List[str]):
    
    r = [] 
    protein_tags = [t.split(":")[1] for t in tags]
    protein_tags = [p if p != "P40313" else "IGGCTR" for p in protein_tags]
    proteome_tag = DB.proteomes.get_proteome_by_protein_tag(protein_tag = protein_tags[0])
    r = build_tree(attribute_tag = "att_pulldown", trait_tags=["att_pulldown:endog"]) 
    r["children"][0]["children"].append(build_tree(attribute_tag="att_protein", trait_tags=[proteome_tag], value = "||".join(protein_tags)))
    return r

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
            elif attribute_tag == "att_protein_treatment":
                r[sampleIdx].append(handle_protein_treatment(sample_attribute_tags))
            elif attribute_tag == "att_gender":
                r[sampleIdx].append(handle_gender(sample_attribute_tags))
            elif attribute_tag == "att_pulldown":
                r[sampleIdx].append(handle_pulldown(sample_attribute_tags))
            elif attribute_tag == "att_cloneid":
                r[sampleIdx].append(handle_clone_id(sample_attribute_tags))
            elif attribute_tag == "att_centr_pellet":
                r[sampleIdx].append(handle_centrifugation_pellet(sample_attribute_tags))
            elif attribute_tag == "att_mouse_id":
                r[sampleIdx].append(handle_mouse_id(sample_attribute_tags))
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
   
   
def build_column_oven(dataset_attributes: dict):
    r = [] 
    
    oven_tags = dataset_attributes.get("att_column_oven_temp", None)
    if oven_tags is None:
        return dataset_attributes, None
    T = build_tree(attribute_tag="att_column_oven", trait_tags=["att_column_oven:son"])
    if oven_tags is not None:
        O = build_tree(attribute_tag="att_temperature", trait_tags=["att_temperature:celc"])
        dataset_attributes.pop("att_column_oven_temp")
    
    T["children"][0]["children"].append(O)
        
    return dataset_attributes, T

def build_ms_attributes(dataset_attributes: dict):

    
    ms_type = dataset_attributes.get("att_ms", None)
    if ms_type is None:
        return dataset_attributes, None
    T = build_tree(attribute_tag="att_ms_type", trait_tags=[t.replace("att_ms","att_ms_type") for t in ms_type], value=None)
    dataset_attributes.pop("att_ms")
    
    ms_instrument = dataset_attributes.get("att_ms_name", None)
    if ms_instrument is not None and len(ms_instrument) > 0:
        ms_instrument_tree = build_tree(attribute_tag="att_ms", trait_tags=[t.replace("att_ms_name","att_ms") for t in ms_instrument], value=None)
        
        rf_level_tags = dataset_attributes.get("att_rf_level", None)
        if rf_level_tags is not None and len(rf_level_tags) > 0:
             rf_level_tree = build_tree(attribute_tag="att_rf_level", trait_tags=["att_rf_level:perc"], value=rf_level_tags[0].split(":")[1].replace("%", ""))
             ms_instrument_tree["children"][0]["children"].append(rf_level_tree)
             dataset_attributes.pop("att_rf_level") 
       
        acquisition = dataset_attributes.get("att_acquisition", None)
        if acquisition is not None and len(acquisition) > 0:
            acquisition_tree = build_tree(attribute_tag="att_acquisition", trait_tags=acquisition, value=None)
            
            ms1_tags = dataset_attributes.get("att_ms1_resolution", None)
            if ms1_tags is not None and len(ms1_tags) > 0:
                ms1_tree = build_tree(attribute_tag="att_ms1_resolution", trait_tags=["att_ms1_resolution:200"], value=ms1_tags[0].split(":")[1].lower().replace("res", ""))
                acquisition_tree["children"][0]["children"].append(ms1_tree)
                dataset_attributes.pop("att_ms1_resolution")
            
            ms2_tags = dataset_attributes.get("att_ms2_resolution", None)
            if ms2_tags is not None and len(ms2_tags) > 0:
                ms2_tree = build_tree(attribute_tag="att_ms2_resolution", trait_tags=["att_ms2_resolution:200"], value=ms2_tags[0].split(":")[1].lower().replace("res", ""))
                acquisition_tree["children"][0]["children"].append(ms2_tree)
                dataset_attributes.pop("att_ms2_resolution")    
                
            dia_windows = dataset_attributes.get("att_diawindows", None)
            if dia_windows is not None and len(dia_windows) > 0:
                dia_tree = build_tree(attribute_tag="att_numspectra", trait_tags=["att_numspectra:diawindows"], value=dia_windows[0].split(":")[1])
                acquisition_tree["children"][0]["children"].append(dia_tree)
                dataset_attributes.pop("att_diawindows")
                
            collision_energy = dataset_attributes.get("att_collision_energy", None)
            if collision_energy is not None and len(collision_energy) > 0:
                ce_tree = build_tree(attribute_tag="att_collision_energy", trait_tags=["att_collision_energy:nce"], value=[ce.split(":")[1] for ce in collision_energy])
                acquisition_tree["children"][0]["children"].append(ce_tree)
                dataset_attributes.pop("att_collision_energy")
            ms_instrument_tree["children"][0]["children"].append(acquisition_tree)

    return dataset_attributes, T

def build_gradient_attributes(dataset_attributes: dict):
        

    gradient_length_tags = dataset_attributes.get("att_lc_gradient_length", None)
    if gradient_length_tags is None:
        return dataset_attributes, None
    T = build_tree(attribute_tag="att_lc_gradient", trait_tags=["att_lc_gradient:binary"])
    time = gradient_length_tags[0].split(":")[1] if gradient_length_tags is not None else None
    if time is not None and len(time) > 0:
        gradient_length_tree = build_tree(attribute_tag="att_duration", trait_tags=["att_duration:min"], value=time)
        T["children"][0]["children"].append(gradient_length_tree)
        dataset_attributes.pop("att_lc_gradient_length")
        
    flow_rate = dataset_attributes.get("att_lc_flow_rate", None)#"att_lc_flow_rate:185nlmin
    
    if flow_rate is not None and len(flow_rate) > 0:
        flow_rate_tree = build_tree(attribute_tag="att_flow_rate", trait_tags=["att_flow_rate:nlpermin"], value=flow_rate[0].split(":")[1].lower().replace("nlmin", ""))
        T["children"][0]["children"].append(flow_rate_tree)
        dataset_attributes.pop("att_lc_flow_rate")
    return dataset_attributes, T

def build_column_attributes(dataset_attributes: dict):
    r = [] 

    column_type = dataset_attributes.get("att_column_type",None)
    if column_type is None:
        return dataset_attributes, None
    T = build_tree(attribute_tag="att_column_type", trait_tags=column_type)
    children = []
    dataset_attributes.pop("att_column_type")
#att_length|att_outer_diameter|att_inner_diameter|att_particle_size|att_pore_size|att_column_stat_phase
    L = dataset_attributes.get("att_column_length", None)
    if L is not None and len(L) > 0:
        L_tree = build_tree(attribute_tag="att_length", trait_tags=["att_length:cm"], value=L[0].split(":")[1].replace("cm", ""))
        children.append(L_tree)
        dataset_attributes.pop("att_column_length")
    id = dataset_attributes.get("att_column_inner_diameter", None)
    if id is not None and len(id) > 0:
        id_tree = build_tree(attribute_tag="att_inner_diameter", trait_tags=["att_inner_diameter:µm"], value=id[0].split(":")[1].replace("µm", "").replace("um", ""))
        children.append(id_tree)
        dataset_attributes.pop("att_column_inner_diameter")
    
    od = dataset_attributes.get("att_column_outer_diameter", None)
    if od is not None and len(od) > 0:
        od_tree = build_tree(attribute_tag="att_outer_diameter", trait_tags=["att_outer_diameter:µm"], value=od[0].split(":")[1].replace("µm", "").replace("um", ""))
        children.append(od_tree)
        dataset_attributes.pop("att_column_outer_diameter")
    pc = dataset_attributes.get("att_column_particle_size", None)
    if pc is not None and len(pc) > 0:
        pc_tree = build_tree(attribute_tag="att_particle_size", trait_tags=["att_particle_size:µm"], value=pc[0].split(":")[1].replace("µm", "").replace("nm", "").replace("um", ""))
        children.append(pc_tree)
        dataset_attributes.pop("att_column_particle_size")
    stat_phase = dataset_attributes.get("att_column_stat_phase", None)
    if stat_phase is not None:
        stat_phase_tree = build_tree(attribute_tag="att_column_stat_phase", trait_tags=["att_column_stat_phase:c18"], value=None)
        children.append(stat_phase_tree)
        dataset_attributes.pop("att_column_stat_phase")
    T["children"][0]["children"] = children
    
    return dataset_attributes, T
    
def build_spray_attributes(dataset_attributes: dict):
    
    spray_tags = dataset_attributes.get("att_ms_ionsource", None)
    if spray_tags is None:
        return dataset_attributes, None
    T = build_tree(attribute_tag="att_ms_ionsource", trait_tags=spray_tags ) 
    
    voltage = dataset_attributes.get("att_spray_voltage", None) 
    if voltage is not None and len(voltage) > 0:
        voltage_tree = build_tree(attribute_tag="att_voltage", trait_tags=["att_voltage:kv"], value=voltage[0].split(":")[1].lower().replace("kv", ""))
        T["children"][0]["children"].append(voltage_tree)
        dataset_attributes.pop("att_spray_voltage")
    temp = dataset_attributes.get("att_cap_temp", None)
    if temp is not None and len(temp) > 0:
        temp_tree = build_tree(attribute_tag="att_temperature", trait_tags=["att_temperature:celc"], value=temp[0].split(":")[1].replace("c", ""))
        T["children"][0]["children"].append(temp_tree)
        dataset_attributes.pop("att_cap_temp")

    return dataset_attributes, T

def build_digestion_attributes(dataset_attributes: dict):
    #att_digestion_method		att_duration|att_termperature|att_volume|att_protease|att_digestion_vessel
    digestion_method = dataset_attributes.get("att_digestion_method",None)
    if digestion_method is None:
        return dataset_attributes, None 
    if len(digestion_method) == 0:
        digestion_method = ["att_digestion_method:sp3"]
    T = build_tree(attribute_tag="att_digestion_method", trait_tags=digestion_method)
    children = [] 
    
#     'att_digestion_temp' from dataset attributes not found in database, skipping.
# WARNING: attribute 'att_digestion_time' from dataset attributes not found in database, skipping.
# WARNING: attribute 'att_digestion_vessel' from dataset attributes not found in database, skipping.
# WARNING: attribute 'att_digestion_volume' from dataset attributes not found in database, skipping.

    temp = dataset_attributes.get("att_digestion_temp", None)
    if temp is not None and len(temp) > 0:
        temp_tree = build_tree(attribute_tag="att_temperature", trait_tags=["att_temperature:celc"], value=temp[0].split(":")[1].replace("c", ""))
        children.append(temp_tree)
        dataset_attributes.pop("att_digestion_temp")
    time = dataset_attributes.get("att_digestion_time", None)
    if time is not None and len(time) > 0:
        time_tree = build_tree(attribute_tag="att_duration", trait_tags=["att_duration:h"], value="16")
        children.append(time_tree)
        dataset_attributes.pop("att_digestion_time")
    vessel = dataset_attributes.get("att_digestion_vessel", None)
    if vessel is not None and len(vessel) > 0:
        vessel_tree = build_tree(attribute_tag="att_digestion_vessel", trait_tags=vessel)
        children.append(vessel_tree)
        dataset_attributes.pop("att_digestion_vessel")
    volume = dataset_attributes.get("att_digestion_volume", None)
    if volume is not None and len(volume) > 0:
        volume_tree = build_tree(attribute_tag="att_volume", trait_tags=["att_volume:ul"], value=volume[0].split(":")[1].lower().replace("µl", "").replace("ul", ""))
        children.append(volume_tree)
        dataset_attributes.pop("att_digestion_volume")
    protease = dataset_attributes.get("att_protease", None)
    if protease is not None and len(protease) > 0:    
        protease_tree = build_tree(attribute_tag="att_protease", trait_tags=protease)
        children.append(protease_tree)
        dataset_attributes.pop("att_protease")
        
    mass = dataset_attributes.get("att_protein_input", None)
    if mass is not None and len(mass) > 0:
        mass_tree = build_tree(attribute_tag="att_mass", trait_tags=["att_mass:µg"], value=mass[0].split(":")[1].lower().replace("µg", "").replace("ug", ""))
        children.append(mass_tree)
        dataset_attributes.pop("att_protein_input")
        
    T["children"][0]["children"] = children
    return dataset_attributes, T

def build_faims(dataset_attributes : dict):
    
    interface_tags = dataset_attributes.get("att_ms_interface", None)
    if interface_tags is None:
        return dataset_attributes, None
    T = build_tree(attribute_tag="att_ms_interface", trait_tags=interface_tags)
    is_faims = any(t.endswith("faims") for t in interface_tags)
    dataset_attributes.pop("att_ms_interface")
    if not is_faims:
        return dataset_attributes, T
    cv = dataset_attributes.get("att_faims_cv", None)
    if cv is not None and len(cv) > 0:
        cv_tree = build_tree(attribute_tag="att_faims_cv", trait_tags=["att_faims_cv:v"], value=cv[0].split(":")[1].replace("v", ""))
        T["children"][0]["children"].append(cv_tree)
        dataset_attributes.pop("att_faims_cv")
    gasflow = dataset_attributes.get("att_faims_gasflow", None)
    if gasflow is not None and len(gasflow) > 0:
        gasflow_tree = build_tree(attribute_tag="att_faims_gasflow", trait_tags=["att_faims_gasflow:lmin"], value=gasflow[0].split(":")[1].lower().replace("mlmin", "").replace("ml/min", ""))
        T["children"][0]["children"].append(gasflow_tree)
        dataset_attributes.pop("att_faims_gasflow")
    inner_temp = dataset_attributes.get("att_faims_inner_temp", None)
    if inner_temp is not None and len(inner_temp) > 0:
        inner_temp_tree = build_tree(attribute_tag="att_faims_inner_temp", trait_tags=["att_faims_inner_temp:c"], value=inner_temp[0].split(":")[1].lower().replace("c", ""))
        T["children"][0]["children"].append(inner_temp_tree)
        dataset_attributes.pop("att_faims_inner_temp")
    outer_temp = dataset_attributes.get("att_faims_outer_temp", None)
    if outer_temp is not None and len(outer_temp) > 0:
        outer_temp_tree = build_tree(attribute_tag="att_faims_outer_temp", trait_tags=["att_faims_outer_temp:c"], value=outer_temp[0].split(":")[1].lower().replace("c", ""))
        T["children"][0]["children"].append(outer_temp_tree)
        dataset_attributes.pop("att_faims_outer_temp")
    return dataset_attributes, T

        
        
def build_dataset_condition_applications(dataset_attributes : dict): 
    "" 
    r = []
    
    for func in [build_ms_attributes, build_gradient_attributes, build_column_oven, build_digestion_attributes, build_column_attributes, build_spray_attributes, build_faims]:
        dataset_attributes, T = func(dataset_attributes)
        if T is not None:
            r.append(T)
    
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
            if attribute_tag in attr_update or DB.attributes.exists(tag=attribute_tag):
                if not attribute_tag in attr_update:
                    checked_trait_tags = [t for t in trait_tags if DB.attributes.exists(trait=t)]
                else:
                    checked_trait_tags = trait_tags
                if len(checked_trait_tags) < len(trait_tags):
                    print(f"WARNING: for attribute '{attribute_tag}', some trait tags were not found in the database and will be skipped. Provided trait tags: {trait_tags}, found trait tags: {checked_trait_tags}")
                if len(checked_trait_tags) > 0:
                    r.append(build_tree(attribute_tag, checked_trait_tags))
            else:
                print(f"WARNING: attribute '{attribute_tag}' from dataset attributes not found in database, skipping.")
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
        
    def get_user(self, user_string : List[str]) -> str:
        for user_str in user_string:
            if user_str is not None and DB.users.exists(tag=user_str):
                return user_str
        return self.fallback_user_tag
    def run(self):

        for i, submission_tag in enumerate(self.dirList):
            print("Starting migration for submission:", submission_tag, (i+1), "out of", len(self.dirList))
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
            timeline_to_insert = [{"created_at" : t["created_on"] * 1000, "user_tag": self.get_user([t.get("user_tag") , t.get("user_label")]), "state": t["state"]} for t in timeline.get("entries", [])] #timeline was previous in python timestamp, but in js frontend we use milliseconds, so we need to convert it by multiplying with 1000.
            print(timeline_to_insert)
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
                        collaborators = submission_insert_model.collaborators,
                        created_at = jsonFile["created_on"] * 1000 if "created_on" in jsonFile else None)
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
                    time.sleep(0.3) # to avoid overwhelming the database with too many requests in a short time, especially when migrating multiple submissions. Adjust the sleep duration as needed based on the size of the data and the performance of the database.
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
                    try:
                        runlist_model = RunListModel(
                            user_tag=old_runlist["user_label"] if "user_label" in old_runlist else self.fallback_user_tag,
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
                    except Exception as e:
                        print(f"Error migrating runlist for submission {submission_tag}: {e}")
            else:
                print(f"Submission {submission_tag} already exists. Skipping.")
      




