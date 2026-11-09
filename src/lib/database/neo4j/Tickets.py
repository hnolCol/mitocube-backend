import secrets
from typing import List, Optional

from neo4j import Driver, Result
from neo4j.exceptions import ConstraintError

from lib.database.abstract.Tickets import TicketsABC
from config.models.tickets import TicketInput, TicketModel, TicketCreatedResponse, TicketStatusEnum
from services.random_generators import get_random_string

# The uniqueness constraints for Ticket.tag and Ticket.reference are created by
# src/migration/create_ticket_constraints.py:
#   PYTHONPATH=src python -m migration.create_ticket_constraints

_TICKET_RETURN = (
    "OPTIONAL MATCH (a:User)-[:HANDLES]->(t) "
    "OPTIONAL MATCH (t)-[:HAS_CONVERSATION]->(c:Conversation) "
    "OPTIONAL MATCH (c)<-[:IN_CONVERSATION]-(m:Message) "
    "WITH u, t, a, c, m ORDER BY m.created_at DESC "
    "WITH u, t, a, c, head(collect(m)) AS last_message "
    "RETURN t.tag AS tag, t.reference AS reference, t.title AS title, "
    "t.description AS description, t.status AS status, t.created_at AS created_at, "
    "t.updated_at AS updated_at, u.tag AS raised_by, c.tag AS conversation_tag, "
    "trim(coalesce(u.firstname, '') + ' ' + coalesce(u.lastname, '')) AS raised_by_name, "
    "a.tag AS assigned_to, "
    "CASE WHEN a IS NULL THEN NULL ELSE trim(coalesce(a.firstname, '') + ' ' + coalesce(a.lastname, '')) END AS assigned_to_name, "
    "last_message.created_at AS last_message_at, "
    "coalesce(c IS NULL OR last_message.sender_tag = u.tag, false) AS awaiting_reply "
)


class Neo4JTickets(TicketsABC):

    def __init__(self, driver : Driver) -> None:
        self._driver = driver

    def _to_models(self, rows) -> List[TicketModel]:
        return [TicketModel(**row) for row in rows]

    def insert_ticket(self, user_tag : str, ticket : TicketInput) -> Optional[TicketCreatedResponse]:
        """Creates a ticket only. No conversation or message is created until an admin replies.
        The reference is a random 6-digit number; uniqueness is enforced by the
        ticket_reference constraint and retried on collision."""
        query = (
            "MATCH (u:User {tag : $user_tag}) "
            "CREATE (t:Ticket {tag : $ticket_tag, reference : $reference, title : $title, "
            "description : $description, status : $status, "
            "created_at : timestamp(), updated_at : timestamp()}) "
            "MERGE (u)-[:RAISED]->(t) "
            "RETURN t.tag AS tag, t.reference AS reference "
        )
        for _ in range(5):
            try:
                r = self._driver.execute_query(query, routing_="w",
                                               user_tag = user_tag,
                                               ticket_tag = get_random_string(N = 12),
                                               reference = f"TIC-{secrets.randbelow(10**6):06d}",
                                               title = ticket.title.strip(),
                                               description = ticket.description.strip(),
                                               status = TicketStatusEnum.OPEN.value,
                                               result_transformer_=Result.data)
                return TicketCreatedResponse(**r[0]) if len(r) > 0 else None
            except ConstraintError:
                continue
        return None

    def get_ticket(self, ticket_tag : str) -> Optional[TicketModel]:
        query = "MATCH (u:User)-[:RAISED]->(t:Ticket {tag : $ticket_tag}) " + _TICKET_RETURN
        r = self._driver.execute_query(query, ticket_tag = ticket_tag, result_transformer_=Result.data)
        return TicketModel(**r[0]) if len(r) > 0 else None

    def get_tickets(self, status : Optional[TicketStatusEnum] = None) -> List[TicketModel]:
        query = (
            "MATCH (u:User)-[:RAISED]->(t:Ticket) "
            "WHERE $status IS NULL OR t.status = $status "
        ) + _TICKET_RETURN + (
            "ORDER BY CASE WHEN awaiting_reply AND status <> 'Resolved' THEN 0 ELSE 1 END, "
            "CASE status WHEN 'Open' THEN 0 WHEN 'In Progress' THEN 1 ELSE 2 END, "
            "coalesce(last_message_at, updated_at) DESC "
        )
        r = self._driver.execute_query(query, routing_="r",
                                       status = status.value if status else None,
                                       result_transformer_=Result.data)
        return self._to_models(r)

    def get_tickets_for_user(self, user_tag : str) -> List[TicketModel]:
        query = "MATCH (u:User {tag : $user_tag})-[:RAISED]->(t:Ticket) " + _TICKET_RETURN + \
                "ORDER BY coalesce(last_message_at, updated_at) DESC "
        r = self._driver.execute_query(query, routing_="r", user_tag = user_tag,
                                       result_transformer_=Result.data)
        return self._to_models(r)

    def link_conversation(self, ticket_tag : str, conversation_tag : str) -> bool:
        query = (
            "MATCH (t:Ticket {tag : $ticket_tag}) "
            "MATCH (c:Conversation {tag : $conversation_tag}) "
            "MERGE (t)-[:HAS_CONVERSATION]->(c) "
            "SET t.updated_at = timestamp() "
            "RETURN count(c) "
        )
        r = self._driver.execute_query(query, routing_="w", ticket_tag = ticket_tag,
                                       conversation_tag = conversation_tag,
                                       result_transformer_=Result.value)
        return len(r) > 0 and r[0] > 0

    def assign(self, ticket_tag : str, admin_tag : str) -> bool:
        """Makes the admin the handler of the ticket if nobody handles it yet.
        Returns True if the admin is (now) the handler."""
        query = (
            "MATCH (t:Ticket {tag : $ticket_tag}) "
            "MATCH (a:User {tag : $admin_tag}) "
            "OPTIONAL MATCH (other:User)-[:HANDLES]->(t) "
            "WITH t, a, other "
            "FOREACH (_ IN CASE WHEN other IS NULL THEN [1] ELSE [] END | "
            "    MERGE (a)-[:HANDLES]->(t)) "
            "RETURN other IS NULL OR other.tag = $admin_tag "
        )
        r = self._driver.execute_query(query, routing_="w", ticket_tag = ticket_tag,
                                       admin_tag = admin_tag, result_transformer_=Result.value)
        return bool(r[0]) if len(r) > 0 else False

    def set_status(self, ticket_tag : str, status : TicketStatusEnum) -> bool:
        query = (
            "MATCH (t:Ticket {tag : $ticket_tag}) "
            "SET t.status = $status, t.updated_at = timestamp() "
            "RETURN count(t) "
        )
        r = self._driver.execute_query(query, routing_="w", ticket_tag = ticket_tag,
                                       status = status.value, result_transformer_=Result.value)
        return len(r) > 0 and r[0] > 0

    def reopen_by_conversation(self, conversation_tag : str, user_tag : str) -> None:
        """If the ticket raiser replies in a resolved ticket's conversation, reopen it."""
        query = (
            "MATCH (u:User {tag : $user_tag})-[:RAISED]->(t:Ticket)-[:HAS_CONVERSATION]->"
            "(:Conversation {tag : $conversation_tag}) "
            "SET t.updated_at = timestamp(), "
            "t.status = CASE WHEN t.status = 'Resolved' THEN 'Open' ELSE t.status END "
        )
        self._driver.execute_query(query, routing_="w", user_tag = user_tag,
                                   conversation_tag = conversation_tag)