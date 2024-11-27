from __future__ import annotations

from datetime import datetime
import json
import re
from typing import Dict, List

import lib.data as dlib
import lib.data.sql.postgresql as psql
from lib.data import ABCAttribute


class CSVAttributeImporter:

    def __init__(self, path_attributes_file: str, path_traits_file: str,
                 attribute_class: dlib.ABCAttribute = psql.PostgreSQLAttribute,
                 trait_class: dlib.ABCTrait = psql.PostgreSQLTrait):

        self._path_attributes_file: str = path_attributes_file
        self._path_traits_file: str = path_traits_file

        self._attribute_class: dlib.ABCAttribute = attribute_class
        self._trait_class: dlib.ABCTrait = trait_class

        self._attributes: Dict[str, dlib.ABCAttribute] = {}
        # self._attributes_sorted: List[dlib.ABCAttribute] = []

        self._traits: Dict[str, dlib.ABCTrait] = {}
        # self._traits_sorted: List[dlib.ABCTrait] = []
