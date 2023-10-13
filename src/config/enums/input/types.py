
from enum import Enum

class InputTypeEnum(Enum):
    """
    Enums that are defined in the frontend which 
    knows what to do with such input types.
    """
    N = "numeric"
    C = "combo"
    T = "text"
    TF = "textfield"
    PW = "password"