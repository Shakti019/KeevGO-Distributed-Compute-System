import hashlib
import secrets
from pathlib import Path


class AdminAuth:
    """Local master token store; the token never enters friend invitations."""

    def __init__(self, path=".shac-master-token"):
        self.path = Path(path)

    def exists(self):
        return self.path.is_file()

    def create(self):
        token = secrets.token_urlsafe(32)
        self.path.write_text(self._digest(token), encoding="utf-8")
        return token

    def verify(self, token):
        if not token or not self.exists():
            return False
        expected = self.path.read_text(encoding="utf-8").strip()
        actual = self._digest(token)
        return secrets.compare_digest(actual, expected)

    @staticmethod
    def _digest(token):
        return hashlib.sha256(token.encode("utf-8")).hexdigest()
