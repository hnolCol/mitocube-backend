
from fastapi import APIRouter, Depends
from lib.database.Database import get_db
from lib.database.abstract.Database import DatabaseABC
from typing import List 

from config.models.user import UserModel
from config.models.submissions.comments import SubmissionCommentModel 
from config.exceptions.HTTPExceptions import tag_not_found

from services.users import get_user_from_token
from services.submission import check_submission_access




router = APIRouter(dependencies=[Depends(get_user_from_token)],
    prefix="/api/submissions",
    tags=["Submission"],
    )

# @router.post('/{submission_tag}/comments')
# def post_comment_to_submission(submission_tag : str, content : str, tags : List[str] = None,  user : UserModel = Depends(get_user_from_token)): 
#     """Adds a comment to a submission.

#     Parameters
#     ----------
#     submission_tag : str
#         The submission tag for which the comment should be posted
#     tags : List[str]
#         _description_
#     content : str
#         _description_
#     """

#     db.submissions.insert_comment(tag = submission_tag, comment = SubmissionCommentModel(user_tag = user.tag, content = content, tags = tags))

@router.post('/{submission_tag}/comments')
def post_comment_to_submission(submission_tag: str, comment: SubmissionCommentModel, user: UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)):
    check_submission_access(submission_tag = submission_tag, user = user, db = db)
    comment.user_tag = user.tag
    db.submissions.insert_comment(tag=submission_tag, comment=comment)

    
@router.get('/{submission_tag}/comments')
def get_comments_for_submission(submission_tag : str, user : UserModel = Depends(get_user_from_token), db : DatabaseABC = Depends(get_db)) -> List[SubmissionCommentModel]:
    "" 
    check_submission_access(submission_tag = submission_tag, user = user, db = db)
    return db.submissions.get_comments(tag = submission_tag)
    
    
@router.get('/{submission_tag}/comments/{tag}')
def get_comment_by_tag(user : UserModel = Depends(get_user_from_token)):
    "" 