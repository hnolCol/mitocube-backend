"""Route-level tests for the ticket attachment (screenshot upload) endpoints,
using dependency_overrides with a fake database like test_migrated_routers.py."""

import sys
import time
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC_DIR))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from config.enums.users.roles import UserRolesEnum
from config.models.tickets import TicketAttachmentModel, TicketModel, TicketStatusEnum
from config.models.user import UserModel
from lib.database.Database import get_db
from services import ticket_attachments
from services.users import get_user_from_token
from routers.tickets.tickets import router as tickets_router

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def make_user(tag, role=UserRolesEnum.STANDARD):
    return UserModel(
        tag=tag,
        firstname="Test",
        lastname="User",
        email=f"{tag}@age.mpg.de",
        created_at=time.time(),
        role=role,
        allow_login=True,
    )


def make_ticket(tag="ticket-1", raised_by="raiser-1"):
    return TicketModel(
        tag=tag,
        reference="TIC-000001",
        title="Cannot export",
        description="The export button does nothing.",
        status=TicketStatusEnum.OPEN,
        created_at=1,
        updated_at=1,
        raised_by=raised_by,
    )


class FakeTicketsDB:
    def __init__(self, ticket):
        self.ticket = ticket
        self.attachments = {}

    def get_ticket(self, ticket_tag):
        return self.ticket if self.ticket.tag == ticket_tag else None

    def insert_attachment(self, ticket_tag, attachment_tag, uploaded_by, filename,
                          content_type, size, extension):
        if self.ticket.tag != ticket_tag:
            return None
        attachment = TicketAttachmentModel(
            tag=attachment_tag, ticket_tag=ticket_tag, filename=filename,
            content_type=content_type, size=size, extension=extension,
            uploaded_by=uploaded_by, uploaded_by_name="Test User", created_at=2)
        self.attachments[attachment_tag] = attachment
        return attachment

    def get_attachment(self, attachment_tag):
        return self.attachments.get(attachment_tag)

    def get_attachments_for_ticket(self, ticket_tag):
        return [a for a in self.attachments.values() if a.ticket_tag == ticket_tag]


class FakeDB:
    def __init__(self, ticket):
        self.tickets = FakeTicketsDB(ticket)


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(ticket_attachments, "get_attachment_root", lambda: tmp_path)
    return tmp_path


def make_client(user, ticket):
    app = FastAPI()
    app.include_router(tickets_router)
    db = FakeDB(ticket)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_user_from_token] = lambda: user
    return TestClient(app)


@pytest.fixture
def raiser_client(env):
    return make_client(make_user("raiser-1"), make_ticket())


@pytest.fixture
def admin_client(env):
    return make_client(make_user("admin-12", UserRolesEnum.ADMIN), make_ticket())


class TestUpload:
    def test_raiser_can_upload_png(self, raiser_client):
        resp = raiser_client.post(
            "/api/tickets/ticket-1/attachments",
            files={"file": ("screenshot.png", PNG_BYTES, "image/png")})
        assert resp.status_code == 201
        body = resp.json()
        assert body["ticket_tag"] == "ticket-1"
        assert body["filename"] == "screenshot.png"
        assert body["content_type"] == "image/png"
        assert body["size"] == len(PNG_BYTES)
        assert body["uploaded_by"] == "raiser-1"

    def test_admin_can_upload(self, admin_client):
        resp = admin_client.post(
            "/api/tickets/ticket-1/attachments",
            files={"file": ("shot.png", PNG_BYTES, "image/png")})
        assert resp.status_code == 201

    def test_stranger_gets_403(self, env):
        client = make_client(make_user("strang1r"), make_ticket())
        resp = client.post(
            "/api/tickets/ticket-1/attachments",
            files={"file": ("shot.png", PNG_BYTES, "image/png")})
        assert resp.status_code == 403

    def test_unknown_ticket_gets_404(self, env):
        client = make_client(make_user("raiser-1"), make_ticket())
        resp = client.post(
            "/api/tickets/nope/attachments",
            files={"file": ("shot.png", PNG_BYTES, "image/png")})
        assert resp.status_code == 404

    def test_non_image_gets_415(self, raiser_client):
        resp = raiser_client.post(
            "/api/tickets/ticket-1/attachments",
            files={"file": ("notes.png", b"definitely not an image", "image/png")})
        assert resp.status_code == 415

    def test_oversized_file_gets_413(self, raiser_client, monkeypatch):
        from config.settings.general import get_general_settings
        import routers.tickets.tickets as tickets_module
        monkeypatch.setattr(tickets_module.GENERAL_SETTINGS, "ticket_attachment_max_size_mb", 0)
        resp = raiser_client.post(
            "/api/tickets/ticket-1/attachments",
            files={"file": ("big.png", PNG_BYTES, "image/png")})
        assert resp.status_code == 413


class TestListAndDownload:
    def _upload(self, client):
        resp = client.post(
            "/api/tickets/ticket-1/attachments",
            files={"file": ("screenshot.png", PNG_BYTES, "image/png")})
        assert resp.status_code == 201
        return resp.json()

    def test_list_and_download_roundtrip(self, raiser_client, env):
        attachment = self._upload(raiser_client)

        resp = raiser_client.get("/api/tickets/ticket-1/attachments")
        assert resp.status_code == 200
        assert [a["tag"] for a in resp.json()] == [attachment["tag"]]

        resp = raiser_client.get(f"/api/tickets/ticket-1/attachments/{attachment['tag']}")
        assert resp.status_code == 200
        assert resp.content == PNG_BYTES
        assert resp.headers["content-type"].startswith("image/png")

    def test_download_from_other_ticket_gets_404(self, raiser_client):
        attachment = self._upload(raiser_client)
        other = make_ticket(tag="ticket-2", raised_by="raiser-1")
        client = make_client(make_user("raiser-1"), other)
        resp = client.get(f"/api/tickets/ticket-2/attachments/{attachment['tag']}")
        assert resp.status_code == 404

    def test_stranger_cannot_download(self, env):
        raiser = make_client(make_user("raiser-1"), make_ticket())
        attachment = self._upload(raiser)
        stranger = make_client(make_user("strang1r"), make_ticket())
        resp = stranger.get(f"/api/tickets/ticket-1/attachments/{attachment['tag']}")
        assert resp.status_code == 403
