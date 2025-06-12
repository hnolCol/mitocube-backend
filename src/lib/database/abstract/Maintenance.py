from __future__ import annotations
from abc import abstractmethod, ABC

from typing import List, Literal
from deprecated import deprecated

from config.models.maintenance import MaintenanceInsertModel, MaintenanceBaseModel, MaintenanceEventInsertModel #, InstrumentMaintenanceModel


class MaintenanceEventABC(ABC):


    @abstractmethod
    def exists(self, tag : str) -> bool:
        """Checks if the maintenance event exists. 

        Parameters
        ----------
        tag : str
            _description_

        Returns
        -------
        bool
            If the given tag is associated with a maintenancen event. 
        """
        

    @abstractmethod
    def get(self, tags : List[str]):
        """Returns maintenance events by tag

        Parameters
        ----------
        tags : List[str]
            List of maintenance events to retrieve from the database. 
            If a tag does not exists, it is simply ignored. 
        """

    
    @abstractmethod
    def insert(self, maintenance_event : MaintenanceEventInsertModel):
        "Insert a new maintenance event. "


        
class MaintenanceABC(ABC):


    @abstractmethod
    def _utils_insert_from_file(path_to_file : str, *args, **kwargs):
        """
        Handles the insertion of multiple maintenance entries using a file. 
        The arguments and kwargs should be passed to pandas.read_csv
        """
        
    # @abstractmethod
    # def insert_maintenance_event(self, tags : str, instrument_tag : str, user_tag : str, costs : float, description : str):
    #     """Inserts a maintenance event, linking the event to an instrument. In addition the Event is described by a set of 
    #     maintenance events (tags)

    #     Parameters
    #     ----------
    #     tags : List[str]
    #         The maintenance tags linked to the maintenance event
    #     instrument_tag : str
    #         The instrument tag
    #     user_tag : str
    #         The user tag that created the maintenance event 
    #     costs : float
    #         The total costs for this maintenance event in the defined currency (see config).
    #     """

    @abstractmethod
    def count(self) -> int:
        "Returns the number of maintenance entries in the database."
        

    @abstractmethod
    def costs(self, instrument_tag  : str = None) -> float:
        """Calculate the costs for maintenance. Either for a specific instrument
        or the total costs. 

        Parameters
        ----------
        instrument_tag  : str, optional
            Instrument tag to get the specific instrument costs, by default None

        Returns
        -------
        float
            The costs per given instrument, or the total costs if tag is None (default)
        """

    @abstractmethod 
    def exists(self, tag : str) -> bool:
        """Checks if a tag is associated with a maintenance.

        Parameters
        ----------
        tag : str
            The tag to check

        Returns
        -------
        bool
            If the tag is associated with a maintenance in the database. 
        """
        
    @abstractmethod
    def history(self, 
                instrument_tag : str = None, 
                limit : int = 50, 
                sort_by : str = Literal["costs", "timestamp"], 
                descending : bool = True) -> List:
        """Maintenance hinstory either for a specific instrument or for all instruments. 

        Parameters
        ----------
        instrument_tag : str, optional
            Tag associated with an instrument, by default None
        limit : int, optional
            The maximum number of history entries to be returned, by default 50

        Returns
        -------
        List[InstrumentMaintenanceModel]
            Sorted list (desc timestamp) of the maintenance
        """
            
    @abstractmethod
    def insert(self, maintenace : MaintenanceInsertModel):
        """Adds a maintenance to the database 

        Parameters
        ----------
        maintenace : MaintenanceInsertModel
            _description_
        """

    @abstractmethod 
    def get(self, tags : List[str] = None) -> List[MaintenanceBaseModel]:
        """Returns the  maintenance entries matching the tags

        Parameters
        ----------
        tags : List[str]
            List of instrument tags, defaults to None. If None then
            all available maintenance will be returned. 

        Returns
        -------
        List[InstrumentModel]
            
        """
        
        
    @abstractmethod
    def find(self, query : str, limit : int = 50) -> List[MaintenanceBaseModel]:
        """Finds a maintenance by a query. The
        query happens in the attribute 's' (search) which
        is a combined search string in only lower cases. See
        insert method. 
        The query is transformed to .lower(). 

        Parameters
        ----------
        query : str
            The search string 
        limit : int 
            The maximum maintenance entries to return 

        Returns
        -------
        List[str]
            The list of maintenances that are found. 
        """
        
