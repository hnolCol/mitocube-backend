"""
Router for exporting submission metadata to markdown format.
"""

import traceback

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC

from config.models.user import UserModel
from config.exceptions.HTTPExceptions import tag_not_found

from services.users import get_user_from_token
from services.export_submissions import export_submission_to_markdown


router = APIRouter(dependencies=[Depends(get_user_from_token)],
    prefix="/api",
    tags=["Submission", "Export"],
)


def _check_access(submission_tag: str, user: UserModel, db: DatabaseABC) -> None:
    """Raises if the submission does not exist or the user has no access."""
    if not db.submissions.exists(tag=submission_tag):
        raise tag_not_found
    if not db.submission_filter.has_user_access(user_tag=user.tag, submission_tag=submission_tag):
        raise HTTPException(
            status_code=403,
            detail=f"User '{user.tag}' does not have access to submission '{submission_tag}'."
        )


def _build_markdown(submission_tag: str, db: DatabaseABC, **include_flags) -> str:
    """Builds the markdown export and converts failures into a 500."""
    try:
        return export_submission_to_markdown(submission_tag=submission_tag, db=db, **include_flags)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export submission metadata: {str(e)}"
        )


@router.get("/submissions/{submission_tag}/export/md/file",
            summary="Download submission metadata as markdown file.")
def download_submission_md_file(
    submission_tag: str,
    include_condition_applications: bool = True,
    include_protocols: bool = True,
    include_protocol_text: bool = True,
    include_runlist: bool = True,
    include_samples: bool = True,
    include_metatext: bool = True,
    include_timeline: bool = True,
    user: UserModel = Depends(get_user_from_token),
    db: DatabaseABC = Depends(get_db),
) -> Response:
    """
    Download submission metadata as a markdown file.

    Parameters
    ----------
    submission_tag : str
        The tag of the submission to export
    include_condition_applications : bool, optional
        Whether to include condition applications, by default True
    include_protocols : bool, optional
        Whether to include protocols, by default True
    include_protocol_text : bool, optional
        Whether to include the full text of protocols, by default True
    include_runlist : bool, optional
        Whether to include run lists, by default True
    include_samples : bool, optional
        Whether to include samples, by default True
    include_metatext : bool, optional
        Whether to include the research aim and other metatexts, by default True
    include_timeline : bool, optional
        Whether to include the timeline (state history), by default True
    user : UserModel, optional
        The user making the request, by default Depends(get_user_from_token)
    db : DatabaseABC, optional
        The database, by default Depends(get_db)

    Returns
    -------
    Response
        A downloadable markdown file with the submission metadata

    Raises
    ------
    tag_not_found
        If the submission does not exist
    HTTPException
        403 if the user does not have access, 500 if the export fails
    """
    _check_access(submission_tag, user, db)

    markdown_content = _build_markdown(
        submission_tag,
        db,
        include_condition_applications=include_condition_applications,
        include_protocols=include_protocols,
        include_protocol_text=include_protocol_text,
        include_runlist=include_runlist,
        include_samples=include_samples,
        include_metatext=include_metatext,
        include_timeline=include_timeline,
    )

    filename = f"submission_{submission_tag}.md"
    return Response(
        content=markdown_content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )