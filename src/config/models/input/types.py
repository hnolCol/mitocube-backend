
from pydantic import BaseModel
from config.enums.input.types import InputTypeEnum

class SubmissionInput(BaseModel):
    """Submission Input Model"""
    name : str 
    type : InputTypeEnum
    hint : str = ""
    optional : bool = False
    style : dict = {} #style props for the front end

class ComboList(SubmissionInput):
    """Combolist model"""
    items : list[str] | dict
    type : InputTypeEnum = InputTypeEnum.C
    default : str = ""
    items_depend_on : str = ""

class Numeric(SubmissionInput):
    """Model to handle numeric inputs."""
    default : float = 1
    min : int = 1
    max : int = 9999
    stepSize : int = 1  #not step_size to match blueprint's params (frontend)
    placeholder : str = ""
    type : InputTypeEnum = InputTypeEnum.N
    
class TextField(SubmissionInput):
    """Model to handle text fields inputs"""
    default : str = ""
    placeholder : str = ""
    type : InputTypeEnum = InputTypeEnum.TF

class PasswordField(SubmissionInput):
    """Model to handle text fields inputs"""
    default : str = ""
    placeholder : str = ""
    type : InputTypeEnum = InputTypeEnum.PW
    min_length : int = 8
    style = {"type" : "password"}

class TextLine(SubmissionInput):
    """Model to handle text line inputs"""
    default : str = ""
    placeholder : str = ""
    type : InputTypeEnum = InputTypeEnum.T




