from __future__ import annotations

from abc import ABC, ABCMeta, abstractmethod
from datetime import datetime
from enum import IntEnum, unique
from typing import Dict, List, Self, Type

import lib.data as dlib

from config import get_system_settings

class PostgreSQLDataRow(dlib.ABCDataRow):
    pass
