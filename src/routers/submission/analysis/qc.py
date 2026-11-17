from typing import List

from fastapi import APIRouter, Depends, HTTPException
from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC
from config.models.user import UserModel
from services.users import get_user_from_token
from services.submission import check_submission_access


router = APIRouter(dependencies=[Depends(get_user_from_token)],
    prefix="/api/submissions/analysis",
    tags=["Submission","Analysis","QC"],
)


def _unique_values(dataframe) -> List[str]:
    """Returns the unique non-null values of a sample-by-attribute dataframe."""
    if dataframe is None or dataframe.empty:
        return []
    values = dataframe.values.flatten()
    return list({value for value in values if value is not None and value == value and isinstance(value, str)})


@router.get("/{submission_tag}/qc/targets")
def get_qc_targets(submission_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)):
    """
    Returns all unique proteins that are connected to a condition application or genotype of the
    submission's samples (e.g. knockdown, overexpression or immunoprecipitation targets), together
    with the sources they are connected to. Used by the QC tab to check whether a manipulation worked.
    """
    check_submission_access(submission_tag = submission_tag, user = user, db = db)

    condition_applications = db.samples.get_condition_applications_by_sample_for_submission(submission_tag=submission_tag, sort_ca_tags=True, return_sample_index=False)
    genotypes = None
    if db.submissions.has_genotypes(tag = submission_tag):
        genotypes = db.samples.get_genotypes_by_sample_for_submission(submission_tag=submission_tag, sort_ca_tags=True, return_sample_index=False)

    sources_by_protein = {}

    for ca_tag in _unique_values(condition_applications):
        for protein_tag in db.condition_applications.get_proteins(ca_tag):
            sources_by_protein.setdefault(protein_tag, []).append({
                "type": "condition_application",
                "tag": ca_tag,
                "text": db.condition_applications.get_text(ca_tag)
            })

    for genotype_tag in _unique_values(genotypes):
        for protein_tag in db.genotypes.get_proteins(genotype_tag) or []:
            sources_by_protein.setdefault(protein_tag, []).append({
                "type": "genotype",
                "tag": genotype_tag,
                "text": db.genotypes.get_text(genotype_tag)
            })

    if len(sources_by_protein) == 0:
        raise HTTPException(status_code=404, detail="No proteins connected to condition applications or genotypes found for this submission.")

    targets = [
        {
            "protein_tag": protein_tag,
            "sources": sources
        }
        for protein_tag, sources in sources_by_protein.items()
    ]
    targets = sorted(targets, key=lambda target: target["protein_tag"])

    return {
        "submission_tag": submission_tag,
        "targets": targets
    }
