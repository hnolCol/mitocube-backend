from fastapi import APIRouter, Depends, Request, BackgroundTasks
from fastapi.exceptions import HTTPException

from typing import List, Dict



router = APIRouter(prefix="/api/genotypes", tags=["Genotypes"])

# ToDo: Next
# INFO:     127.0.0.1:49582 - "GET /api/users/roles HTTP/1.1" 404 Not Found

@router.get("/genotypes/q")
def rest_get_genotype_by_query(query : str):  # pass  -> List[GenotypeModel]:
    # ToDo: Implement genotypes and router.get("/genotypes/q")
    print(" > /genotypes/q (@ rest.routes.genotypes.[genotypes.py]) is not implemented yet and returns only [].")
    return []
