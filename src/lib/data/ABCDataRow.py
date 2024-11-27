from __future__ import annotations

from abc import ABC, ABCMeta, abstractmethod
from datetime import datetime
from enum import IntEnum, unique
from typing import Dict, List, Self, Type

import lib.data as dlib

from config import get_system_settings

class ABCDataRow(ABC, dlib.FlexDataClass):
    def __init__(self, parent_dataset: dlib.ABCDataset | None = None,
                 data: Dict[str, float] | None = None,
                 replicates_samples: Dict[str, str] | None = None,
                 batches_samples: Dict[str, str] | None = None):
        pass

    @classmethod
    def _get_class_rulings(cls) -> Dict[str, Self]:
        import lib.data.sql.postgresql as sqllib
        return {"postgresql": sqllib.PostgreSQLDataRow}

    def __init__(self, feature: str,
                 data: Dict[str, float],
                 parent_dataset: dlib.ABCDataset | None = None,
                 replicates_samples: Dict[str, str] | None = None,
                 batches_samples: Dict[str, str] | None = None):
        pass

    ## ToDo: Idea, just one Feature at a time for samples, maybe multiple datasets? ABCDataRows
