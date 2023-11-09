from enum import IntEnum, Enum

class SubmissionStates(IntEnum):
    """
    Enums that are defined in the frontend which 
    knows what to do with such input types.
    """
    STOPPED = -2 
    PAUSED = -1
    SUBMITTED = 0 
    PROCESSED = 1 
    MEASURING = 2
    ANALYSIS = 3 
    DONE = 4 
    PUBLISHED = 5


class SubmissionStateColors(Enum):
    STOPPED = "#1e3f49"
    PAUSED = "#484848"
    SUBMITTED = "#ededed"
    PROCESSED = "#dbae57" 
    MEASURING = "#93b98e"
    ANALYSIS = "#558ba4" 
    DONE = "#b91e18" 
    PUBLISHED = "#134295"