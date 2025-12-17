from __future__ import annotations
from abc import abstractmethod, ABC

from typing import List, Literal
from deprecated import deprecated

from config.models.maintenance import MaintenanceInsertModel, MaintenanceBaseModel, MaintenanceEventInsertModel, MaintenanceEventModel, MaintenanceStateResponseModel, MaintenanceProcedureResponseModel, ExternalServiceInsertModel, ExternalServiceModel #, InstrumentMaintenanceModel


class MaintenanceEventABC(ABC):

    @abstractmethod
    def _utils_insert_maintenance_state_from_file(self, path_to_file : str, *args, **kwargs):
        """Handles the insertion of multiple maintenance events using a file.
        The arguments and kwargs should be passed to pandas.read_csv
        """

    @abstractmethod
    def count(self, instrument_tag : str = None, user_tag : str = None, timestamp_min : float = None, timestamp_max : float = None) -> int:
        """Count the number of maintenance events given by the range (instrument, timestamp, users
        """
        

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
            If the given tag is associated with a maintenance event. 
        """
    @abstractmethod
    def find(self, instrument_tag : str = None, user_tag : str = None, timestamp_min : float = None, timestamp_max : float = None, limit : int = 50, order_by_time : bool = True) -> List[str]:
        """
        Finds maintenance events by instrument_tag and user_tag.
        
        Parameters
        ----------
        instrument_tag : str, optional
            The tag of the instrument, by default None
        user_tag : str, optional
            The tag of the user, by default None
        timestamp_min : float, optional
            The minimum timestamp to filter the events, by default None 
        timestamp_max : float, optional     
            The maximum timestamp to filter the events, by default None
        limit : int, optional
            The maximum number of results to return, by default 50
        order_by_time : bool, optional      
            If True, the results are ordered by time, by default True
        
        Returns
        -------
        List[str]
            A list of maintenance events tags.
        """

    @abstractmethod
    def costs(self, instrument_tag  : str = None, timestamp_min : float = None, timestamp_max : float = None) -> float:
        """Calculate the costs for maintenance event. Either for a specific instrument
        or the total costs. 

        Parameters
        ----------
        instrument_tag  : str, optional
            Instrument tag to get the specific instrument costs, by default None
        timestamp_min : float, optional
            Minimum timestamp to filter the costs, by default None 
        timestamp_max : float, optional
            Maximum timestamp to filter the costs, by default None
            
        Returns
        -------
        float
            The costs per given instrument, or the total costs if tag is None (default) in 
            the given time range.
        """

    @abstractmethod
    def get(self, tag : str = None) -> MaintenanceEventModel|List[MaintenanceEventModel]|None:
        """Returns maintenance events by tag

        Parameters
        ----------
        tag : str, optional
            List of maintenance events to retrieve from the database. 
            If a tag does not exists, it is simply ignored. 
        """



    @abstractmethod
    def set_state(self, tag : str, state_tag : str, user_tag : str = None, description : str = None) -> str|None:
        """Sets the state of a maintenance event. 

        Parameters
        ----------
        tag : str
            The tag of the maintenance event to set the state for.
        state_tag : str
            The tag of the state to set.
        user_tag : str, optional
            The user who sets the state, by default None
        description : str, optional
            A description for the state change, by default None

        Returns
        -------
        str|None
            The tag of the maintenance event if successful, None otherwise.
        """
    @abstractmethod
    def get_states(self) -> List[MaintenanceStateResponseModel]:
        """Returns a list of all maintenance states.
        
        Returns
        -------
        List[MaintenanceStateResponseModel]
            A list of maintenance state tags.
        """
         
    
    @abstractmethod
    def insert(self, maintenance_event : MaintenanceEventInsertModel):
        "Insert a new maintenance event. "


    @abstractmethod
    def get_costs_per_event(self, tag : str) -> float:
        """
        Returns the costs of a maintenance event by its tag.
        """
        
        
class MaintenanceProcedureABC(ABC):


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
    def get(self, tag : str = None) -> MaintenanceBaseModel:
        """Returns the  maintenance entries matching the tag

        Parameters
        ----------
        tag : str
            maintenance tag 

        Returns
        -------
        List[InstrumentModel]
            
        """
    
    @abstractmethod
    def get_text(self, tag : str) -> str:
        """Get maintenance texts by its tag. 

        Parameters
        ----------
            The maintenance tag.

        Returns
        -------
        [str]
            The maintenance text.
        """

    @abstractmethod
    def get_description(self, tag : str) -> str:
        """Get maintenance descriptions by its tag. 

        Parameters
        ----------
          The maintenance tag.

        Returns
        -------
        [str]
            The maintenance description.
        """
    
    @abstractmethod
    def get_priority(self, tag : str) -> int:
        """Get maintenance priorities by its tag. 

        Parameters
        ----------
          The maintenance tag.

        Returns
        -------
        int
            The maintenance priority.
        """ 
        
    @abstractmethod
    def find(self, search_string : str, limit : int = 50) -> List[MaintenanceBaseModel]:
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

    @abstractmethod
    def update(self, procedure :  MaintenanceProcedureResponseModel, user_tag : str) -> bool:
        """Updates a maintenance procedure in the database.

        Parameters
        ----------
        procedure : MaintenanceProcedureResponseModel
            The procedure to update.
        user_tag : str
            The user who updates the procedure.

        Returns
        -------
        bool
            True if the procedure was updated successfully, False otherwise.
        """
        
    @abstractmethod
    def delete(self, tag : str, user_tag : str) -> bool:
        """Deletes a maintenance procedure from the database.

        Parameters
        ----------
        tag : str
            The tag of the procedure to delete.
        user_tag : str
            The user who deletes the procedure.

        Returns
        -------
        bool
            True if the procedure was deleted successfully, False otherwise.
        """
        

class ExternalServicesABC(ABC):
    """
    Abstract Base Class for external maintenance services.

    Ann ExternalService represents an third-party company or person that 
    performs maintenance on an instrument. 
    """
    
    @abstractmethod
    def exists(self, tag: str) -> bool:
        """
        Check if a mainteance service with the given tag exists.

         Parameters
        ----------
        tag : str
            The service tag.

        Returns
        -------
        bool
            True if the service exists, otherwise False.
        """

    @abstractmethod
    def get(self, tag: str) -> ExternalServiceModel:
        """
        Get the complete external service model.

        Parameters
        ----------
        tag : str
            The maintenance service tag.
            The model containing all required fields for creating a maintenance service.

        Returns
        -------
       ExternalServiceModel
            A model containing all maintenance service data.
        """

    @abstractmethod
    def insert(self, service: ExternalServiceInsertModel, user_tag : str, is_active : bool = True) -> bool:
        """
        Inserts a new external maintenance service. 

        Parameters
        ----------
        service : ExternalServiceInsertModel
                        The model containing all required fields for creating a external service.

         Returns
        -------
        bool
            True if the insertion was successful, otherwise False.
        """
    
    @abstractmethod
    def delete(self, tag : str, is_active : bool = False) -> bool:
        """
        Delete a external service from the database.

        Parameters
        ----------
        tag : str
           The service tag.

        Returns
        -------
        bool
           True if the deletion was successful, otherwise False.
        """
    
    @abstractmethod
    def update(self, service: ExternalServiceModel, user_tag: str = None) -> bool:
        """
        Update an existing external service in the database.

        Parameters
        ----------
        tag : str
            The service tag to be updated.
        service: ExternalServiceModel
            Model containing updated field values.

        Returns
        -------
        bool
            True if the update was successful.
        """


    @abstractmethod
    def get_description(self, tag: str) -> str:
        """
        Get the description of the service by its tag. 

        Parameters
        ----------
        tag : str
            The service tag.

        Returns
        -------
        str
            The description of the external service.
        """

    @abstractmethod
    def get_name(self, tag: str) -> str:
        """
        Get the name of the person that provided the service by its tag.

        Parameters
        ----------
        tag : str
            The servicce tag.

        Returns
        -------
        str
            The person's name.
        """

    @abstractmethod
    def get_company(self, tag: str) -> str:
        """
        Get the company name providing the service.

        Parameters
        ----------
        tag : str
            The service tag.

        Returns
        -------
        str
            The company name.
        """

    @abstractmethod
    def get_email(self, tag: str) -> str:
        """
        Get the contact person's email address. 

        Parameters
        ----------
        tag : str
           The service tag. 

        Returns
        -------
        str
            Email address.
        """

    @abstractmethod
    def get_cost(self, tag: str) -> float | int:
        """
        Get cost of the service

        Parameters
        ----------
        tag : str
           The service tag. 

        Returns
        -------
        float | int
            Cost of the service
        """

    @abstractmethod
    def get_billing_number(self, tag: str) -> str:
        """
        Get the billing or invoice number. 

        Parameters
        ----------
        tag : str
           The service tag. 

        Returns
        -------
        str
           The billing or invoice number
        """

    @abstractmethod
    def get_internal_id(self, tag: str) -> str:
        """
        Get Internal ID for the service. 
        
        Parameters
        ----------
        tag : str
            The service tag. 

        Returns
        -------
        str
           Internal ID 
        """