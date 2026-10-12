"""Resolve the .env file location independent of the current working directory.

Settings classes use ``env_file = get_env_file()`` so that the application
loads the same .env file whether it is started from the repository root
(``python3 src/app.py``) or from inside ``src/`` (``python3 app.py``).

Search order:
1. ``MITOCUBE_ENV_FILE`` environment variable (explicit override)
2. ``.env`` in the directory containing the ``config`` package (``src/.env``)
3. ``.env`` in the parent of that directory (repository root ``.env``)
"""

import os
from pathlib import Path

_PACKAGE_DIR = Path(__file__).resolve().parent.parent  # .../src/config
_SRC_DIR = _PACKAGE_DIR.parent                          # .../src
_REPO_ROOT = _SRC_DIR.parent                             # repository root


def get_env_file() -> str:
    override = os.environ.get("MITOCUBE_ENV_FILE")
    if override:
        return override
    src_env = _SRC_DIR / ".env"
    if src_env.is_file():
        return str(src_env)
    return str(_REPO_ROOT / ".env")
