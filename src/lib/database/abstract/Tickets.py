from abc import ABC, abstractmethod
from typing import List, Optional
from config.models.tickets import (
    TicketAttachmentModel,
    TicketInput,
    TicketModel,
    TicketCreatedResponse,
    TicketStatusEnum,
)


class TicketsABC(ABC):

    @abstractmethod
    def insert_ticket(self, user_tag : str, ticket : TicketInput) -> Optional[TicketCreatedResponse]: 
        """Inserts a new ticket into the database and returns the created ticket's tag and reference."""

    @abstractmethod
    def get_ticket(self, ticket_tag : str) -> Optional[TicketModel]: 
        """Retrieves a ticket by its tag. Returns None if the ticket does not exist."""

    @abstractmethod
    def get_tickets(self, status : Optional[TicketStatusEnum] = None) -> List[TicketModel]: 
        """Retrieves a list of tickets, optionally filtered by status."""

    @abstractmethod
    def get_tickets_for_user(self, user_tag : str) -> List[TicketModel]: 
        """Retrieves a list of tickets raised by a specific user."""

    @abstractmethod
    def link_conversation(self, ticket_tag : str, conversation_tag : str) -> bool: 
        """Links a conversation to a ticket. Returns True if successful, False otherwise."""

    @abstractmethod
    def assign(self, ticket_tag : str, admin_tag : str) -> bool: 
        """Assigns an admin to a ticket. Returns True if successful, False otherwise."""

    @abstractmethod
    def set_status(self, ticket_tag : str, status : TicketStatusEnum) -> bool:
        """Sets the status of a ticket. Returns True if successful, False otherwise."""

    @abstractmethod
    def reopen_by_conversation(self, conversation_tag : str, user_tag : str) -> None: 
        """Reopens a ticket based on a conversation. This is typically called when a user replies to a conversation linked to a ticket."""

    @abstractmethod
    def insert_attachment(self, ticket_tag : str, attachment_tag : str, uploaded_by : str,
                          filename : str, content_type : str, size : int,
                          extension : str) -> Optional[TicketAttachmentModel]:
        """Stores the metadata of an uploaded ticket attachment and links it to the ticket
        and the uploading user. Returns the created attachment or None if ticket/user do not exist."""

    @abstractmethod
    def get_attachment(self, attachment_tag : str) -> Optional[TicketAttachmentModel]:
        """Retrieves an attachment by its tag, including the tag of the ticket it belongs to.
        Returns None if the attachment does not exist."""

    @abstractmethod
    def get_attachments_for_ticket(self, ticket_tag : str) -> List[TicketAttachmentModel]:
        """Retrieves all attachments of a ticket, oldest first."""