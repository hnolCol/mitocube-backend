from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Self

import lib.data as dlib

import pandas as pd
# import copy
# from enum import Enum
# from typing import Self

# class CSVDataTableType(Enum):
#     UNKNOWN = -1
#     WIDE_FULL_DATA = 1

class ABCGenotypeError(dlib.ABCDatasetError):
    pass

class ABCGenotypeNotFoundError(ABCGenotypeError):
    pass

class ABCGenotype(ABC, dlib.FlexDataClass):

    @classmethod
    def _get_class_rulings(cls) -> Dict[str, Self]:  # ToDo: Update return values!
        import lib.data.sql.postgresql as sqllib
        return {"postgresql": sqllib.PostgreSQLGenotype}