
from typing import List, Dict 
from config.models.conditions_applications import ConditionApplicationItemModel, ConditionApplicationTreeModel


def build_condition_application_tree(paths: List[List[ConditionApplicationItemModel]]) -> ConditionApplicationTreeModel:
    def insert_node(children: List[Dict], path: List[ConditionApplicationItemModel]):
        if not path:
            return

        node = path[0]
        trait_tag = node.trait_tag

        # Check if a node with this trait_tag already exists
        existing = next((child for child in children if child["trait_tag"] == trait_tag), None)

        if not existing:
            existing = {
                "tag" : node.tag,
                "trait_tag": trait_tag, #should be in 1 object which has atribute as children the trait # create genottype and check trait 
                "attribute_tag": node.attribute_tag,
                "value": node.value,
                "children": []
            }
            children.append(existing)

        # Recurse for the rest of the path
        insert_node(existing["children"], path[1:])

    root: List[Dict] = []
    for path in paths:
        insert_node(root, path)
    return [ConditionApplicationTreeModel(**node) for node in root]