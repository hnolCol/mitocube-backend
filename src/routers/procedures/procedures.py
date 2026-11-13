from fastapi import APIRouter, Depends, HTTPException
from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC
from typing import List

from config.models.user import UserModel
from config.models.procedures import (
    InsertModularProcedureModel,
    InsertProcedureExecutionModel,
    ModularProcedureBaseModel,
    ModularProcedureSubmissionModel,
    ProcedureExecutionModel,
    PublishModularProcedureModel,
    UpdateModularProcedureModel,
)
from services.users import get_user_from_token, is_user_at_least_curator



router = APIRouter(dependencies=[Depends(get_user_from_token)],
    prefix="/api/procedures",
    tags=["Modular Procedures"]
    )


@router.get("/q", response_model=List[str])
def get_modular_procedures(search_string : str = None, status : str = None, limit : int = None, latest_only : bool = False, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[str]:
    "Returns the tags of modular procedures that match the search string and status. If latest_only, only the highest version per lineage is returned."
    return db.modular_procedures.find(search_string=search_string, status=status, limit=limit, latest_only=latest_only)


@router.get("/executions/{execution_tag}", response_model=ProcedureExecutionModel)
def get_modular_procedure_execution(execution_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> ProcedureExecutionModel:
    "Returns the procedure execution identified by the given tag."
    try:
        return db.modular_procedures.get_execution(execution_tag=execution_tag)
    except KeyError:
        raise HTTPException(status_code=404, detail="Procedure execution not found.")


@router.get("/submissions/{submission_tag}", response_model=List[ModularProcedureSubmissionModel])
def get_submission_modular_procedures(submission_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[ModularProcedureSubmissionModel]:
    "Returns the modular procedures the given submission is linked to, in the order it was assigned to them."
    return db.modular_procedures.get_submission_procedures(submission_tag=submission_tag)


@router.get("/{procedure_tag}", response_model=ModularProcedureBaseModel)
def get_modular_procedure(procedure_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> ModularProcedureBaseModel:
    "Returns the modular procedure identified by the given tag."
    try:
        return db.modular_procedures.get(tag=procedure_tag)
    except KeyError:
        raise HTTPException(status_code=404, detail="Modular procedure not found.")


@router.get("/{procedure_tag}/submissions", response_model=List[ModularProcedureSubmissionModel])
def get_modular_procedure_submissions(procedure_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[ModularProcedureSubmissionModel]:
    "Returns the submissions linked to the given modular procedure with their link information."
    try:
        return db.modular_procedures.get_submissions(tag=procedure_tag)
    except KeyError:
        raise HTTPException(status_code=404, detail="Modular procedure not found.")


@router.post("/", response_model=ModularProcedureBaseModel)
def insert_modular_procedure(procedure : InsertModularProcedureModel, user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> ModularProcedureBaseModel:
    "Creates a new draft modular procedure. The user must be at least curator."
    try:
        tag = db.modular_procedures.insert(title=procedure.title, description=procedure.description, user_tag=user.tag,
                                          condition_application_tags=procedure.condition_application_tags,
                                          protocol_tags=procedure.protocol_tags)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return db.modular_procedures.get(tag=tag)


@router.patch("/{procedure_tag}", response_model=ModularProcedureBaseModel)
def update_modular_procedure(procedure_tag : str, updated_procedure : UpdateModularProcedureModel, user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> ModularProcedureBaseModel:
    "Updates a draft modular procedure. Published modular procedures are immutable. The user must be at least curator."
    try:
        db.modular_procedures.update(tag=procedure_tag, title=updated_procedure.title, description=updated_procedure.description,
                                     user_tag=user.tag, condition_application_tags=updated_procedure.condition_application_tags,
                                     protocol_tags=updated_procedure.protocol_tags)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return db.modular_procedures.get(tag=procedure_tag)


@router.post("/{procedure_tag}/publish", response_model=PublishModularProcedureModel)
def publish_modular_procedure(procedure_tag : str, user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> PublishModularProcedureModel:
    "Publishes a draft modular procedure: sets the SHA-256 content hash and makes it immutable. The user must be at least curator."
    try:
        return db.modular_procedures.publish(tag=procedure_tag, user_tag=user.tag)
    except KeyError:
        raise HTTPException(status_code=404, detail="Modular procedure not found.")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{procedure_tag}/link/{submission_tag}", response_model=bool)
def link_modular_procedure_to_submission(procedure_tag : str, submission_tag : str, user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> bool:
    "Assigns the given submission to the specified modular procedure. The user must be at least curator."
    try:
        return db.modular_procedures.link(tag=procedure_tag, submission_tag=submission_tag, user_tag=user.tag)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{procedure_tag}/link/{submission_tag}", response_model=bool)
def unlink_modular_procedure_from_submission(procedure_tag : str, submission_tag : str, user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> bool:
    "Removes the given submission from the specified modular procedure. The user must be at least curator."
    try:
        return db.modular_procedures.unlink(tag=procedure_tag, submission_tag=submission_tag)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{procedure_tag}/link/{submission_tag}/done", response_model=bool)
def mark_modular_procedure_submission_done(procedure_tag : str, submission_tag : str, user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> bool:
    "Marks the given submission as done in the specified modular procedure so that it can proceed to the next procedure. The user must be at least curator."
    try:
        return db.modular_procedures.mark_done(tag=procedure_tag, submission_tag=submission_tag, user_tag=user.tag)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{procedure_tag}/link/{submission_tag}/done", response_model=bool)
def reopen_modular_procedure_submission(procedure_tag : str, submission_tag : str, user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> bool:
    "Reverts the done flag of the given submission in the specified modular procedure. The user must be at least curator."
    try:
        return db.modular_procedures.reopen(tag=procedure_tag, submission_tag=submission_tag)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{procedure_tag}/executions", response_model=List[str])
def get_modular_procedure_executions(procedure_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[str]:
    "Returns the tags of the executions of the given modular procedure."
    try:
        return db.modular_procedures.get_executions(tag=procedure_tag)
    except KeyError:
        raise HTTPException(status_code=404, detail="Modular procedure not found.")


@router.post("/{procedure_tag}/execute", response_model=ProcedureExecutionModel)
def execute_modular_procedure(procedure_tag : str, execution : InsertProcedureExecutionModel, user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> ProcedureExecutionModel:
    """Executes the given published modular procedure on a set of samples: maps the input plate wells
    to the output plate wells (pooling and splitting supported) and marks the submissions owning the
    input samples as done in the procedure. The user must be at least curator."""
    try:
        return db.modular_procedures.execute(tag=procedure_tag, execution=execution, user_tag=user.tag)
    except KeyError:
        raise HTTPException(status_code=404, detail="Modular procedure not found.")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{procedure_tag}/versions", response_model=List[str])
def get_modular_procedure_versions(procedure_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[str]:
    "Returns the tags of all versions in the lineage of the given modular procedure, oldest first."
    try:
        return db.modular_procedures.get_versions(tag=procedure_tag)
    except KeyError:
        raise HTTPException(status_code=404, detail="Modular procedure not found.")


@router.post("/{procedure_tag}/versions", response_model=ModularProcedureBaseModel)
def create_modular_procedure_version(procedure_tag : str, user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> ModularProcedureBaseModel:
    """Creates a new draft version of the given published modular procedure, copying its content.
    Submissions stay linked to the version they were assigned to. The user must be at least curator."""
    try:
        return db.modular_procedures.create_version(tag=procedure_tag, user_tag=user.tag)
    except KeyError:
        raise HTTPException(status_code=404, detail="Modular procedure not found.")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
