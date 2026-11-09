from typing import Callable, Dict, List, Tuple

from config.models.attributes import AttributeTree


def resolve_trait_paths(
    attribute_tag: str,
    trait_tags: List[str],
    parent_tags: List[str],
    implied_edges: Dict[str, List[Tuple[str, str]]],
) -> Dict[str, List[Dict[str, str]]]:
    """Resolves the full hierarchy path for traits that deterministically imply
    their parent traits.

    Parameters
    ----------
    attribute_tag : str
        The tag of the attribute the traits belong to.
    trait_tags : List[str]
        The trait tags of the attribute.
    parent_tags : List[str]
        The ordered ancestor chain of the attribute (root first).
    implied_edges : Dict[str, List[Tuple[str, str]]]
        Maps a trait tag to its implied parent traits as
        (parent_attribute_tag, parent_trait_tag) tuples.

    Returns
    -------
    Dict[str, List[Dict[str, str]]]
        Maps each trait tag with a fully resolved chain to its path
        (root first). Traits without a unique implied parent trait at every
        level are omitted.
    """
    trait_paths = {}
    if not parent_tags:
        return trait_paths
    for trait_tag in trait_tags:
        path = [{"attribute_tag": attribute_tag, "trait_tag": trait_tag}]
        current_trait = trait_tag
        resolved = True
        for parent_attribute in reversed(parent_tags):
            candidates = [
                parent_trait
                for parent_attribute_tag, parent_trait in implied_edges.get(current_trait, [])
                if parent_attribute_tag == parent_attribute
            ]
            if len(candidates) != 1:
                resolved = False
                break
            path.append({"attribute_tag": parent_attribute, "trait_tag": candidates[0]})
            current_trait = candidates[0]
        if resolved:
            trait_paths[trait_tag] = list(reversed(path))
    return trait_paths


def complete_or_validate_attribute_trees(
    get_parents: Callable[[str], List[str]],
    get_implied_parent_traits: Callable[[List[str]], Dict[str, List[Tuple[str, str]]]],
    attribute_trees: List[AttributeTree],
) -> List[AttributeTree]:
    """Validates that child attribute traits are always submitted together with
    their parent attribute and trait.

    A root-level attribute that has parents is auto-completed: when every trait
    child of the node unambiguously implies its parent trait, the node is
    attached under the parent attribute (an existing parent root when present,
    otherwise a newly wrapped one). When no unambiguous implication exists, a
    ValueError is raised. Nested child attributes that are not placed below one
    of their parents are rejected.

    Parameters
    ----------
    get_parents : Callable[[str], List[str]]
        Returns the parent attribute tags for an attribute tag.
    get_implied_parent_traits : Callable[[List[str]], Dict[str, List[Tuple[str, str]]]]
        Returns the implied (parent_attribute_tag, parent_trait_tag) pairs for
        trait tags.
    attribute_trees : List[AttributeTree]
        The attribute trees submitted by the client.

    Returns
    -------
    List[AttributeTree]
        The validated and auto-completed attribute trees.

    Raises
    ------
    ValueError
        When a child attribute trait is present without its parent attribute
        and trait and no unambiguous implication exists.
    """
    roots: List[AttributeTree] = []
    pending: List[AttributeTree] = []
    for tree in attribute_trees:
        if get_parents(tree.tag):
            pending.append(tree)
        else:
            roots.append(tree)

    if pending:
        trait_children = [
            child for tree in pending for child in (tree.children or []) if child.type == "trait"
        ]
        implied = get_implied_parent_traits([child.tag for child in trait_children])
        for tree in pending:
            implied_map = _resolve_node_implications(tree, implied)
            parent_attribute_tag = implied_map["parent_attribute_tag"]
            target = next((root for root in roots if root.tag == parent_attribute_tag), None)
            if target is None:
                target = AttributeTree(tag=parent_attribute_tag, type="attribute", children=[])
                roots.append(target)
            _attach_node(target, tree, implied_map)

    for root in roots:
        _validate_nested(get_parents, root, [])
    return roots


def _resolve_node_implications(
    tree: AttributeTree,
    implied: Dict[str, List[Tuple[str, str]]],
) -> Dict:
    """Resolves the implied parent trait for every trait child of a node.

    Raises a ValueError when a trait child does not unambiguously imply a
    parent trait or when the implied parent traits belong to different parent
    attributes.
    """
    trait_children = [child for child in (tree.children or []) if child.type == "trait"]
    if not trait_children:
        raise ValueError(
            f"The attribute '{tree.tag}' is a child attribute and requires its "
            "parent attribute and trait to be selected as well."
        )
    implied_map = {}
    for trait_child in trait_children:
        edges = implied.get(trait_child.tag, [])
        if len(edges) != 1:
            raise ValueError(
                f"The trait '{trait_child.tag}' of the child attribute '{tree.tag}' "
                "is selected without its parent attribute and trait, and the parent "
                "trait cannot be unambiguously resolved. Select the parent trait first."
            )
        implied_map[trait_child.tag] = edges[0]
    parent_attributes = {parent_attribute_tag for parent_attribute_tag, _ in implied_map.values()}
    if len(parent_attributes) != 1:
        raise ValueError(
            f"The traits of the child attribute '{tree.tag}' imply different parent "
            "attributes. Select the parent attribute and trait first."
        )
    return {
        "parent_attribute_tag": parent_attributes.pop(),
        "trait_map": implied_map,
    }


def _attach_node(target: AttributeTree, tree: AttributeTree, implied_map: Dict) -> None:
    """Attaches a child attribute node below the parent trait nodes of an
    existing or newly created parent attribute root."""
    for trait_child in [child for child in (tree.children or []) if child.type == "trait"]:
        parent_trait_tag = implied_map["trait_map"][trait_child.tag][1]
        trait_node = next(
            (child for child in (target.children or []) if child.type == "trait" and child.tag == parent_trait_tag),
            None,
        )
        if trait_node is None:
            trait_node = AttributeTree(tag=parent_trait_tag, type="trait", children=[])
            target.children.append(trait_node)
        trait_node.children.append(
            AttributeTree(
                tag=tree.tag,
                type="attribute",
                value=tree.value,
                children=[trait_child],
            )
        )


def _validate_nested(get_parents: Callable[[str], List[str]], node: AttributeTree, ancestors: List[str]) -> None:
    """Rejects nested child attributes that are not placed below one of their parents."""
    if node.type == "attribute":
        parents = get_parents(node.tag)
        if parents and ancestors and not any(ancestor in parents for ancestor in ancestors):
            raise ValueError(
                f"The child attribute '{node.tag}' must be selected below one of its "
                f"parent attributes {parents}."
            )
        ancestors = ancestors + [node.tag]
    for child in node.children or []:
        _validate_nested(get_parents, child, ancestors)
