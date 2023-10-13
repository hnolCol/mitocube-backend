from pydantic import BaseModel 


class OkResponseWithData(BaseModel):
    status : str = "OK"
    success : bool
    msg : str = None


