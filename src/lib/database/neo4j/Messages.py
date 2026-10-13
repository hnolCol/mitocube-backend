from typing import List, Optional

from neo4j import Driver, Result

from lib.database.abstract.Messages import MessagesABC
from config.models.messages import (
    ConversationInput,
    ConversationModel,
    ConversationResponseModel,
    MessageInput,
    MessageModel,
)
from services.random_generators import get_random_string


class Neo4JMessages(MessagesABC):

    def __init__(self, driver : Driver) -> None:
        self._driver = driver

    def _all_participants_exist(self, user_tags : List[str]) -> bool:
        query = (
            "UNWIND $user_tags AS user_tag "
            "MATCH (u:User {tag : user_tag}) "
            "RETURN count(u) AS n "
        )
        r = self._driver.execute_query(query, user_tags = user_tags, result_transformer_=Result.value)
        return len(r) > 0 and r[0] == len(set(user_tags))

    def insert_conversation(self, created_by : str, conversation : ConversationInput) -> Optional[str]:
        """Creates a conversation with the given participants, optionally linked
        to a submission. All participants must exist. The creator is implicitly a
        participant even if not included in user_tags."""
        if not self._all_participants_exist(conversation.user_tags):
            return None
        if not self._all_participants_exist([created_by]):
            return None
        participants = list(set(conversation.user_tags + [created_by]))

        conversation_tag = get_random_string(N = 12)
        query = (
            "CREATE (c:Conversation {tag : $conversation_tag, created_at : timestamp(), "
            "created_by : $created_by, title : $title, submission_tag : $submission_tag}) "
            "WITH c "
            "UNWIND $participants AS participant_tag "
            "MATCH (u:User {tag : participant_tag}) "
            "MERGE (u)-[r:PARTICIPATES]->(c) "
            "ON CREATE SET r.created_at = timestamp() "
            "WITH c "
            "RETURN c.tag "
        )
        r = self._driver.execute_query(query, routing_="w",
                                       conversation_tag = conversation_tag,
                                       created_by = created_by,
                                       title = conversation.title,
                                       submission_tag = conversation.submission_tag,
                                       participants = participants,
                                       result_transformer_=Result.value)
        if len(r) == 0:
            return None

        if conversation.submission_tag is not None:
            link_query = (
                "MATCH (c:Conversation {tag : $conversation_tag}) "
                "MATCH (s:Submission {tag : $submission_tag}) "
                "MERGE (c)-[:ABOUT_SUBMISSION]->(s) "
            )
            self._driver.execute_query(link_query, routing_="w",
                                       conversation_tag = conversation_tag,
                                       submission_tag = conversation.submission_tag)

        if conversation.initial_message:
            message_input = MessageInput(content = conversation.initial_message)
            self.insert_message(conversation_tag = conversation_tag, sender_tag = created_by,
                                message = message_input)
        return conversation_tag

    def exists(self, conversation_tag : str) -> bool:
        query = "RETURN EXISTS { (c:Conversation {tag : $conversation_tag})} "
        r = self._driver.execute_query(query, conversation_tag = conversation_tag, result_transformer_=Result.value)
        return r[0] if len(r) > 0 else False

    def get_conversation(self, conversation_tag : str) -> Optional[ConversationModel]:
        query = (
            "MATCH (c:Conversation {tag : $conversation_tag}) "
            "OPTIONAL MATCH (u:User)-[:PARTICIPATES]->(c) "
            "OPTIONAL MATCH (c)-[:ABOUT_SUBMISSION]->(s:Submission) "
            "RETURN c.tag AS tag, c.created_at AS created_at, c.created_by AS created_by, "
            "c.title AS title, s.tag AS submission_tag, collect(u.tag) AS user_tags "
        )
        r = self._driver.execute_query(query, conversation_tag = conversation_tag, result_transformer_=Result.data)
        if len(r) == 0: return None
        row = r[0]
        return ConversationModel(tag = row["tag"], created_at = row["created_at"],
                                 created_by = row["created_by"],
                                 user_tags = [t for t in row["user_tags"] if t is not None],
                                 submission_tag = row.get("submission_tag"),
                                 title = row.get("title"))

    def get_conversations_for_user(self, user_tag : str, submission_tag : str = None) -> List[ConversationResponseModel]:
        """Returns all conversations of the given user, optionally filtered by
        the linked submission, ordered by the latest message (newest first)."""
        query = (
            "MATCH (u:User {tag : $user_tag})-[:PARTICIPATES]->(c:Conversation) "
        )
        params = {"user_tag" : user_tag}
        if submission_tag is not None:
            query += "MATCH (c)-[:ABOUT_SUBMISSION]->(s:Submission {tag : $submission_tag}) "
            params["submission_tag"] = submission_tag
        query += (
            "OPTIONAL MATCH (c)<-[:PARTICIPATES]-(p:User) "
            "WITH c, collect(p.tag) AS participants "
            "OPTIONAL MATCH (c)-[:ABOUT_SUBMISSION]->(s:Submission) "
            "WITH c, participants, s "
            "OPTIONAL MATCH (c)<-[:IN_CONVERSATION]-(m:Message) "
            "WITH c, participants, s, m "
            "ORDER BY m.created_at DESC "
            "WITH c, participants, s, head(collect(m)) AS last_message, count(m) AS n_messages "
            "RETURN c.tag AS tag, c.created_at AS created_at, c.created_by AS created_by, c.title AS title, "
            "s.tag AS submission_tag, participants AS user_tags, "
            "last_message.created_at AS last_message_at, n_messages AS n_messages, "
            "last_message.content AS last_message, "
            "EXISTS { MATCH (c)<-[:IN_CONVERSATION]-(m2:Message) WHERE NOT $user_tag IN m2.read_by AND m2.sender_tag <> $user_tag } AS unread "
        )
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.data, **params)
        results = []
        for row in r:
            results.append(ConversationResponseModel(
                tag = row["tag"],
                created_at = row["created_at"],
                created_by = row["created_by"],
                user_tags = [t for t in row["user_tags"] if t is not None],
                submission_tag = row.get("submission_tag"),
                title = row.get("title"),
                last_message_at = row.get("last_message_at"),
                n_messages = row.get("n_messages", 0),
                unread = bool(row.get("unread", False)),
                last_message = row.get("last_message"),
            ))
        return results

    def get_conversations_for_submission(self, submission_tag : str) -> List[ConversationModel]:
        query = (
            "MATCH (c:Conversation)-[:ABOUT_SUBMISSION]->(s:Submission {tag : $submission_tag}) "
            "OPTIONAL MATCH (u:User)-[:PARTICIPATES]->(c) "
            "RETURN c.tag AS tag, c.created_at AS created_at, c.created_by AS created_by, "
            "c.title AS title, s.tag AS submission_tag, collect(u.tag) AS user_tags "
        )
        r = self._driver.execute_query(query, submission_tag = submission_tag, result_transformer_=Result.data)
        return [ConversationModel(tag = row["tag"], created_at = row["created_at"],
                                  created_by = row["created_by"],
                                  user_tags = [t for t in row["user_tags"] if t is not None],
                                  submission_tag = row.get("submission_tag"),
                                  title = row.get("title")) for row in r]

    def is_participant(self, conversation_tag : str, user_tag : str) -> bool:
        query = (
            "MATCH (u:User {tag : $user_tag})-[:PARTICIPATES]->(c:Conversation {tag : $conversation_tag}) "
            "RETURN count(u) "
        )
        r = self._driver.execute_query(query, user_tag = user_tag, conversation_tag = conversation_tag,
                                       result_transformer_=Result.value)
        return r[0] > 0 if len(r) > 0 else False

    def insert_message(self, conversation_tag : str, sender_tag : str, message : MessageInput) -> Optional[str]:
        """Adds a message to a conversation. The message is linked to the sender
        and the conversation and starts with the sender in read_by."""
        if not self.exists(conversation_tag):
            return None
        message_tag = get_random_string(N = 12)
        query = (
            "MATCH (c:Conversation {tag : $conversation_tag}) "
            "MATCH (u:User {tag : $sender_tag}) "
            "CREATE (m:Message {tag : $message_tag, created_at : timestamp(), "
            "content : $content, sender_tag : $sender_tag, read_by : [$sender_tag]}) "
            "MERGE (m)-[:IN_CONVERSATION]->(c) "
            "MERGE (u)-[:SENT]->(m) "
            "RETURN m.tag "
        )
        r = self._driver.execute_query(query, routing_="w",
                                       conversation_tag = conversation_tag,
                                       sender_tag = sender_tag,
                                       message_tag = message_tag,
                                       content = message.content,
                                       result_transformer_=Result.value)
        if len(r) == 0:
            return None
        return message_tag

    def get_messages(self, conversation_tag : str, limit : int = None) -> List[MessageModel]:
        query = (
            "MATCH (m:Message)-[:IN_CONVERSATION]->(c:Conversation {tag : $conversation_tag}) "
            "RETURN m.tag AS tag, m.created_at AS created_at, m.sender_tag AS sender_tag, "
            "m.content AS content, m.read_by AS read_by "
            "ORDER BY m.created_at ASC "
        )
        params = {"conversation_tag" : conversation_tag}
        if limit is not None:
            query += "LIMIT $limit "
            params["limit"] = limit
        r = self._driver.execute_query(query, routing_="r", result_transformer_=Result.data, **params)
        return [MessageModel(tag = row["tag"], created_at = row["created_at"],
                             sender_tag = row["sender_tag"], content = row["content"],
                             read_by = row.get("read_by") or []) for row in r]

    def mark_read(self, conversation_tag : str, user_tag : str) -> bool:
        """Marks all messages of the conversation as read for the given user
        (messages sent by other users)."""
        query = (
            "MATCH (m:Message)-[:IN_CONVERSATION]->(c:Conversation {tag : $conversation_tag}) "
            "WHERE m.sender_tag <> $user_tag AND NOT $user_tag IN m.read_by "
            "SET m.read_by = coalesce(m.read_by, []) + [$user_tag] "
            "RETURN count(m) "
        )
        r = self._driver.execute_query(query, routing_="w",
                                       conversation_tag = conversation_tag,
                                       user_tag = user_tag,
                                       result_transformer_=Result.value)
        return r[0] >= 0 if len(r) > 0 else False

    def get_unread_count(self, conversation_tag : str, user_tag : str) -> int:
        query = (
            "MATCH (m:Message)-[:IN_CONVERSATION]->(c:Conversation {tag : $conversation_tag}) "
            "WHERE m.sender_tag <> $user_tag AND NOT $user_tag IN m.read_by "
            "RETURN count(m) "
        )
        r = self._driver.execute_query(query, conversation_tag = conversation_tag, user_tag = user_tag,
                                       result_transformer_=Result.value)
        return r[0] if len(r) > 0 else 0
