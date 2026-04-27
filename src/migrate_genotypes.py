import json
import os
from pydantic import BaseModel
from typing import List, Optional, ForwardRef, Literal

from lib.database.Database import Database
import argparse
DB = Database.DB()


ONLY_LABEL = None   # set to a label string to migrate only one, or None to migrate all


# Inline models 

AttributeTree = ForwardRef('AttributeTree')

class AttributeTree(BaseModel):
    tag: str
    type: Literal["attribute", "trait"]
    value: Optional[float | int | str] = None
    children: Optional[List[AttributeTree]] = []

AttributeTree.model_rebuild()

class InsertGeneticApplicationModel(BaseModel):
    text: str
    description: Optional[str] = None
    publication: Optional[str] = None
    technical_text: Optional[str] = None
    components: List[AttributeTree]


# Tag mappings



ZYGOSITY_MAP = {
    "(+/+)": "wt",
    "(-/-)": "homozygot",
    "(+/-)": "hetero",
    "(-/+)": "hetero",
}



UNTARGETED_MUTATIONS = {"frameshift", "premstop"}


# Tree builders 

def build_position_attr(pos_data):
    if not pos_data:
        return None
    position_tag = pos_data.get("attribute_value", {}).get("tag")
    if not position_tag:
        return None
    aa_positions = pos_data.get("aa_position", [])
    position_children = []
    if position_tag in ("region", "aa") and aa_positions:
        position_children.append(AttributeTree(
            tag="att_aa_position_start", type="attribute",
            children=[AttributeTree(tag="att_aa_position_start:aa", type="trait", value=str(aa_positions[0]), children=[])]
        ))
        if len(aa_positions) > 1:
            position_children.append(AttributeTree(
                tag="att_aa_position_end", type="attribute",
                children=[AttributeTree(tag="att_aa_position_end:aa", type="trait", value=str(aa_positions[1]), children=[])]
            ))
    
    position_value = f"{aa_positions[0]}-{aa_positions[1]}" if len(aa_positions) > 1 else str(aa_positions[0]) if aa_positions else None

    return AttributeTree(
        tag="att_protein_position", type="attribute",
        children=[AttributeTree(tag=f"att_protein_position:{position_tag}", type="trait", value=position_value, children=position_children)]
    )


def build_mutation_attr(mut_tag, pos_data):
    position_attr = build_position_attr(pos_data) if pos_data else None
    trait_children = [position_attr] if position_attr else []
    if mut_tag in UNTARGETED_MUTATIONS:
        attr_tag  = "att_protein_untargeted_mutation"
        trait_tag = f"att_protein_untargeted_mutation:{mut_tag}"
    else:
        attr_tag  = "att_protein_mutation"
        trait_tag = f"att_protein_mutation:{mut_tag}"
    return AttributeTree(
        tag=attr_tag, type="attribute",
        children=[AttributeTree(tag=trait_tag, type="trait", children=trait_children)]
    )


def build_component(attr_block):
    protein_key  = attr_block["att_protein_coding_sequence"][0]["key"]
    eng_tag      = attr_block["att_gene_engineering"][0]["tag"]
    method_tag   = attr_block["att_gene_editing_method"][0]["tag"] if "att_gene_editing_method" in attr_block else "att_gene_editing_method:crispr"
    raw_zyg      = attr_block["att_gene_zygosity"][0]["tag"]
    zygosity_tag = ZYGOSITY_MAP.get(raw_zyg, raw_zyg)
    mutations    = attr_block.get("att_protein_mutation", [])
    positions    = attr_block.get("att_protein_position", {})

    zygosity_attr = AttributeTree(
        tag="att_gene_zygosity", type="attribute",
        children=[AttributeTree(tag=f"att_gene_zygosity:{zygosity_tag}", type="trait", children=[])]
    )
    mutation_attrs = [build_mutation_attr(mut["tag"], positions.get(mut["tag"])) for mut in mutations]
    method_attr = AttributeTree(
        tag="att_gene_editing_method", type="attribute",
        children=[AttributeTree(tag=f"att_gene_editing_method:{method_tag}", type="trait", children=mutation_attrs)]
    )
    proteome_tag = DB.proteomes.get_proteome_by_protein_tag(protein_tag=protein_key)  # check if protein exists, will raise exception if not
    print(proteome_tag)
    protein_attr = AttributeTree(
        tag="att_protein", type="attribute",
        children=[AttributeTree(tag=proteome_tag, type="trait", value=protein_key, children=[])]
    )
    
    print(protein_attr)
    return AttributeTree(
        tag="att_gene_engineering", type="attribute",
        children=[AttributeTree(
            tag=f"att_gene_engineering:{eng_tag}", type="trait",
            children=[zygosity_attr, method_attr, protein_attr]
        )]
    )


#  Migration 
from services.encryption import create_hierarchical_hash
import argparse

class MigrateGenotypes:

    def __init__(self, path_to_genotypes :str, fallback_user_tag : str):
        self.fallback_user_tag = fallback_user_tag
        
        if not os.path.exists(path_to_genotypes):
            raise ValueError(f"Path to genotypes file does not exist: {path_to_genotypes}") 
        
        self.path_to_genotypes = path_to_genotypes 
            
    def migrate(self):
        
        with open(self.path_to_genotypes) as f:
            genotypes = json.load(f)

        genotype_list = [g for g in genotypes if ONLY_LABEL is None or g["label"] in ONLY_LABEL]
        
        label_to_tag = {}

        for g in genotype_list:
            label = g["label"]
            components = []
            for block in g["attributes"]:
                mutations = block.get("att_protein_mutation", [])
                try:
                    if len(mutations) <= 1:
                        components.append(build_component(block))
                    else:
                        for mut in mutations:
                            single_mut_block = {**block, "att_protein_mutation": [mut]}
                            components.append(build_component(single_mut_block))
                except Exception as e: 
                    print(f"Error building component for genotype {label}: {e}")
                    continue
            if len(components) == 0:
                print(f"No valid components found for genotype {label}, skipping.")
                continue
            model = InsertGeneticApplicationModel(
                text=g["text"],
                technical_text=g.get("text"),
                description= "Genotype imported from old database, original label: " + label,
                components=components
            )
            genotype_tag = create_hierarchical_hash([c.model_dump() for c in model.components])
            
            try:
                ok = DB.genotypes.insert(model, user_tag=self.fallback_user_tag) #old DB had no user assignment for genotypes, so we assign to fallback user.
                if ok:
                    print(f"Genotype {label} inserted successfully.")
                else:
                    print(f"Genotype {label} already exists. Skipping.")
                label_to_tag[label] = genotype_tag
                
            except Exception as e:
                print(f"Error inserting genotype {label}: {e}")
                continue

        with open("label_to_tag.json", "w") as f:
            json.dump(label_to_tag, f, indent=2)
        print(f"Label to tag mapping saved to label_to_tag.json")
        
        return "label_to_tag.json"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Migrate genotypes from JSON file')

    parser.add_argument('--user-tag', default='kxWH7py3', help='User tag for database insertion')
    parser.add_argument('--genotypes-path', default='/home/cloud/resources/genotypes/genotypes.json', help='Path to genotypes JSON file')
    args = parser.parse_args()
    GENOTYPES_PATH = args.genotypes_path
    USER_TAG = args.user_tag
    MigrateGenotypes(path_to_genotypes=GENOTYPES_PATH, fallback_user_tag=USER_TAG).migrate()
