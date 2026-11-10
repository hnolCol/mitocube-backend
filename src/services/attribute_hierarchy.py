from typing import Callable, List

from config.models.attributes import AttributeTree


def validate_attribute_trees(
    get_parents: Callable[[str], List[str]],
    attribute_trees: List[AttributeTree],
) -> List[AttributeTree]:
    """Validates the structure of submitted attribute trees.

    A nested child attribute must be placed below one of its parent
    attributes; trees violating this are rejected with a ValueError.
    Root-level child attributes are passed through unchanged — the parent
    attribute and trait are selected by the user during selection, assisted
    by the search ordering that prefers parentless attributes on equal
    priority and by the parent_tags hierarchy metadata.

    Parameters
    ----------
    get_parents : Callable[[str], List[str]]
        Returns the parent attribute tags for an attribute tag.
    attribute_trees : List[AttributeTree]
        The attribute trees submitted by the client.

    Returns
    -------
    List[AttributeTree]
        The validated attribute trees.

    Raises
    ------
    ValueError
        When a nested child attribute is placed below a non-parent attribute.
    """
    for root in attribute_trees:
        _validate_nested(get_parents, root, [])
    return attribute_trees


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
