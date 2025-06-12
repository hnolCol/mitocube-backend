from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException

from services.users import is_user_admin
from services.mail import send_email_in_background
from lib.database.Database import Database 
from config.models.user import UserModel

DB = Database.DB()


router = APIRouter(
    prefix="/api/rc",
    tags=["Proteomes"]
    )

    
@router.post("network")
def add_network(self):
    "" 
    
    
    
@router.patch("fulltext")
def update_full_text_search(user : UserModel = Depends(is_user_admin)):
    """Updates the full text search

    Parameters
    ----------
    user : UserModel, optional
        the inferred user from the token by default Depends(is_user_admin)
    """
    
    
    
    
    
    