import time 

from fastapi import APIRouter, BackgroundTasks, Depends, Body

from config.models.user import UserModel
from config.models.token.token import TokenVerificationCode, TokenResponse, ShareTokenPassword, TokenValidResponse
from config.settings.general import get_general_settings
from config.settings.email import get_email_settings




from lib.database.Database import Database
DB = Database.DB()

EMAIL_SETTINGS = get_email_settings()
GENERAL_SETTINGS = get_general_settings()
router = APIRouter(
    prefix="/api/ai/openai",
    tags=["OpenAI", "ChatGPT"]
    )



@router.get("/cypher", response_description="Generates a cypher query for a given prompt.", response_model=str)
def generate_cypher_query(prompt: str) -> str:
    
    cypher_query = DB.openai.generate_cypher_query_for_prompt(prompt)
    print(cypher_query)
    
    return cypher_query