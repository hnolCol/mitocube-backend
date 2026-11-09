import os
import re
from pathlib import Path
from typing import Optional, Tuple

from services.paths.utils import getPathToResources

# (MIME type, file extension, magic bytes predicate)
_IMAGE_SIGNATURES = [
    ("image/png", ".png", lambda d: d[:8] == b"\x89PNG\r\n\x1a\n"),
    ("image/jpeg", ".jpg", lambda d: d[:3] == b"\xff\xd8\xff"),
    ("image/gif", ".gif", lambda d: d[:6] in (b"GIF87a", b"GIF89a")),
    ("image/webp", ".webp", lambda d: d[:4] == b"RIFF" and d[8:12] == b"WEBP"),
]

_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")


def detect_image_type(data : bytes) -> Optional[Tuple[str, str]]:
    """Returns (MIME type, extension) if the bytes match a supported image
    signature, None otherwise. The check uses magic bytes, not the filename."""
    if not data:
        return None
    for mime, ext, matches in _IMAGE_SIGNATURES:
        if matches(data):
            return mime, ext
    return None


def sanitize_filename(filename : Optional[str]) -> str:
    """Reduces an uploaded filename to a safe basename without path parts."""
    name = os.path.basename((filename or "").replace("\\", "/")).strip()
    name = _SAFE_FILENAME.sub("_", name).strip(".")
    return name[:120] if name else "attachment"


def get_attachment_root() -> Path:
    """Returns the root directory for ticket attachments (gitignored resources/data)."""
    return Path(getPathToResources()) / "data" / "ticket_attachments"


def get_attachment_path(ticket_tag : str, attachment_tag : str, extension : str) -> Path:
    """Returns the storage path of an attachment. The filename is derived from the
    attachment tag only, so ticket/attachment tags cannot escape the directory."""
    safe_ticket = _SAFE_FILENAME.sub("_", ticket_tag)
    safe_attachment = _SAFE_FILENAME.sub("_", attachment_tag)
    safe_ext = extension if re.fullmatch(r"\.[A-Za-z0-9]+", extension) else ""
    return get_attachment_root() / safe_ticket / f"{safe_attachment}{safe_ext}"


def save_attachment_file(path : Path, data : bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
