
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from lib.database.Database import Database
from config.models.user import UserModel
from config.enums.states import SubmissionStatesEnums
from services.users import get_user_from_token
from config.exceptions.HTTPExceptions import submission_tag_not_found

from lib.data.transform.PCA import PCATransform
from config.models.dataset.pca import DatasetPCAResponse
import networkx as nx
import random
from typing import Dict, Any, List

DB = Database.DB()

router = APIRouter(
    prefix="/api/submissions/analysis",
    tags=["Annotations"],
    )


def nx_to_indexed_graph_with_layout(
    G: nx.Graph,
    seed: int = 42,
    scale: float = 1.0,
    iterations: int = 50
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
        seed=seed,
        scale=scale,
        iterations=iterations
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
    
    
def make_fake_graph(protein_tags : List[str] = None, annotation_tags : List[str] = None) -> nx.Graph:
    G = nx.Graph()

    for p in protein_tags:
        G.add_node(p, type="protein")

    for a in annotation_tags:
        G.add_node(a, type="annotation")

    # random connections
    for p in protein_tags:
        for a in annotation_tags:
            G.add_edge(p, a)

    return G

@router.get("/{submission_tag}/annotations/network")
def get_annotation_network(submission_tag : str, annotation_group_tag : str = None, min_proteins : int = 3, user : UserModel = Depends(get_user_from_token)):
    "" 
    
    print(annotation_group_tag)
    
    if not DB.submissions.exists(tag = submission_tag): raise submission_tag_not_found 
    if not DB.submissions.quantification_exists(tag = submission_tag, type = "proteins"): raise HTTPException(status_code=404, detail="No quantification data found for this submission.")
    print(DB.annotation_groups.exists(tag = annotation_group_tag))
    if DB.annotation_groups.exists(tag = annotation_group_tag):
        annotation_tags = DB.annotation_groups.get_annotations(group_tag = annotation_group_tag)
        print(annotation_tags)
        for annotation_tag in annotation_tags:
            if DB.annotations.exists(tag = annotation_tag): 
                if DB.annotations.count_proteins(tag = annotation_tag) >= min_proteins:
                    #get the annotation data and add it to the network
                    #TO DO : add the annotation data to the network
                    protein_tags = DB.annotations.get_protein_tags(tag = annotation_tag)
                   
                    #TO DO: FIX LINKS
        print(annotation_tags)
        G = make_fake_graph(protein_tags=protein_tags, annotation_tags=annotation_tags)
    
    
        return nx_to_indexed_graph_with_layout(G)