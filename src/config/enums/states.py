from enum import Enum

class States(Enum):
    """
    Enums that are defined in the frontend which 
    knows what to do with such input types.
    """
    SUBMITTED = "Submitted"
    PROCESSED = "Samples Processed"
    MEASURING = "Measuring"
    PAUSED = "Paused"
    STOPPED = "Stopped"
    DONE = "Done"
    