from services import ticket_attachments
from services.ticket_attachments import detect_image_type, sanitize_filename, get_attachment_path

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 16
GIF = b"GIF89a" + b"\x00" * 16
WEBP = b"RIFF" + b"\x04\x00\x00\x00" + b"WEBP" + b"\x00" * 8


class TestDetectImageType:
    def test_accepts_supported_images(self):
        assert detect_image_type(PNG) == ("image/png", ".png")
        assert detect_image_type(JPEG) == ("image/jpeg", ".jpg")
        assert detect_image_type(GIF) == ("image/gif", ".gif")
        assert detect_image_type(WEBP) == ("image/webp", ".webp")

    def test_rejects_non_images(self):
        assert detect_image_type(b"") is None
        assert detect_image_type(b"<html>not an image</html>") is None
        assert detect_image_type(b"RIFF\x04\x00\x00\x00WAVE" + b"\x00" * 8) is None
        assert detect_image_type(b"\x89PNG") is None


class TestSanitizeFilename:
    def test_strips_path_parts(self):
        assert sanitize_filename("../../etc/passwd") == "passwd"
        assert sanitize_filename("C:\\temp\\shot.png") == "shot.png"

    def test_replaces_unsafe_characters(self):
        assert sanitize_filename("my screenshot (1).png") == "my_screenshot_1_.png"

    def test_fallback_for_empty_name(self):
        assert sanitize_filename("") == "attachment"
        assert sanitize_filename(None) == "attachment"


class TestAttachmentPath:
    def test_path_is_derived_from_tags(self, tmp_path, monkeypatch):
        monkeypatch.setattr(ticket_attachments, "get_attachment_root", lambda: tmp_path)
        path = get_attachment_path("ticket1", "attach1", ".png")
        assert path == tmp_path / "ticket1" / "attach1.png"

    def test_tags_cannot_escape_directory(self, tmp_path, monkeypatch):
        monkeypatch.setattr(ticket_attachments, "get_attachment_root", lambda: tmp_path)
        path = get_attachment_path("../..", "..\\evil", ".png")
        assert path.parent.parent == tmp_path
        assert ".." not in path.parts

    def test_dot_only_tags_are_neutralized(self, tmp_path, monkeypatch):
        monkeypatch.setattr(ticket_attachments, "get_attachment_root", lambda: tmp_path)
        for ticket_tag, attachment_tag in [("..", "abc12345"), ("tick1234", ".."), ("..", "..")]:
            path = get_attachment_path(ticket_tag, attachment_tag, ".png")
            assert path.parent.parent == tmp_path
            assert "." not in path.parts and ".." not in path.parts
