
from datetime import timedelta

from fastapi import APIRouter, Depends,  HTTPException
from lib.database.Database import Database
from config.models.user import UserModel
from services.users import get_user_from_token
from config.exceptions.HTTPExceptions import submission_tag_not_found

import networkx as nx
import random
from typing import Dict, Any, List
from lib.cache.cache import db_cache_runtime
from collections import deque
DB = Database.DB()

router = APIRouter(
    prefix="/api/submissions/analysis",
    tags=["Annotations"],
    )

import math
from typing import Any, Dict, List, Optional
 
import networkx as nx
import numpy as np
from numba import njit

@njit(cache=True)
def remove_overlaps_numba(coords, min_dist, iterations):
    min_dist2 = min_dist * min_dist

    for _ in range(iterations):
        moved = False

        for i in range(coords.shape[0]):
            for j in range(i + 1, coords.shape[0]):

                dx = coords[i, 0] - coords[j, 0]
                dy = coords[i, 1] - coords[j, 1]

                dist2 = dx * dx + dy * dy

                if dist2 < min_dist2 and dist2 > 1e-12:
                    dist = np.sqrt(dist2)

                    factor = (min_dist - dist) / (2.0 * dist)

                    px = dx * factor
                    py = dy * factor

                    coords[i, 0] += px
                    coords[i, 1] += py

                    coords[j, 0] -= px
                    coords[j, 1] -= py

                    moved = True

        if not moved:
            break

    return coords
 
# -----------------------------------------------------------------
# 1. Figure out which nodes are "centers"
# -----------------------------------------------------------------
def infer_center_nodes(
    G: nx.Graph,
    center_type: Optional[str] = None,
) -> List[Any]:
    """
    Decide which nodes act as cluster centers.
 
    - If center_type is given, any node whose attrs["type"] == center_type
      is treated as a center.
    - Otherwise, falls back to picking the highest-degree node in each
      connected component (a reasonable default when no explicit type
      tagging exists).
    """
    if center_type is not None:
        centers = [n for n, attrs in G.nodes(data=True) if attrs.get("type") == center_type]
        if centers:
            return centers
 
    centers = []
    for component in nx.connected_components(G):
        sub = G.subgraph(component)
        center = max(sub.degree, key=lambda x: x[1])[0]
        centers.append(center)
    return centers
 
 
# -----------------------------------------------------------------
# 2. Map every node to its cluster's center
# -----------------------------------------------------------------
def assign_clusters2(G: nx.Graph, center_nodes: List[Any]) -> Dict[Any, Any]:
    """
    Assigns every node to the nearest center node (by shortest path length).
    Nodes unreachable from any center fall back to being their own cluster.
    """
    cluster_of: Dict[Any, Any] = {}
 
    # multi-source BFS: for each node, find which center it's closest to
    dist_from_center = {
        c: nx.single_source_shortest_path_length(G, c) for c in center_nodes
    }
 
    for node in G.nodes:
        best_center = None
        best_dist = math.inf
        for c in center_nodes:
            d = dist_from_center[c].get(node, math.inf)
            if d < best_dist:
                best_dist = d
                best_center = c
        cluster_of[node] = best_center if best_center is not None else node
 
    return cluster_of
 


def assign_clusters(G, center_nodes):
    cluster_of = {}
    queue = deque()

    # Initialize all centers
    for c in center_nodes:
        cluster_of[c] = c
        queue.append(c)

    while queue:
        node = queue.popleft()

        for nbr in G.neighbors(node):
            if nbr not in cluster_of:
                cluster_of[nbr] = cluster_of[node]
                queue.append(nbr)

    # Handle disconnected nodes
    for node in G.nodes:
        cluster_of.setdefault(node, node)

    return cluster_of
# -----------------------------------------------------------------
# 3a. Measure how connected each pair of clusters is
# -----------------------------------------------------------------
def compute_inter_cluster_weights(
    G: nx.Graph,
    cluster_of: Dict[Any, Any],
) -> Dict[tuple, int]:
    """
    Counts edges that cross between two different clusters.
    Returns { (cluster_a, cluster_b): edge_count }, keys sorted by str()
    so each pair only appears once regardless of edge direction.
    """
    weights: Dict[tuple, int] = {}
    for u, v in G.edges():
        cu, cv = cluster_of[u], cluster_of[v]
        if cu != cv:
            key = tuple(sorted((cu, cv), key=str))
            weights[key] = weights.get(key, 0) + 1
    return weights
 
 
def _pair_weight(weights: Dict[tuple, int], a: Any, b: Any) -> int:
    return weights.get(tuple(sorted((a, b), key=str)), 0)
 
 
# -----------------------------------------------------------------
# 3b. Order clusters so heavily-connected ones sit next to each other
# -----------------------------------------------------------------
def order_clusters_by_overlap(
    center_nodes: List[Any],
    weights: Dict[tuple, int],
    refine_iterations: int = 150,
) -> List[Any]:
    """
    Arranges center_nodes into a circular order that maximizes the total
    inter-cluster edge weight between *adjacent* clusters (including the
    wrap-around pair last->first). This is a circular-arrangement / TSP-like
    problem, so this uses a greedy nearest-neighbor chain followed by a
    simple 2-opt local search — good enough for a handful of clusters.
    """
    n = len(center_nodes)
    if n <= 2:
        return list(center_nodes)
 
    # 1. Greedy chain: repeatedly attach the most-connected remaining cluster
    remaining = set(center_nodes)
    order = [center_nodes[0]]
    remaining.remove(center_nodes[0])
    while remaining:
        last = order[-1]
        nxt = max(remaining, key=lambda c: _pair_weight(weights, last, c))
        order.append(nxt)
        remaining.remove(nxt)
 
    # 2. 2-opt refinement on the circular order
    def circular_score(seq: List[Any]) -> int:
        return sum(
            _pair_weight(weights, seq[i], seq[(i + 1) % len(seq)])
            for i in range(len(seq))
        )
 
    best_score = circular_score(order)
    improved = True
    steps = 0
    while improved and steps < refine_iterations:
        improved = False
        for i in range(n - 1):
            for j in range(i + 1, n):
                candidate = order[:i] + order[i:j + 1][::-1] + order[j + 1:]
                score = circular_score(candidate)
                if score > best_score:
                    order = candidate
                    best_score = score
                    improved = True
            steps += 1
 
    return order
 
 
# -----------------------------------------------------------------
# 3c. Place cluster centers evenly on a circle
# -----------------------------------------------------------------
def place_centers(center_nodes: List[Any], radius: float = 6.0) -> Dict[Any, np.ndarray]:
    n = len(center_nodes)
    initial_pos = {}
    for i, center in enumerate(center_nodes):
        angle = 2 * math.pi * i / n
        initial_pos[center] = np.array(
            [radius * math.cos(angle), radius * math.sin(angle)]
        )
    return initial_pos
 
 
# -----------------------------------------------------------------
# 4. Layout each cluster locally, then shift into place
# -----------------------------------------------------------------
def layout_clusters(
    G: nx.Graph,
    center_nodes: List[Any],
    cluster_of: Dict[Any, Any],
    center_pos: Dict[Any, np.ndarray],
    seed: int = 42,
    k: float = 1.2,
    iterations: int = 150,
) -> Dict[Any, np.ndarray]:
    pos = dict(center_pos)
 
    for center in center_nodes:
        members = [n for n in G.nodes if cluster_of[n] == center and n != center]
        if not members:
            continue
 
        sub_nodes = [center] + members
        sub_G = G.subgraph(sub_nodes)
 
        rng = np.random.RandomState(seed)
        init = {center: np.array([0.0, 0.0])}
        init.update({m: rng.rand(2) - 0.5 for m in members})
 
        sub_pos = nx.spring_layout(
            sub_G,
            pos=init,
            fixed=[center],
            seed=seed,
            k=k / np.sqrt(len(sub_nodes)),
            iterations=iterations,
        )
 
        offset = center_pos[center]
        for node, p in sub_pos.items():
            if node != center:
                pos[node] = p + offset
 
    return pos
 
 
# -----------------------------------------------------------------
# 5. Final overlap cleanup
# -----------------------------------------------------------------
def remove_overlaps(pos, min_dist=0.3, iterations=50):
    nodes = list(pos.keys())
    coords = np.array([pos[n] for n in nodes], dtype=np.float64)

    coords = remove_overlaps_numba(coords, min_dist, iterations)

    return {n: coords[i] for i, n in enumerate(nodes)}
 
 
# -----------------------------------------------------------------
# 6. Main entry point — same signature/output shape as your original
# -----------------------------------------------------------------
def nx_to_indexed_graph_with_layout(
    G: nx.Graph,
    seed: int = 42,
    scale: float = 1.0,
    k: Optional[float] = None,
    iterations: int = 150,
    center_nodes: Optional[List[Any]] = None,
    center_type: Optional[str] = None,
    radius: float = 6.0,
    min_dist: float = 0.3,
    order_by_overlap: bool = True,
) -> Dict[str, Any]:
    """
    Convert a NetworkX graph to an indexed graph with a clustered,
    force-directed layout: nodes group tightly around their cluster's
    center node, and clusters themselves are spaced apart.
 
    Args:
        G:            input graph. Node attrs may include "type".
        seed:         RNG seed for reproducibility.
        scale:        final uniform scale-up applied to all positions.
        k:            spring_layout spacing factor used *within* each
                      cluster (k / sqrt(cluster_size) is passed to
                      spring_layout). Defaults to 1.2 if not given.
        iterations:   spring_layout iterations per cluster.
        center_nodes: explicit list of nodes to treat as cluster centers.
                      If omitted, inferred via center_type or, failing
                      that, highest-degree-per-component.
        center_type:  if center_nodes is omitted, nodes whose attrs["type"]
                      equals this value are used as centers.
        radius:       distance of cluster centers from the origin
                      (increase to separate clusters more).
        min_dist:     minimum allowed distance between any two nodes in
                      the final layout (overlap cleanup).
        order_by_overlap: if True, arranges clusters around the circle so
                      that clusters with more inter-cluster edges (i.e.
                      more overlap/connection between them) end up next
                      to each other, instead of an arbitrary order.
 
    Returns:
        { "nodes": [{ tag, type, x, y }], "links": [[i, j]] }
    """
    if G.number_of_nodes() == 0:
        return {"nodes": [], "links": []}
 
    k_value = k if k is not None else 1.2
 
    # 1. Determine centers + cluster membership
    if center_nodes is None:
        center_nodes = infer_center_nodes(G, center_type=center_type)
    cluster_of = assign_clusters(G, center_nodes)
 
    # 1b. Optionally reorder centers so heavily-connected clusters are adjacent
    if order_by_overlap and len(center_nodes) > 2:
        inter_weights = compute_inter_cluster_weights(G, cluster_of)
        center_nodes = order_clusters_by_overlap(center_nodes, inter_weights)
 
    # 2. Compute clustered layout
    center_pos = place_centers(center_nodes, radius=radius)
    pos = layout_clusters(
        G, center_nodes, cluster_of, center_pos,
        seed=seed, k=k_value, iterations=iterations,
    )
    pos = remove_overlaps(pos, min_dist=min_dist)
 
    # 3. Apply final scale
    if scale != 1.0:
        pos = {n: p * scale for n, p in pos.items()}
 
    # 4. Assign stable indices + positions (same shape as before)
    nodes = []
    node_index = {}
 
    for i, (node, attrs) in enumerate(G.nodes(data=True)):
        node_index[node] = i
        x, y = pos[node]
 
        nodes.append({
            "tag": node,
            "type": attrs.get("type", "unknown"),
            "x": float(x),
            "y": float(y),
        })
 
    # 5. Convert edges to index pairs
    links = [
        [node_index[u], node_index[v]]
        for u, v in G.edges()
    ]
 
    return {
        "nodes": nodes,
        "links": links,
    }
 

def nx_to_indexed_graph_with_layout2(
    G: nx.Graph,
    seed: int = 42,
    scale: float = 1.0,
    k = None,
    iterations: int = 150
) -> Dict[str, Any]:
    """
    Convert a NetworkX graph to an indexed graph with force-directed positions.

    Returns:
    {
      nodes: [{ tag, type, x, y }],
      links: [[i, j]]
    }
    """

    # 1. Compute force-directed layout
    pos = nx.spring_layout(
        G,
        k = None,
        seed=seed,
        scale=scale,
        iterations=iterations,
        method="energy"
    )

    nodes = []
    node_index = {}

    # 2. Assign stable indices + positions
    for i, (node, attrs) in enumerate(G.nodes(data=True)):
        node_index[node] = i

        x, y = pos[node]

        nodes.append({
            "tag": node,
            "type": attrs.get("type", "unknown"),
            "x": float(x),
            "y": float(y)
        })

    # 3. Convert edges to index pairs
    links = [
        [node_index[u], node_index[v]]
        for u, v in G.edges()
    ]

    return {
        "nodes": nodes,
        "links": links
    }
    
    
def make_graph(graph_data : List[tuple] = None) -> nx.Graph:
    """Creates a nx.Graph from the annotation data

    Parameters
    ----------
    graph_data : List[tuple], optional
        _description_, by default None

    Returns
    -------
    nx.Graph
        _description_
    """
    G = nx.Graph()

    for annotation_tag, protein_tags in graph_data:
        
        for p in protein_tags:
            G.add_node(p, type="protein")
        G.add_node(annotation_tag, type="annotation")
        for p in protein_tags:
            G.add_edge(p, annotation_tag)
            
    return G

@router.get("/{submission_tag}/annotations/network")
def get_annotation_network(submission_tag : str, annotation_group_tag : str = None, show_quantified_proteins_only : bool = True, min_proteins : int = 0, user : UserModel = Depends(get_user_from_token)):
    "" 
    
    
    if not DB.submissions.exists(tag = submission_tag): raise submission_tag_not_found 
    if not DB.submissions.quantification_exists(tag = submission_tag, type = "proteins"): raise HTTPException(status_code=404, detail="No quantification data found for this submission.")
    cache_key = db_cache_runtime.make_cache_key(key_data = ["db.submission.get_network",submission_tag, annotation_group_tag, show_quantified_proteins_only, min_proteins])  
    cached_result =  db_cache_runtime.get(cache_key)
    if cached_result is not None:
        return cached_result
    if DB.annotation_groups.exists(tag = annotation_group_tag):
        annotation_tags = DB.annotation_groups.get_annotations(group_tag = annotation_group_tag)
        graph_data = []
        for annotation_tag in annotation_tags:
            if DB.annotations.exists(tag = annotation_tag): 
                if DB.annotations.count_proteins(tag = annotation_tag) >= min_proteins:
                    #get the annotation data and add it to the network
                    #TO DO : add the annotation data to the network
                    protein_tags = DB.annotations.get_protein_tags(tag = annotation_tag)
                    isin = DB.submissions.is_quantified(tag = submission_tag, quant_tags = protein_tags, quantification_type = "proteins")
                    #at least on protein must be quantified
                    if isin.sum() > 0:
                        if show_quantified_proteins_only:
                            protein_tags = isin[isin].index.tolist()
                            
                        graph_data.append((annotation_tag, protein_tags))
        if len(graph_data) == 0:
            raise HTTPException(status_code=404, detail="No annotations found for this submission with the given parameters. Or none of the proteins in the annotations are quantified in this submission.")
        G = make_graph(graph_data)
        result = nx_to_indexed_graph_with_layout(
                G,
                center_type="annotation",   # or center_nodes=["Pathway_A", "Pathway_B"]
                radius=6.0,
                min_dist=0.3,
            )
          
        db_cache_runtime.set(cache_key, result, cache_time=timedelta(hours = 12))
        
        return result