"""GitHub authentication.

Three sources, in order of preference:

* a GitHub App: a short-lived installation token minted from an RS256 JWT;
* a personal access token (the M0.5 bootstrap for self-host);
* SSH/deploy-key remotes, which have no API token and cannot open PRs.

The App path needs the ``cryptography`` package; it is an optional extra
(``pip install 'forgel[github]'``). PATs work without it.
"""

from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from ..secrets import get_secret

DEFAULT_API_BASE = "https://api.github.com"
API_VERSION = "2022-11-28"


class GithubAuthError(RuntimeError):
    """GitHub credentials are missing or invalid."""


@dataclass(frozen=True)
class AuthToken:
    token: str
    kind: str  # app | pat
    expires_at: int | None = None


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


class GithubAuth:
    def __init__(
        self,
        home: Path,
        environ: Mapping[str, str] | None = None,
        api_base: str | None = None,
    ) -> None:
        self.home = home
        self.env = environ if environ is not None else os.environ
        self.api_base = (
            api_base
            or self.env.get("FORGEL_GITHUB_API_BASE", DEFAULT_API_BASE)
        ).rstrip("/")
        self._cached: AuthToken | None = None

    # --------------------------------------------------------------- source

    def pat(self) -> str:
        return get_secret(self.home, "github.token", self.env)

    def app_id(self) -> str:
        return get_secret(self.home, "github.app_id", self.env)

    def installation_id(self) -> str:
        return get_secret(self.home, "github.installation_id", self.env)

    def private_key(self) -> str:
        literal = get_secret(self.home, "github.app_private_key", self.env)
        if literal:
            return literal
        path = get_secret(
            self.home, "github.app_private_key_path", self.env
        )
        if not path:
            return ""
        key_path = Path(path).expanduser()
        try:
            return key_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise GithubAuthError(
                f"cannot read the GitHub App private key: {exc}"
            ) from exc

    def app_ready(self) -> bool:
        return bool(self.app_id() and self.private_key())

    def status(self) -> str:
        parts: list[str] = []
        try:
            app_ready = self.app_ready()
        except GithubAuthError as exc:
            parts.append(f"GitHub App misconfigured: {exc}")
            app_ready = False
        if app_ready:
            parts.append("GitHub App configured")
        if self.pat():
            parts.append("PAT configured")
        return ", ".join(parts) or "no GitHub credentials"

    # --------------------------------------------------------------- tokens

    def resolve(self, prefer: str = "auto") -> AuthToken:
        if prefer == "deploy_key":
            raise GithubAuthError(
                "deploy keys have no API token; use auth=pat or github_app "
                "for pull requests"
            )
        if prefer == "pat" or (prefer == "auto" and not self.app_ready()):
            token = self.pat()
            if not token:
                raise GithubAuthError(
                    "no GitHub token; set FORGEL_GITHUB_TOKEN or use "
                    "/secret set github.token"
                )
            return AuthToken(token=token, kind="pat")
        if not self.app_ready():
            raise GithubAuthError(
                "github_app auth needs github.app_id and a private key"
            )
        return self._app_token()

    # ------------------------------------------------------------------ app

    def _app_token(self) -> AuthToken:
        now = int(time.time())
        if (
            self._cached is not None
            and self._cached.expires_at is not None
            and self._cached.expires_at > now + 60
        ):
            return self._cached
        jwt = self._jwt()
        installation = self.installation_id()
        if not installation:
            installations = self._request(
                "GET", "/app/installations", jwt
            )
            if not isinstance(installations, list) or not installations:
                raise GithubAuthError(
                    "the GitHub App has no installations"
                )
            if len(installations) > 1:
                names = ", ".join(
                    str(item.get("account", {}).get("login", "?"))
                    for item in installations
                )
                raise GithubAuthError(
                    "the GitHub App has several installations; set "
                    f"github.installation_id (one of {names})"
                )
            installation = str(installations[0].get("id", ""))
            if not installation:
                raise GithubAuthError("cannot determine the installation id")
        result = self._request(
            "POST",
            f"/app/installations/{installation}/access_tokens",
            jwt,
        )
        if not isinstance(result, dict) or not result.get("token"):
            raise GithubAuthError(
                "GitHub did not return an installation token"
            )
        expires_at = None
        raw_expiry = result.get("expires_at")
        if isinstance(raw_expiry, str):
            try:
                expires_at = int(
                    datetime.fromisoformat(
                        raw_expiry.replace("Z", "+00:00")
                    ).timestamp()
                )
            except ValueError:
                expires_at = None
        token = AuthToken(
            token=str(result["token"]),
            kind="app",
            expires_at=expires_at,
        )
        self._cached = token
        return token

    def _jwt(self) -> str:
        app_id = self.app_id()
        key = self.private_key()
        if not app_id or not key:
            raise GithubAuthError("the GitHub App is not configured")
        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding
        except ImportError as exc:
            raise GithubAuthError(
                "GitHub App auth requires the 'github' extra: "
                "pip install 'forgel[github]'"
            ) from exc
        now = int(time.time())
        header = _b64(
            json.dumps({"alg": "RS256", "typ": "JWT"}).encode("utf-8")
        )
        payload = _b64(
            json.dumps(
                {"iat": now - 60, "exp": now + 540, "iss": app_id}
            ).encode("utf-8")
        )
        signing_input = f"{header}.{payload}".encode("ascii")
        try:
            private_key = serialization.load_pem_private_key(
                key.encode("utf-8"), password=None
            )
            signature = private_key.sign(
                signing_input, padding.PKCS1v15(), hashes.SHA256()
            )
        except Exception as exc:  # noqa: BLE001 - surface a clear auth error
            raise GithubAuthError(
                f"cannot sign the GitHub App JWT: {exc}"
            ) from exc
        return f"{header}.{payload}.{_b64(signature)}"

    def _request(
        self, method: str, path: str, token: str
    ) -> Any:
        request = urllib.request.Request(
            f"{self.api_base}{path}",
            data=b"{}" if method == "POST" else None,
            method=method,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": API_VERSION,
                "User-Agent": "forgel",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read()
        except urllib.error.HTTPError as exc:
            try:
                detail = json.loads(exc.read().decode("utf-8"))
                message = str(detail.get("message", exc.reason))
            except (OSError, ValueError):
                message = str(exc.reason)
            raise GithubAuthError(
                self._redact(f"GitHub auth failed ({exc.code}): {message}")
            ) from exc
        except (urllib.error.URLError, OSError) as exc:
            raise GithubAuthError(
                self._redact(f"GitHub auth request failed: {exc}")
            ) from exc
        if not body:
            return None
        try:
            return json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise GithubAuthError("GitHub returned invalid JSON") from exc

    def _redact(self, message: str) -> str:
        pat = self.pat()
        if pat:
            message = message.replace(pat, "***")
        return message
