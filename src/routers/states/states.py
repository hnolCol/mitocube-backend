from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from config.enums.states import SubmissionStatesEnums, SubmissionStateColors


from lib.database.Database import Database
from services.users import get_user_from_token



DB = Database.DB()

router = APIRouter(dependencies=[Depends(get_user_from_token)],
    prefix="/api/states",
    tags=["States"],
    )


@router.get('/{state_tag}/name')
def get_state_name(state_tag : int) -> str:
    "" 
    try: 
        return SubmissionStatesEnums(state_tag).name
    except:
        raise HTTPException(status_code=400, detail="The state was not found.")
        
@router.get('/{state_tag}/color')
def get_state_name(state_tag : int) -> str:
    "" 
    try:
        state_name = SubmissionStatesEnums(state_tag).name

        return SubmissionStateColors[state_name].value
    except Exception as e:
        print(e)
        raise HTTPException(status_code=400, detail="The state was not found or no color is associated to it.")
    