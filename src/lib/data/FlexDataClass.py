from __future__ import annotations

from abc import abstractmethod
from typing import Type, Self, Dict

from config import get_system_settings
import lib.data as dlib

class FlexDataClass:
    _class_object: Type[Self] = None

    @classmethod
    @abstractmethod
    def _get_class_rulings(cls) -> Dict[str, Self]:
        pass

    @classmethod
    def get_class(cls, use_last_class_object: bool = True) -> Type[Self]:

        if not use_last_class_object or cls._class_object is None:
            CONF = get_system_settings()

            rulings = cls._get_class_rulings()

            if CONF.db_handler in rulings:
                cls._class_object = rulings[CONF.db_handler]
            else:
                raise dlib.ABCDataError("Configured type '{str_handler}' (db_handler) is not implemented!".format(str_handler = CONF.db_handler))

        return cls._class_object
