
from fastapi import APIRouter, Depends
from typing import List 

from lib.database.Database import Database
from config.models.user import UserModel
from config.models.submissions.comments import SubmissionCommentModel 
from config.exceptions.HTTPExceptions import tag_not_found

from services.users import get_user_from_token


DB = Database.DB()


router = APIRouter(
    prefix="/api/submissions",
    tags=["Submission"],
    )

@router.post('/{submission_tag}/comments')
def post_comment_to_submission(submission_tag : str, content : str, tags : List[str] = None,  user : UserModel = Depends(get_user_from_token)): 
    """Adds a comment to a submission.

    Parameters
    ----------
    submission_tag : str
        The submission tag for which the comment should be posted
    tags : List[str]
        _description_
    content : str
        _description_
    """

    DB.submissions.add_comment(tag = submission_tag, comment = SubmissionCommentModel(user_tag = user.tag, content = content, tags = tags))

@router.get('/{submission_tag}/comments')
def get_comments_for_submission(submission_tag : str) -> List[SubmissionCommentModel]:
    "" 
    if not DB.submissions.exists(submission_tag): tag_not_found
    return DB.submissions.get_comments(tag = submission_tag)
    
    
@router.get('/{submission_tag}/comments/{tag}')
def get_comment_by_tag():
    "" 