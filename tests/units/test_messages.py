import pytest

from config.models.messages import ConversationInput, MessageInput, ConversationModel


class FakeMessagesDB:
    """Minimal in-memory implementation of the message system."""
    def __init__(self, users=None):
        self.users = users or set()
        self.conversations = {}     # tag -> ConversationModel
        self.messages = {}          # conversation_tag -> [dict]
        self.submission_links = {}  # conversation_tag -> submission_tag

    def _all_participants_exist(self, user_tags):
        return all(u in self.users for u in user_tags)

    def insert_conversation(self, created_by, conversation):
        if not self._all_participants_exist(conversation.user_tags + [created_by]):
            return None
        tag = f"conv-{len(self.conversations) + 1}"
        self.conversations[tag] = ConversationModel(
            tag=tag, created_by=created_by,
            user_tags=list(set(conversation.user_tags + [created_by])),
            submission_tag=conversation.submission_tag,
            title=conversation.title)
        if conversation.submission_tag:
            self.submission_links[tag] = conversation.submission_tag
        if conversation.initial_message:
            self.insert_message(tag, created_by, MessageInput(content=conversation.initial_message))
        return tag

    def exists(self, conversation_tag):
        return conversation_tag in self.conversations

    def get_conversation(self, conversation_tag):
        return self.conversations.get(conversation_tag)

    def is_participant(self, conversation_tag, user_tag):
        conv = self.conversations.get(conversation_tag)
        return conv is not None and user_tag in conv.user_tags

    def insert_message(self, conversation_tag, sender_tag, message):
        if conversation_tag not in self.conversations:
            return None
        self.messages.setdefault(conversation_tag, []).append(
            {"sender_tag": sender_tag, "content": message.content, "read_by": [sender_tag]})
        return f"msg-{len(self.messages[conversation_tag])}"

    def add_participants(self, conversation_tag, user_tags):
        if conversation_tag not in self.conversations:
            return False
        if not all(u in self.users for u in user_tags):
            return False
        conv = self.conversations[conversation_tag]
        for u in user_tags:
            if u not in conv.user_tags:
                conv.user_tags.append(u)
        return True

    def get_messages(self, conversation_tag, limit=None):
        msgs = self.messages.get(conversation_tag, [])
        return msgs if limit is None else msgs[:limit]

    def get_unread_count(self, conversation_tag, user_tag):
        return sum(1 for m in self.messages.get(conversation_tag, [])
                   if m["sender_tag"] != user_tag and user_tag not in m["read_by"])

    def mark_read(self, conversation_tag, user_tag):
        for m in self.messages.get(conversation_tag, []):
            if user_tag not in m["read_by"]:
                m["read_by"].append(user_tag)
        return True


class TestConversationCreation:

    def test_create_conversation_with_submission_link(self):
        db = FakeMessagesDB(users={"owner-1", "user-1"})
        tag = db.insert_conversation(
            created_by="user-1",
            conversation=ConversationInput(user_tags=["owner-1"], submission_tag="subm-1",
                                           initial_message="Hello!"))
        assert tag is not None
        assert db.submission_links[tag] == "subm-1"
        assert len(db.get_messages(tag)) == 1

    def test_create_conversation_without_submission(self):
        db = FakeMessagesDB(users={"a", "b"})
        tag = db.insert_conversation(created_by="a", conversation=ConversationInput(user_tags=["b"]))
        assert tag is not None
        assert db.get_conversation(tag).submission_tag is None

    def test_unknown_participant_returns_none(self):
        db = FakeMessagesDB(users={"a"})
        tag = db.insert_conversation(created_by="a", conversation=ConversationInput(user_tags=["ghost"]))
        assert tag is None

    def test_creator_is_participant(self):
        db = FakeMessagesDB(users={"a", "b"})
        tag = db.insert_conversation(created_by="a", conversation=ConversationInput(user_tags=["b"]))
        assert db.is_participant(tag, "a") is True
        assert db.is_participant(tag, "b") is True
        assert db.is_participant(tag, "c") is False


class TestMessaging:

    def test_message_order_and_content(self):
        db = FakeMessagesDB(users={"a", "b"})
        tag = db.insert_conversation(created_by="a", conversation=ConversationInput(user_tags=["b"]))
        db.insert_message(tag, "a", MessageInput(content="hi"))
        db.insert_message(tag, "b", MessageInput(content="hello"))
        msgs = db.get_messages(tag)
        assert [m["content"] for m in msgs] == ["hi", "hello"]

    def test_message_to_unknown_conversation_returns_none(self):
        db = FakeMessagesDB(users={"a"})
        assert db.insert_message("nope", "a", MessageInput(content="x")) is None

class TestAddParticipants:

    def test_participant_can_invite_more_users(self):
        db = FakeMessagesDB(users={"a", "b", "c", "d"})
        tag = db.insert_conversation(created_by="a", conversation=ConversationInput(user_tags=["b"]))
        assert db.add_participants(tag, ["c", "d"]) is True
        conv = db.get_conversation(tag)
        assert set(conv.user_tags) == {"a", "b", "c", "d"}

    def test_invite_duplicate_participant_is_idempotent(self):
        db = FakeMessagesDB(users={"a", "b"})
        tag = db.insert_conversation(created_by="a", conversation=ConversationInput(user_tags=["b"]))
        assert db.add_participants(tag, ["b"]) is True
        assert set(db.get_conversation(tag).user_tags) == {"a", "b"}

    def test_invite_unknown_user_fails(self):
        db = FakeMessagesDB(users={"a", "b"})
        tag = db.insert_conversation(created_by="a", conversation=ConversationInput(user_tags=["b"]))
        assert db.add_participants(tag, ["ghost"]) is False

    def test_invite_to_unknown_conversation_fails(self):
        db = FakeMessagesDB(users={"a"})
        assert db.add_participants("nope", ["a"]) is False

    def test_invited_participant_gains_message_access(self):
        db = FakeMessagesDB(users={"a", "b", "c"})
        tag = db.insert_conversation(created_by="a", conversation=ConversationInput(user_tags=["b"]))
        db.add_participants(tag, ["c"])
        assert db.is_participant(tag, "c") is True
        db.insert_message(tag, "a", MessageInput(content="hi all"))
        assert db.get_unread_count(tag, "c") == 1

    def test_unread_and_mark_read(self):
        db = FakeMessagesDB(users={"a", "b"})
        tag = db.insert_conversation(created_by="a", conversation=ConversationInput(user_tags=["b"]))
        db.insert_message(tag, "a", MessageInput(content="hi"))
        assert db.get_unread_count(tag, "b") == 1
        assert db.get_unread_count(tag, "a") == 0
        db.mark_read(tag, "b")
        assert db.get_unread_count(tag, "b") == 0
