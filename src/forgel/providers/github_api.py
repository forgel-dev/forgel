"""Minimal GitHub REST client for the pull-request flow.

Only the endpoints the flow needs: repository metadata, pull requests, check
runs and the merge call. Errors carry the HTTP status and GitHub's message;
the token is redacted.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from .github_auth import API_VERSION, DEFAULT_API_BASE, is_dns_error

FAILED_CONCLUSIONS = {
    "failure",
    "cancelled",
    "timed_out",
    "action_required",
    "startup_failure",
}


class GithubAPIError(RuntimeError):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


@dataclass(frozen=True)
class CheckReport:
    state: str  # green | pending | failed | none
    total: int = 0
    failed: list[str] | None = None
    pending: list[str] | None = None

    @property
    def is_green(self) -> bool:
        return self.state in {"green", "none"}


class GithubAPI:
    def __init__(
        self,
        token: str,
        api_base: str = DEFAULT_API_BASE,
        opener: Callable[..., Any] | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.token = token
        self.api_base = api_base.rstrip("/")
        self._opener = opener or urllib.request.urlopen
        self.timeout = timeout

    def request(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> Any:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            f"{self.api_base}{path}",
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": API_VERSION,
                "User-Agent": "forgel",
                **(
                    {"Content-Type": "application/json"}
                    if payload is not None
                    else {}
                ),
            },
        )
        attempts = 3
        backoff = (0.0, 1.0, 3.0)
        for attempt in range(1, attempts + 1):
            try:
                with self._opener(
                    request, timeout=self.timeout
                ) as response:
                    body = response.read()
                break
            except urllib.error.HTTPError as exc:
                if exc.code in {429, 500, 502, 503, 504} and attempt < attempts:
                    time.sleep(backoff[min(attempt - 1, len(backoff) - 1)])
                    continue
                message = self._error_message(exc)
                raise GithubAPIError(exc.code, message) from exc
            except (urllib.error.URLError, OSError) as exc:
                if is_dns_error(exc):
                    raise GithubAPIError(
                        0,
                        "GitHub API is not reachable by DNS "
                        "(api.github.com). Check VPN/network and retry.",
                    ) from exc
                if attempt < attempts:
                    time.sleep(backoff[min(attempt - 1, len(backoff) - 1)])
                    continue
                raise GithubAPIError(
                    0, self._redact(f"GitHub request failed: {exc}")
                ) from exc
        if not body:
            return None
        try:
            return json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise GithubAPIError(0, "GitHub returned invalid JSON") from exc

    def _error_message(self, exc: urllib.error.HTTPError) -> str:
        try:
            body = json.loads(exc.read().decode("utf-8"))
            message = str(body.get("message", exc.reason))
            errors = body.get("errors")
            if isinstance(errors, list) and errors:
                details = "; ".join(
                    str(item.get("message", item))
                    if isinstance(item, dict)
                    else str(item)
                    for item in errors
                )
                message += f" ({details})"
        except (OSError, ValueError):
            message = str(exc.reason)
        return self._redact(f"GitHub API {exc.code}: {message}")

    def _redact(self, message: str) -> str:
        return message.replace(self.token, "***") if self.token else message

    # --------------------------------------------------------------- repo

    def repo(self, full_name: str) -> dict[str, Any]:
        return self.request("GET", f"/repos/{full_name}")

    def user(self) -> dict[str, Any]:
        return self.request("GET", "/user")

    def create_repo(
        self,
        owner: str,
        name: str,
        private: bool = True,
        description: str = "",
    ) -> dict[str, Any]:
        """Create an empty repository in an organization or for the user."""

        path = f"/orgs/{owner}/repos" if owner else "/user/repos"
        return self.request(
            "POST",
            path,
            {
                "name": name,
                "private": private,
                "description": description,
                "auto_init": False,
            },
        )

    # ------------------------------------------------------------ pull requests

    def find_open_pull(
        self, full_name: str, head: str, base: str
    ) -> dict[str, Any] | None:
        query = urllib.parse.urlencode(
            {"state": "open", "head": head, "base": base}
        )
        result = self.request(
            "GET", f"/repos/{full_name}/pulls?{query}"
        )
        if isinstance(result, list) and result:
            return result[0]
        return None

    def get_pull(self, full_name: str, number: int) -> dict[str, Any]:
        return self.request("GET", f"/repos/{full_name}/pulls/{number}")

    def create_pull(
        self,
        full_name: str,
        head: str,
        base: str,
        title: str,
        body: str,
        draft: bool,
    ) -> dict[str, Any]:
        return self.request(
            "POST",
            f"/repos/{full_name}/pulls",
            {
                "title": title,
                "head": head,
                "base": base,
                "body": body,
                "draft": draft,
            },
        )

    def mark_ready(self, full_name: str, number: int) -> None:
        try:
            self.request(
                "POST",
                f"/repos/{full_name}/pulls/{number}/ready_for_review",
            )
        except GithubAPIError as exc:
            if exc.status == 422 and "ready" in exc.message.lower():
                return
            raise

    def merge_pull(
        self,
        full_name: str,
        number: int,
        method: str = "squash",
    ) -> dict[str, Any]:
        return self.request(
            "PUT",
            f"/repos/{full_name}/pulls/{number}/merge",
            {"merge_method": method},
        )

    # ------------------------------------------------------------ releases

    def release_for_tag(
        self, full_name: str, tag: str
    ) -> dict[str, Any] | None:
        path = (
            f"/repos/{full_name}/releases/tags/"
            + urllib.parse.quote(tag, safe="")
        )
        try:
            return self.request("GET", path)
        except GithubAPIError as exc:
            if exc.status == 404:
                return None
            raise

    def create_release(
        self,
        full_name: str,
        tag: str,
        target: str,
        name: str = "",
        body: str = "",
        draft: bool = False,
        prerelease: bool = False,
        generate_notes: bool = False,
    ) -> dict[str, Any]:
        """Create a GitHub release on an existing tag."""

        payload: dict[str, Any] = {
            "tag_name": tag,
            "target_commitish": target,
            "name": name or tag,
            "body": body,
            "draft": draft,
            "prerelease": prerelease,
        }
        if generate_notes:
            payload["generate_release_notes"] = True
        return self.request(
            "POST", f"/repos/{full_name}/releases", payload
        )

    # ---------------------------------------------------------------- checks

    def check_state(self, full_name: str, ref: str) -> CheckReport:
        runs = self.request(
            "GET",
            f"/repos/{full_name}/commits/{ref}/check-runs?per_page=100",
        )
        items = runs.get("check_runs", []) if isinstance(runs, dict) else []
        if items:
            failed: list[str] = []
            pending: list[str] = []
            for item in items:
                name = str(item.get("name", "check"))
                status = str(item.get("status", ""))
                conclusion = str(item.get("conclusion") or "")
                if conclusion in FAILED_CONCLUSIONS:
                    failed.append(name)
                elif status != "completed":
                    pending.append(name)
            if failed:
                return CheckReport("failed", len(items), failed, pending)
            if pending:
                return CheckReport("pending", len(items), [], pending)
            return CheckReport("green", len(items), [], [])

        combined = self.request(
            "GET", f"/repos/{full_name}/commits/{ref}/status"
        )
        if isinstance(combined, dict):
            try:
                total = int(combined.get("total_count", 0))
            except (TypeError, ValueError):
                total = 0
            if total == 0:
                return CheckReport("none")
        state = (
            str(combined.get("state", "none"))
            if isinstance(combined, dict)
            else "none"
        )
        if state == "success":
            return CheckReport("green")
        if state in {"failure", "error"}:
            return CheckReport("failed", failed=[state])
        if state == "pending":
            return CheckReport("pending", pending=["combined status"])
        return CheckReport("none")


def wait_for_checks(
    api: Any,
    full_name: str,
    ref: str,
    timeout: float = 300.0,
    interval: float = 5.0,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
    log: Callable[[str], None] | None = None,
) -> CheckReport:
    deadline = monotonic() + timeout
    last = api.check_state(full_name, ref)
    while last.state == "pending" and monotonic() < deadline:
        if log:
            log("[github] waiting for checks")
        sleep(interval)
        last = api.check_state(full_name, ref)
    return last
