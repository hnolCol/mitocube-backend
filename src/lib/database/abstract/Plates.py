from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from config.models.plates import PlateInsertModel, PlateModel, PlateOptionsModel


class PlatesABC(ABC):
    """Handles physical well plates in which samples are stored in the lab."""

    @abstractmethod
    def exists(self, tag : str) -> bool:
        "Checks if a plate with the given tag exists."

    @abstractmethod
    def name_exists(self, name : str) -> bool:
        "Checks if a plate with the given name exists (case insensitive)."

    @abstractmethod
    def next_name(self, rows : int, columns : int) -> str:
        "Suggests the next free plate name for a format, e.g. 'P-96-004'."

    @abstractmethod
    def get_options(self) -> PlateOptionsModel:
        "Returns the selectable traits (format, cold storage, plate type, vendor) for creating a plate."

    @abstractmethod
    def insert(self, plate : PlateInsertModel, user_tag : str) -> str:
        """Inserts a new plate and links the selected traits as condition applications.

        Raises
        ------
        ValueError
            If the name exists already or a trait does not belong to its attribute.
        """

    @abstractmethod
    def get(self, tag : str) -> Optional[PlateModel]:
        "Returns the plate or None if not found."

    @abstractmethod
    def list(self) -> List[PlateModel]:
        "Returns all plates, newest first."

    @abstractmethod
    def get_occupied_positions(self, tag : str) -> List[Tuple[int, int, str]]:
        "Returns (row_index, column_index, position) of all wells on the plate that hold a run."

    @abstractmethod
    def check_positions(self, tag : str, positions : List[List[bool]]) -> None:
        """Checks that a well selection fits the plate and that the selected wells are free.

        Raises
        ------
        ValueError
            If the plate does not exist, the selection does not match or wells are occupied.
        """

    @abstractmethod
    def delete(self, tag : str) -> bool:
        """Deletes a plate.

        Raises
        ------
        ValueError
            If runs are still stored on the plate.
        """