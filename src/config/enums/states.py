from enum import IntEnum, Enum

class SubmissionStatesEnums(IntEnum):
    """
    Enumerate of the submission states
    """
    CANCELED = -2 
    PAUSED = -1
    SUBMITTED = 0 
    PROCESSED = 1 
    MEASURING = 2
    ANALYSIS = 3 
    DONE = 4 
    ACTIVE = 5


class SubmissionStateColors(Enum):
    CANCELED = "#1e3f49"
    PAUSED = "#484848"
    SUBMITTED = "#cfcfcf"
    PROCESSED = "#93b98e" 
    MEASURING = "#558ba4"
    ANALYSIS = "#dbae57" 
    DONE = "#eb6a47" 
    ACTIVE = "#ac3e30"
    
