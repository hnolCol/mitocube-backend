from fastapi import APIRouter, Depends, HTTPException
from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC
from typing import List

from config.models.user import UserModel
from services.attribute_hierarchy import validate_attribute_trees
from config.models.procedures import (
    ExecutionStateModel,
    ExecutionSummaryModel,
    SampleLocationModel,
    ExecutionWellMetricModel,
    FinishProcedureExecutionModel,
    InsertModularProcedureModel,
    InsertProcedureExecutionModel,
    ModularProcedureBaseModel,
    ModularProcedureSubmissionModel,
    ProcedureExecutionModel,
    PublishModularProcedureModel,
    UpdateModularProcedureModel,
)
from services.users import get_user_from_token, is_user_at_least_curator



def _plate_constraints(procedure) -> dict:
    "Extracts the plate layout constraints defined in the procedure setup."
    return {
        "input_plate_format": procedure.input_plate_format,
        "input_plate_type": procedure.input_plate_type,
        "output_plate_format": procedure.output_plate_format,
        "output_plate_type": procedure.output_plate_type,
    }


def _scoped_submission_tags(user, db) -> "list | None":
    """Returns the submission tags the user may see, or None if the user is unrestricted
    (curator role or higher: curators see everything, group curators see their group's
    submissions via the scope computed by the submissions database)."""
    from config.enums.users.roles import UserRolesEnum
    if user.role >= UserRolesEnum.CURATOR:
        return None
    return db.submissions.get_user_submission_scope_tags(user_tag=user.tag)


def _mask_execution_for_scope(execution, scoped_submissions, db):
    """Masks a procedure execution for a restricted user (standard users and group curators:
    their submission scope was computed by the submissions database).
    Wells the user has no sample in are dropped; wells shared with other users' samples only
    expose the user's own samples and no metrics or condition applications; fully own wells
    show all their details. done_submission_tags is limited to the accessible submissions."""
    from config.enums.users.roles import UserRolesEnum
    from config.models.procedures import ProcedureExecutionModel
    if scoped_submissions is None:
        return execution
    scoped = set(scoped_submissions)
    visible = False

    def accessible_tags(sample_tags, sample_map):
        return {submission for tag in sample_tags for submission in sample_map.get(tag, [])}

    def filter_wells(wells, sample_map):
        filtered = []
        for well in wells:
            own_samples = [tag for tag in well.sample_tags
                          if accessible_tags([tag], sample_map) & scoped]
            if len(own_samples) == 0:
                continue
            others_present = len(well.sample_tags) > len(own_samples)
            update = {"sample_tags": own_samples}
            if others_present:
                update["metrics"] = []
                if hasattr(well, "condition_application_tags"):
                    update["condition_application_tags"] = []
            filtered.append(well.model_copy(update=update))
        return filtered

    all_samples = {tag for well in execution.input_wells for tag in well.sample_tags} | \
                  {tag for well in execution.output_wells for tag in well.sample_tags}
    sample_map = db.modular_procedures.get_sample_submission_map(sorted(all_samples))
    input_wells = filter_wells(execution.input_wells, sample_map)
    output_wells = filter_wells(execution.output_wells, sample_map)
    if len(input_wells) == 0 and len(output_wells) == 0:
        return None
    return execution.model_copy(update={
        "input_wells": input_wells,
        "output_wells": output_wells,
        "input_well_metrics": [],
        "done_submission_tags": [tag for tag in execution.done_submission_tags if tag in scoped],
    })



router = APIRouter(dependencies=[Depends(get_user_from_token)],
    prefix="/api/procedures",
    tags=["Modular Procedures"]
    )


@router.get("/q", response_model=List[str])
def get_modular_procedures(search_string : str = None, status : str = None, limit : int = None, latest_only : bool = False, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[str]:
    "Returns the tags of modular procedures that match the search string and status. If latest_only, only the highest version per lineage is returned."
    return db.modular_procedures.find(search_string=search_string, status=status, limit=limit, latest_only=latest_only)


@router.get("/executions/q", response_model=List[ExecutionSummaryModel])
def query_procedure_executions(search_submission_tag : str = None, status : str = None, limit : int = 200, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[ExecutionSummaryModel]:
    """Returns the procedure executions as summaries (header data and well counts) for the
    overview, newest first, optionally filtered by a submission tag and the current state.
    The user's submission scope is respected: curators and admins see everything, group
    curators their group's executions and other users only the executions of their own
    submissions (creators); executions holding other users' data are not released."""
    scoped = _scoped_submission_tags(user, db)
    if scoped is not None:
        if search_submission_tag is not None and search_submission_tag not in scoped:
            return []
        filter_tags = [search_submission_tag] if search_submission_tag is not None else list(scoped)
        visible_tags = set(db.modular_procedures.find_execution_tags_by_submissions(submission_tags=filter_tags))
        if len(visible_tags) == 0:
            return []
    else:
        visible_tags = None
    tags = db.modular_procedures.find_execution_tags(status=status, limit=None)
    if visible_tags is not None:
        tags = [tag for tag in tags if tag in visible_tags]
    tags = tags[:limit] if limit is not None else tags
    summaries = []
    for execution_tag in tags:
        try:
            execution = db.modular_procedures.get_execution(execution_tag=execution_tag)
        except KeyError:
            continue
        summaries.append(ExecutionSummaryModel(
            tag=execution.tag, procedure_tag=execution.procedure_tag,
            input_plate_tag=execution.input_plate_tag, output_plate_tag=execution.output_plate_tag,
            user_tag=execution.user_tag, responsible_user_tag=execution.responsible_user_tag,
            created_at=execution.created_at, status=execution.status,
            finished_at=execution.finished_at, finished_by=execution.finished_by,
            finish_comment=execution.finish_comment,
            done_submission_tags=execution.done_submission_tags,
            n_input_wells=len(execution.input_wells), n_output_wells=len(execution.output_wells)))
    return summaries


@router.get("/submissions/{submission_tag}/wells", response_model=List[SampleLocationModel])
def get_submission_sample_locations(submission_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[SampleLocationModel]:
    """Returns the current plate locations of the samples of a submission: for every sample the
    wells of its most recent procedure execution (input and output plate). The user's submission
    scope is respected; restricted users cannot query foreign submissions."""
    scoped = _scoped_submission_tags(user, db)
    if scoped is not None and submission_tag not in scoped:
        raise HTTPException(status_code=404, detail="Submission not found.")
    try:
        return db.modular_procedures.get_submission_sample_locations(submission_tag=submission_tag)
    except KeyError:
        raise HTTPException(status_code=404, detail="Submission not found.")


@router.get("/executions/{execution_tag}/states", response_model=List[ExecutionStateModel])
def get_procedure_execution_states(execution_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[ExecutionStateModel]:
    "Returns the state history of a procedure execution (state, created_at and the user who made the change), newest first."
    try:
        return db.modular_procedures.get_execution_states(execution_tag=execution_tag)
    except KeyError:
        raise HTTPException(status_code=404, detail="Procedure execution not found.")


@router.get("/executions/{execution_tag}", response_model=ProcedureExecutionModel)
def get_modular_procedure_execution(execution_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> ProcedureExecutionModel:
    """Returns the procedure execution identified by the given tag with all plate details.
    Restricted users only see the wells (samples, input values and metrics) of their own
    submissions: wells without accessible samples are omitted, shared wells expose neither
    metrics nor condition applications of the other users' samples."""
    try:
        execution = db.modular_procedures.get_execution(execution_tag=execution_tag)
    except KeyError:
        raise HTTPException(status_code=404, detail="Procedure execution not found.")
    masked = _mask_execution_for_scope(execution, _scoped_submission_tags(user, db), db)
    if masked is None:
        raise HTTPException(status_code=404, detail="Procedure execution not found.")
    return masked


@router.post("/executions/{execution_tag}/metrics", response_model=ProcedureExecutionModel)
def set_modular_procedure_execution_metrics(execution_tag : str, well_metrics : List[ExecutionWellMetricModel], user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> ProcedureExecutionModel:
    """Sets or updates the measured attribute values (metrics) of the output wells of a procedure
    execution, e.g. the protein concentration of each well. The user must be at least curator."""
    try:
        return db.modular_procedures.set_execution_metrics(execution_tag=execution_tag, well_metrics=well_metrics, user_tag=user.tag)
    except KeyError:
        raise HTTPException(status_code=404, detail="Procedure execution not found.")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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
    """Creates a new draft modular procedure. Condition applications can be reused by tag
    or newly defined as hierarchical attribute/trait trees (like when inserting a submission).
    The user must be at least curator."""
    try:
        procedure.condition_application_trees = validate_attribute_trees(
            get_parents=db.attributes.get_parents,
            attribute_trees=procedure.condition_application_trees,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    try:
        tag = db.modular_procedures.insert(title=procedure.title, description=procedure.description, user_tag=user.tag,
                                          condition_application_tags=procedure.condition_application_tags,
                                          condition_application_trees=procedure.condition_application_trees,
                                          protocol_tags=procedure.protocol_tags,
                                          plate_constraints=_plate_constraints(procedure),
                                          input_attribute_tags=procedure.input_attribute_tags,
                                          output_attribute_tags=procedure.output_attribute_tags,
                                          success_submission_state=procedure.success_submission_state,
                                          pubmed_ids=procedure.pubmed_ids,
                                          min_output_wells_per_sample=procedure.min_output_wells_per_sample,
                                          max_output_wells_per_sample=procedure.max_output_wells_per_sample)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return db.modular_procedures.get(tag=tag)


@router.patch("/{procedure_tag}", response_model=ModularProcedureBaseModel)
def update_modular_procedure(procedure_tag : str, updated_procedure : UpdateModularProcedureModel, user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> ModularProcedureBaseModel:
    """Updates a draft modular procedure (published procedures are immutable). Condition
    applications can be reused by tag or newly defined as hierarchical attribute/trait trees.
    The user must be at least curator."""
    try:
        updated_procedure.condition_application_trees = validate_attribute_trees(
            get_parents=db.attributes.get_parents,
            attribute_trees=updated_procedure.condition_application_trees,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    try:
        db.modular_procedures.update(tag=procedure_tag, title=updated_procedure.title, description=updated_procedure.description,
                                     user_tag=user.tag, condition_application_tags=updated_procedure.condition_application_tags,
                                     condition_application_trees=updated_procedure.condition_application_trees,
                                     protocol_tags=updated_procedure.protocol_tags,
                                     plate_constraints=_plate_constraints(updated_procedure),
                                     input_attribute_tags=updated_procedure.input_attribute_tags,
                                     output_attribute_tags=updated_procedure.output_attribute_tags,
                                     success_submission_state=updated_procedure.success_submission_state,
                                     pubmed_ids=updated_procedure.pubmed_ids,
                                     min_output_wells_per_sample=updated_procedure.min_output_wells_per_sample,
                                     max_output_wells_per_sample=updated_procedure.max_output_wells_per_sample)
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


@router.post("/{procedure_tag}/retire", response_model=ModularProcedureBaseModel)
def retire_modular_procedure(procedure_tag : str, user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> ModularProcedureBaseModel:
    """Retires a published modular procedure: because published procedures are content-hash
    immutable and never deleted (their executions must stay reproducible), retiring marks a
    procedure as no longer usable — greyed out in the UI, not assignable and not executable —
    while keeping its content, hash and history. The user must be at least curator."""
    try:
        return db.modular_procedures.retire(tag=procedure_tag, user_tag=user.tag)
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

@router.post("/{procedure_tag}/executions/draft", response_model=ProcedureExecutionModel)
def create_execution_draft(procedure_tag : str, user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> ProcedureExecutionModel:
    """Creates an empty DRAFT execution of the given published modular procedure with a
    backend-generated ID: the design (plates, sample placement, transfer map, per-well values)
    can be saved via PUT /executions/{execution_tag} and continued later — drafts do not block
    anything. Starting the run (full validation incl. output well occupancy) happens via
    POST /executions/{execution_tag}/start. The user must be at least curator."""
    try:
        return db.modular_procedures.create_execution_draft(tag=procedure_tag, user_tag=user.tag)
    except KeyError:
        raise HTTPException(status_code=404, detail="Modular procedure not found.")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/executions/{execution_tag}", response_model=ProcedureExecutionModel)
def save_execution_draft(execution_tag : str, design : InsertProcedureExecutionModel, user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> ProcedureExecutionModel:
    """Saves the setup of a DRAFT execution, replacing the stored design wholesale (plates,
    responsible user, sample placement, transfer map, condition applications and per-well
    values). Executions that already started are immutable. The user must be at least curator."""
    try:
        return db.modular_procedures.update_execution_draft(execution_tag=execution_tag, design_update=design, user_tag=user.tag)
    except KeyError:
        raise HTTPException(status_code=404, detail="Procedure execution not found.")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/executions/{execution_tag}/start", response_model=ProcedureExecutionModel)
def start_procedure_execution(execution_tag : str, user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> ProcedureExecutionModel:
    """Starts a saved draft execution as a run: the stored design is re-validated in full —
    including the output well occupancy, which drafts do not block until they start — and the
    execution moves to RUNNING and starts blocking its output wells. The user must be at least
    curator (and becomes the executing user)."""
    try:
        return db.modular_procedures.start_execution(execution_tag=execution_tag, user_tag=user.tag)
    except KeyError:
        raise HTTPException(status_code=404, detail="Procedure execution not found.")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/executions/{execution_tag}", response_model=bool)
def delete_procedure_execution_draft(execution_tag : str, user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> bool:
    """Deletes a DRAFT execution (and only a draft): drafts are setup work, not recorded facility
    history. Started executions are never deleted — they are part of the reproducibility chain.
    The user must be at least curator."""
    try:
        return db.modular_procedures.delete_execution_draft(execution_tag=execution_tag, user_tag=user.tag)
    except KeyError:
        raise HTTPException(status_code=404, detail="Procedure execution not found.")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/executions/{execution_tag}/finish", response_model=ProcedureExecutionModel)
def finish_modular_procedure_execution(execution_tag : str, confirmation : FinishProcedureExecutionModel, user : UserModel = Depends(is_user_at_least_curator), db : DatabaseABC = Depends(get_db)) -> ProcedureExecutionModel:
    """Transitions a procedure execution to the given state (SUCCEEDED, FAILED or ABORTED):
    the change is recorded in the execution's state history together with the user who made
    it. Leaving RUNNING frees the linked submissions for the next module; a transition to
    SUCCEEDED sets the procedure's optional submission state and makes the submissions adopt
    the condition applications of the module. Already finished executions can be corrected
    (e.g. FAILED to SUCCEEDED). Only curators and admins may change the state."""
    try:
        return db.modular_procedures.finish_execution(execution_tag=execution_tag, outcome=confirmation.outcome,
                                                      user_tag=user.tag, comment=confirmation.comment,
                                                      block_output_wells=confirmation.block_output_wells)
    except KeyError:
        raise HTTPException(status_code=404, detail="Procedure execution not found.")
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
