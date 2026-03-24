
import json 
import os 
GENOTYPES_PATH = "/Users/hnolte/Documents/GitHub/mitocube-backend/resources/genotypes/genotypes.json"
from pydantic import BaseModel   
from typing import List, Optional, ForwardRef, Literal



AttributeTree = ForwardRef('AttributeTree')
    
class AttributeTree(BaseModel):
    """
    Represents a node in a hierarchical tree of attributes and traits used by the frontend
    when inserting genetic and condition applications.
    Each node describes a single attribute or trait and may contain an optional scalar
    value and zero or more child nodes to form a tree. This model is intended to be used
    with Pydantic (BaseModel) and serializes cleanly to/from JSON for API traffic.
    Fields
    - tag (str): A short identifier or name for the attribute or trait (e.g. "att_organ", "att_cellline").
        Should be non-empty.
    - type (Literal["attribute","trait"]): Distinguishes whether the node is an attribute or a trait.
        Within the tree, the type must be alternating along the children (i.e. an attribute node may only
        have trait children, and a trait node may only have attribute children).
    - value (float | int | str | None): Optional scalar value associated with this node. Use None
        when no value is applicable. Numeric values are typical for magnitudes; strings can be used
        for categorical values. Values can only be assigned to trait nodes.
    - children (Optional[List[AttributeTree]]): Optional list of child AttributeTree nodes. Use None
        or an empty list for leaf nodes.
    Validation and conventions
    - tag should be meaningful to the domain and unique among siblings when necessary.
    - type must be exactly "attribute" or "trait".
    - If children is provided, each child must itself be a valid AttributeTree instance.
    - Prefer numeric types for quantitative attributes; use strings for descriptive values.
    Example (Pydantic)
    >>> # Construct a small tree representing a genetic attribute with traits
    >>> root = AttributeTree(
    ...     tag="growth_rate",
    ...     type="attribute",
    ...     value=None,
    ...     children=[
    ...         AttributeTree(tag="baseline", type="trait", value=1.0),
    ...         AttributeTree(tag="temperature_modifier", type="trait", value=0.2)
    ...     ]
    ... )
    >>> # Serialize to dict / JSON for sending to frontend
    >>> root.dict()
    {
            "tag": "growth_rate",
            "type": "attribute",
            "value": 1.2,
            "children": [
                    {"tag": "baseline", "type": "trait", "value": 1.0, "children": None},
                    {"tag": "temperature_modifier", "type": "trait", "value": 0.2, "children": None}
            ]
    }
    """
   
    tag : str # Attribute or Trait String
    type :  Literal["attribute","trait"]
    value : Optional[float|int|str] = None
    children : Optional[List[AttributeTree]] = []
    

class InsertGeneticApplicationModel(BaseModel):
    text : str 
    description : Optional[str] = None
    publication : Optional[str] = None 
    technical_text : Optional[str] = None
    components : List[AttributeTree] # the list of components as attribute tree

with open(GENOTYPES_PATH, "r") as f:
    genotypes = json.load(f)






for g in genotypes:
     
    genotype_tag = g["label"]
    genotype_feature = [f["key"] for f in g["features"]] 
    print(genotype_tag, genotype_feature)
    cs = [] 
    for aa in g["attributes"]:
        print(aa)
        att_protein_tag = aa["att_protein_coding_sequence"]
        att_protein_tag = att_protein_tag[0]["key"]
        print(att_protein_tag)
        gene_engineering = aa["att_gene_engineering"]
        r = [{"type" : "attribute", "tag" : "att_gene_engineering", "children" : [{"type" : "trait", "tag" : f"att_gene_engineering:{gene_engineering[0]['tag']}", "children" : []}]}]
        
        for att_tag in ["att_gene_zygosity","att_gene_editing_method"]:
            att = aa[att_tag]
            if att is not None:
                att_dict = {"type" : "attribute", "tag" : att_tag, "children" : [{"type" : "trait", "tag" : f"{att_tag}:{att[0]['tag']}", "children" : []}]}
                r[0]["children"][0]["children"].append(att_dict)
        
        print(r)
        cs.extend(r)
        
        
    genotype_model = InsertGeneticApplicationModel(
            text = g["text"],
            description="Genotype imported from legacy database, original label: " + g["label"],
            technical_text= g["text"],
            components=cs
        )
    
    print(genotype_model)
    #  attribute_tags = aa.keys() 
    #  print(attribute_tags)
    #  for at in attribute_tags:
    #      if at != "att_protein_coding-sequence":
                
                
                
        
    #  print(aa)
    
    print(b)
    
    