import hashlib
import secrets
from abc import abstractmethod, ABC
from typing import List, Optional, Tuple

from config.models.pat import PATResponseModel

PAT_TOKEN_PREFIX = "mcp_"


def hash_pat_token(token : str) -> str:
    """Returns the SHA-256 hex digest of a plain PAT."""
    return hashlib.sha256(token.encode()).hexdigest()


def generate_pat_token() -> str:
    """Generates a new plain PAT. Prefixed so secret scanners can recognize leaks."""
    return f"{PAT_TOKEN_PREFIX}{secrets.token_urlsafe(32)}"


class PATABC(ABC):
    """Personal access tokens (PATs) for non-interactive API access.

    A PAT belongs to exactly one user, carries a set of scopes and can be
    revoked at any time. Only the SHA-256 hash of the plain token is
    stored; the plain token is returned exactly once at creation.
    """

    @abstractmethod
    def create(self, user_tag : str, name : str, scopes : List[str], expires_at_epochmillis : int) -> Tuple[PATResponseModel, str]:
        """Creates a PAT for the user and returns its metadata and the plain token.

        Parameters
        ----------
        user_tag : str
            The tag of the user the token belongs to.
        name : str
            Human readable name of the token.
        scopes : List[str]
            Scopes granted to the token.
        expires_at_epochmillis : int
            Expiration of the token in epoch milliseconds.

        Returns
        -------
        Tuple[PATResponseModel, str]
            The token metadata and the plain token (shown exactly once).

        Raises
        ------
        ValueError
            If the user does not exist or token creation is blocked for the user.
        """

    @abstractmethod
    def get_by_hash(self, token_hash : str) -> Optional[dict]:
        """Returns the PAT with the given hash together with its owner tag.

        Parameters
        ----------
        token_hash : str
            SHA-256 hex digest of the plain token.

        Returns
        -------
        Optional[dict]
            Dict with keys 'user_tag' and 'pat' (PAT properties), or None
            if no active PAT with this hash exists.
        """

    @abstractmethod
    def list(self, user_tag : str) -> List[PATResponseModel]:
        """Returns all PATs of the user (metadata only, no hashes)."""

    @abstractmethod
    def revoke(self, user_tag : str, pat_tag : str) -> bool:
        """Revokes the PAT if it belongs to the user.

        Returns
        -------
        bool
            True if a token was revoked.
        """

    @abstractmethod
    def revoke_by_admin(self, pat_tag : str, revoked_by : str) -> bool:
        """Revokes any PAT and records which admin revoked it.

        Parameters
        ----------
        pat_tag : str
            The tag of the token to revoke.
        revoked_by : str
            The tag of the admin performing the revocation.

        Returns
        -------
        bool
            True if an active token was revoked.
        """

    @abstractmethod
    def set_creation_blocked(self, user_tag : str, blocked : bool) -> bool:
        """Blocks or unblocks PAT creation for the user.

        Returns
        -------
        bool
            True if the user exists and the flag was set.
        """

    @abstractmethod
    def touch(self, pat_tag : str) -> None:
        """Stamps last_used_at of the PAT with the current time."""
