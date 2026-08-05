from email.policy import strict
from typing import List, Dict, Literal
 
from fastapi import APIRouter, Depends, HTTPException
from collections import OrderedDict
 
from lib.database.Database import Database
 
from lib.data.statistic.ANOVA import OneWayANOVA
from lib.data.clustering.HierarchicalClustering import HierarchicalClustering
 
from config.exceptions.HTTPExceptions import no_data_found_http_exception, filter_tag_does_not_exist_exception
from config.models.user import UserModel
from config.models.compare import CompareModel
from config.exceptions.HTTPExceptions import submission_tag_not_found
from services.users import get_user_from_token
import pandas as pd 
from scipy.stats import ttest_ind, false_discovery_control
import numpy as np
from services.statistics.clustering import cluster_to_dataframe

DB = Database.DB()

router = APIRouter(
    prefix="/api/submissions/analysis",
    tags=["Submission","Analysis","Heatmap"],
)
# --- 1. fix handle_pairwise index -------------------------------------------------
def handle_pairwise(submission_tag: str, annotation_tag: str, sample_tags: list, sample_tags_left: list, sample_tags_right: list, suffix: str, equal_variance: bool, fdr: float):
    dt = DB.get_datatable(tag=submission_tag, annotation_tag=annotation_tag, sample_tags=sample_tags, use_sample_tags=True)
    if dt.empty:
        raise HTTPException(status_code=404, detail="No data found for the given submission and annotation tag. Ensure that the annotation tag is correct and that there is data available. Double check the ca_tags please.")
    if sample_tags_left.size < 2 or sample_tags_right.size < 2:
        raise HTTPException(status_code=400, detail="At least two samples are required in each group for t-test.")
 
    X = dt.loc[:, sample_tags_left]
    Y = dt.loc[:, sample_tags_right]
 
    T, p = ttest_ind(X, Y, nan_policy="omit", axis=1, equal_var=equal_variance)
    p_value_name = "p-value"
 
    stats = pd.DataFrame(
        {f"t-value {suffix}": T,
         p_value_name: p,
         "tag": dt.index,
         f"log2FC {suffix}": X.mean(axis=1) - Y.mean(axis=1)},
        index=dt.index,  # <-- explicit protein_group index, no longer relying on implicit alignment
        columns=[f"t-value {suffix}", p_value_name, "tag", f"log2FC {suffix}"]
    ).dropna(subset=[p_value_name])
    stats.loc[:, f"-log10 p-value {suffix}"] = -np.log10(stats.loc[:, p_value_name])
    stats.loc[:, f"fdr {suffix}"] = false_discovery_control(stats[p_value_name].values)
    stats.loc[:, f"Significant {suffix}"] = stats.loc[:, f"fdr {suffix}"] <= fdr
    return stats
 
 
# --- 2. expose the trend pivot so we can pull log2FC out of it, not just the mask --
def _build_trend_pivot(rows: List[dict], n_groups: int) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame()
    pivot = df.pivot(index="tag", columns="idx", values="avg_value")
    pivot = pivot.dropna(axis=0, how="any")
    if pivot.shape[1] != n_groups:
        return pd.DataFrame()
    return pivot[sorted(pivot.columns)]
 
 
def compute_trend_subset(pivot: pd.DataFrame, increase: bool = True, strict: bool = True) -> pd.Index:
    if pivot.empty:
        return pd.Index([], name="tag")
    diffs = pivot.diff(axis=1).iloc[:, 1:]
    mask = (diffs > 0).all(axis=1) if (increase and strict) else \
           (diffs >= 0).all(axis=1) if increase else \
           (diffs < 0).all(axis=1) if strict else \
           (diffs <= 0).all(axis=1)
    return pivot.index[mask]
 
def _annotation_analysis(annotation_tag: str, submission_tag : str) -> Dict:
    

    protein_tags = DB.annotations.get_protein_tags(tag = annotation_tag, submission_tag = submission_tag)
    return {"ids" : pd.Index(protein_tags)}
    
 
def _trend_analysis(submission_tag: str, attribute_tag: str, ca_tags: List[List[str]], increase: bool = True, strict: bool = True, protein_group_tags: List[str] = None) -> Dict:
    condition_applications = DB.samples.get_sample_condition_application_map_for_submission(submission_tag=submission_tag)
    sample_groups, group_labels = [], []
    for ca_tag in ca_tags:
        ca_tag_i = ca_tag[0] if len(ca_tag) == 1 else ";".join(ca_tag)
        sample_tags = condition_applications[condition_applications[attribute_tag] == ca_tag_i].index
        sample_groups.append((ca_tag, ca_tag_i, sample_tags.values.tolist()))
        group_labels.append(ca_tag_i)
 
    df = DB.protein_groups.find_trend_values(sample_group_tags=sample_groups, tags=protein_group_tags)
    pivot = _build_trend_pivot(df, n_groups=len(sample_groups))
    computed_ids = compute_trend_subset(pivot, increase=increase, strict=strict)
    if not pivot.empty:
        # log2FC of every group vs. the first (baseline) group — data is already log2 LFQ
        baseline = pivot.iloc[:, 0]
        log2fc = pivot.iloc[:, 1:].sub(baseline, axis=0)
        log2fc.columns = [f"{DB.condition_applications.get_text(group_labels[i])} vs {DB.condition_applications.get_text(group_labels[0])}" for i in range(1, len(group_labels))]
    else:
        log2fc = pd.DataFrame()
 
    return {"ids": computed_ids, "log2fc": log2fc}
 
 
# --- 3. pairwise: return both filtered ids and the full per-protein log2FC --------
def _pairwise_analysis(submission_tag: str,
                        ca_tag_left: str,
                        ca_tag_right: str,
                        criteria: Literal["significant", "not_significant", "significant_increase", "significant_decrease"],
                        within_attribute_tags: str,
                        within_ca_tags: str,
                        annotation_tag: str = None,
                        protein_group_tags: List[str] = None) -> Dict:
    sample_tags_left, sample_tags_right, sample_tags, suffix, ca_left_text, ca_right_text, attribute_tag = DB.samples.handle_comparison(
        submission_tag=submission_tag,
        ca_tag_left=ca_tag_left,
        ca_tag_right=ca_tag_right,
        within_attribute_tags=within_attribute_tags,
        within_ca_tags=within_ca_tags,
        annotation_tag=annotation_tag)
 
    stats = handle_pairwise(
        submission_tag=submission_tag,
        annotation_tag=annotation_tag,
        sample_tags=sample_tags,
        sample_tags_left=sample_tags_left,
        sample_tags_right=sample_tags_right,
        suffix="",
        equal_variance=True,
        fdr=0.05
    )
 
    if criteria == "significant":
        ids = stats.loc[stats.loc[:, "Significant "] == True].index
    elif criteria == "not_significant":
        ids = stats.loc[stats.loc[:, "Significant "] == False].index
    elif criteria == "significant_increase":
        ids = stats.loc[(stats.loc[:, "Significant "] == True) & (stats.loc[:, "log2FC "] > 0)].index
    elif criteria == "significant_decrease":
        ids = stats.loc[(stats.loc[:, "Significant "] == True) & (stats.loc[:, "log2FC "] < 0)].index
    else:
        raise HTTPException(status_code=400, detail=f"Unknown criteria: {criteria}")
 
    log2fc = stats[["log2FC "]].rename(columns={"log2FC ": f"{ca_left_text} vs {ca_right_text}"})
 
    return {"ids": ids, "log2fc": log2fc, "ca_left_text": ca_left_text, "ca_right_text": ca_right_text}
 
 
# --- 4. tree walk now also collects a flat leaf_data registry ---------------------
# NOTE: leaves and and/or/not nodes are now tagged with an "id" so that
# merge_comparison_results can report a per-step protein count for every
# node in the tree, not just the leaves.
def _process_comparison_children(
    comparisons: CompareModel,
    protein_group_tags: List[str] = None,
    operator: Literal["and", "or", "not"] = "and",
    protein_tag_results: Dict = None,
    leaf_data: Dict = None,
):
    if protein_tag_results is None:
        protein_tag_results = {"operator": operator, "children": [], "id": comparisons.id}
    if leaf_data is None:
        leaf_data = {}
 
    if not comparisons.children or len(comparisons.children) == 0:
        return protein_tag_results, leaf_data
 
    for child_comp in comparisons.children:
        leaf_id = child_comp.id or f"leaf_{len(leaf_data)}"
 
        if child_comp.type == "trend":
            if not child_comp.submission_tag or not child_comp.props.attribute_tag or not child_comp.props.ca_tags:
                raise HTTPException(status_code=400, detail="Missing required fields in comparison")
            if len(child_comp.props.ca_tags) < 2:
                raise HTTPException(status_code=400, detail="At least two condition application tags are required for comparison")
            direction = child_comp.criteria
            trend_result = _trend_analysis(
                submission_tag=child_comp.submission_tag,
                attribute_tag=child_comp.props.attribute_tag,
                ca_tags=child_comp.props.ca_tags,
                increase=direction == "increasing"
            )
            description = f"trend ({direction}) over {child_comp.props.attribute_tag}: " + \
                          " > ".join(";".join(ca) for ca in child_comp.props.ca_tags)
            protein_tag_results["children"].append({
                "id": leaf_id,
                "type": "trend",
                "ids": trend_result["ids"],
            })
            leaf_data[leaf_id] = {"type": "trend", "log2fc": trend_result["log2fc"], "description": description}
 
        elif child_comp.type == "annotation":
            
            annotation_results = _annotation_analysis(
                annotation_tag=child_comp.props["annotation_tag"],
                submission_tag=child_comp.submission_tag
            )
            protein_tag_results["children"].append({
                "id": leaf_id,
                "type": "annotation",
                "ids": annotation_results["ids"],
            })
            leaf_data[leaf_id] = {"type": "annotation", "description": f"Proteins in annotation: {DB.annotations.get_text(child_comp.props['annotation_tag'])}", "log2fc": pd.DataFrame()}
 
        elif child_comp.type == "pairwise":
            pairwise_result = _pairwise_analysis(
                submission_tag=child_comp.submission_tag,
                ca_tag_left=child_comp.props["ca_tag_left"],
                ca_tag_right=child_comp.props["ca_tag_right"],
                criteria=child_comp.criteria,
                within_attribute_tags=child_comp.props.get("within_attribute_tags", None),
                within_ca_tags=child_comp.props.get("within_ca_tags", None),
                annotation_tag=child_comp.props.get("annotation_tag", None),
            )
            description = f"{pairwise_result['ca_left_text']} vs {pairwise_result['ca_right_text']} ({child_comp.criteria})"
            protein_tag_results["children"].append({
                "id": leaf_id,
                "type": "pairwise",
                "ids": pairwise_result["ids"],
            })
            leaf_data[leaf_id] = {"type": "pairwise", "log2fc": pairwise_result["log2fc"], "description": description}
 
        elif child_comp.type in ["and", "or", "not"]:
            nested_node = {"operator": child_comp.type, "children": [], "id": leaf_id}
            protein_tag_results["children"].append(nested_node)
            _process_comparison_children(
                child_comp,
                protein_group_tags=protein_group_tags,
                operator=child_comp.type,
                protein_tag_results=nested_node,
                leaf_data=leaf_data,
            )
 
    return protein_tag_results, leaf_data
 
# --- 5. merge now also builds a nested count tree, mirroring the comparison tree --
# Each leaf node in the returned tree looks like:
#   {"id": ..., "type": "trend"|"pairwise", "count": N, "description": "...", "children": []}
# Each and/or/not node looks like:
#   {"id": ..., "operator": "and"|"or"|"not", "count": N, "children": [...]}
def merge_comparison_results(node, universe: pd.Index = None, leaf_data: Dict = None):
    # leaf node: {"id", "type", "ids"}
    if isinstance(node, dict) and "ids" in node:
        ids = node["ids"]
        description = None
        if leaf_data is not None and node["id"] in leaf_data:
            description = leaf_data[node["id"]].get("description")
        tree_node = {
            "id": node["id"],
            "type": node["type"],
            "count": len(ids),
            "description": description,
            "children": [],
        }
        return ids, tree_node
 
    operator = node["operator"]
    children = node["children"]
    if not children:
        raise ValueError(f"'{operator}' node has no children to merge")
 
    resolved_children = []
    child_trees = []
    for child in children:
        resolved, child_tree = merge_comparison_results(child, universe, leaf_data)
        resolved_children.append(resolved)
        child_trees.append(child_tree)
 
    if operator == "and":
        result = resolved_children[0]
        for child_idx in resolved_children[1:]:
            result = result.intersection(child_idx)
    elif operator == "or":
        result = resolved_children[0]
        for child_idx in resolved_children[1:]:
            result = result.union(child_idx)
    elif operator == "not":
        if len(resolved_children) != 1:
            raise ValueError("'not' expects exactly one child")
        if universe is None:
            raise ValueError("'not' requires a `universe` Index to compute the complement against")
        result = universe.difference(resolved_children[0])
    else:
        raise ValueError(f"Unknown operator: {operator}")
 
    tree_node = {
        "id": node.get("id"),
        "operator": operator,
        "count": len(result),
        "children": child_trees,
    }
    return result, tree_node
 
 
def flatten_count_tree(tree_node: Dict, out: List[Dict] = None) -> List[Dict]:
    """Post-order flatten of the count tree — children (in resolution order)
    before their parent — giving the same shape/order as the old flat
    `step_counts` list, derived from the tree instead of tracked separately."""
    if out is None:
        out = []
    for child in tree_node.get("children", []):
        flatten_count_tree(child, out)
 
    entry = {"id": tree_node["id"], "count": tree_node["count"]}
    if "operator" in tree_node:
        entry["type"] = tree_node["operator"]
    else:
        entry["type"] = tree_node["type"]
        if tree_node.get("description"):
            entry["description"] = tree_node["description"]
    out.append(entry)
    return out
 
 
# --- 6. build the protein x comparison log2FC matrix for the final ids ------------
def build_heatmap_matrix(final_ids: pd.Index, leaf_data: Dict[str, Dict]) -> pd.DataFrame:
    columns = []
    for leaf_id, data in leaf_data.items():
        log2fc = data["log2fc"]
        if log2fc.empty:
            continue
        reindexed = log2fc.reindex(final_ids)
        reindexed.columns = [f"{leaf_id} | {col}" for col in reindexed.columns]
        columns.append(reindexed)
 
    if not columns:
        return pd.DataFrame(index=final_ids)
 
    return pd.concat(columns, axis=1)
 
 
# --- 7. endpoint -------------------------------------------------------------
@router.post("/compare")
def get_compare(comparisons: CompareModel, user: UserModel = Depends(get_user_from_token)):
    if len(comparisons.children) == 0:
        raise HTTPException(status_code=400, detail="No comparisons provided")
 
    operator_root = comparisons.type
    result, leaf_data = _process_comparison_children(comparisons, operator=operator_root)
 
    final_ids, count_tree = merge_comparison_results(result, leaf_data=leaf_data)
    step_counts = flatten_count_tree(count_tree)
    heatmap = build_heatmap_matrix(final_ids, leaf_data)
    heatmap = heatmap.where(pd.notnull(heatmap), None)  # NaN -> None so it's valid JSON
    
    if heatmap.empty:
        raise HTTPException(status_code=404, detail="No data found for the given comparison. Ensure that the submission tags and condition application tags are correct and that there is data available.")
    if heatmap.columns.size == 1:
        heatmap_out = heatmap.sort_values(by=heatmap.columns[0], ascending=False)
    else:
        heatmap_out = cluster_to_dataframe(heatmap.values, n_clusters=5, index = heatmap.index, columns=heatmap.columns)
    heatmap_out = heatmap_out.reset_index(names="tag")
    return {
        "tags": final_ids.to_list(),
        "step_counts": step_counts,
        "tree" : count_tree,
        "heatmap": {
            "data" : heatmap_out.to_dict(orient="records"),
            "value_names" : [col for col in heatmap.columns if col not in ["tag", "index"]],
            "label_names" : ["tag"],
            "rows": heatmap.reset_index().rename(columns={"index": "tag"}).to_dict(orient="records"),
        }
    }