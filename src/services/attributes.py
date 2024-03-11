from fastapi import HTTPException
from typing import List 


def get_suffix_from_attributes_and_attribute_tags(
        sample_attribute_tag : str,
        attribute_value_tag_left : str,
        attribute_value_tag_right : str,
        db_attributes,
        genotype_db,
        feature_db,
        comparison_suffix : str = "",
        within_attribute_tag : List[str] = [],
        within_attribute_value_tag : List[str] = []):
    """_summary_
    """
    attribute_values = db_attributes.getAttributeValues(tags=[attribute_value_tag_left,attribute_value_tag_right] + within_attribute_value_tag).set_index("tag", drop=False)
    attribute = db_attributes.getAttributes(tags=[sample_attribute_tag] + within_attribute_tag).set_index("tag")
    if sample_attribute_tag == "att_genotype":
        genotype_left = genotype_db.get(label = attribute_value_tag_left)
        genotype_right = genotype_db.get(label = attribute_value_tag_right)
        comparison_suffix = f"{genotype_left.text} vs {genotype_right.text}"
    elif attribute_value_tag_left not in attribute_values.index or attribute_value_tag_right not in attribute_values.index:
        comparison_suffix = f"{attribute_value_tag_left} vs {attribute_value_tag_right}"
    else:
        comparison_suffix = f"{attribute_values.loc[attribute_value_tag_left,'text']} vs {attribute_values.loc[attribute_value_tag_right,'text']}"
    
    
    if len(within_attribute_tag) > 0:
        if len(within_attribute_tag) != len(within_attribute_value_tag):
            raise HTTPException(status_code=422, detail="within_attribute_tag and within_attribute_tag must have the same length after splitting the string using the split_string (default ;).")
        within_attribute_text = ""
        within_attribute_value_text = ""
        for within_attr_tag, within_attr_value_tag in zip(within_attribute_tag,within_attribute_value_tag):
            if within_attr_tag not in attribute.index: raise HTTPException(status_code=404,detail="Within attribute tag not found")
            within_attribute_text = attribute.loc[within_attr_tag,"text"]
            if within_attr_tag == "att_genotype":
                genotype_within = genotype_db.get(label = within_attr_value_tag)
                within_attribute_value_text = genotype_within.text
            elif attribute.loc[within_attr_tag,"has_features_value"]:
                feature = feature_db.get(keys=[within_attr_value_tag.split(":")[1]],ignoreMissing=True)
                within_attribute_value_text = feature.loc[:,"genes"].values[0].split(" ")[0]
            elif attribute.loc[within_attr_tag,"has_numeric_input"]:
                within_attribute_value_text = within_attr_tag.split(":")[-1]
            elif within_attr_value_tag in attribute_values.index:
                within_attribute_value_text = attribute_values.loc[within_attr_value_tag,"text"]
                
            comparison_suffix += f"({within_attribute_text}: {within_attribute_value_text})"
    return comparison_suffix