"""Model client for project conversations.

Production uses an OpenAI-compatible endpoint (DeepSeek by default) with the
key and URL from the environment or the local secret store. Local runs and
tests can use a scripted client, which returns pre-generated responses; that is
how a subagent with the same prompt can stand in for a model call.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence

from .artifacts import write_json

from . import daemon_config
from .model_profiles import default_profile
from .project_config import ConfigError, load_project_config
from .secrets import get_secret

DEFAULT_MODEL = default_profile().default_model


class ModelError(RuntimeError):
    """The model endpoint is not configured or returned an invalid answer."""


@dataclass(frozen=True)
class ModelMessage:
    role: str
    content: str


@dataclass(frozen=True)
class ModelConfig:
    base_url: str
    api_key: str
    timeout: float = 120.0


class ModelClient(Protocol):
    def complete(
        self,
        messages: Sequence[ModelMessage],
        model: str | None = None,
    ) -> str: ...


class OpenAICompatibleClient:
    def __init__(
        self,
        config: ModelConfig,
        opener: Callable[..., Any] | None = None,
    ) -> None:
        self.config = config
        self._opener = opener or urllib.request.urlopen

    def complete(
        self,
        messages: Sequence[ModelMessage],
        model: str | None = None,
    ) -> str:
        payload = {
            "model": model or DEFAULT_MODEL,
            "messages": [
                {"role": message.role, "content": message.content}
                for message in messages
            ],
            "temperature": 0.2,
        }
        request = urllib.request.Request(
            f"{self.config.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.api_key}",
            },
        )
        try:
            with self._opener(
                request, timeout=self.config.timeout
            ) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, OSError) as exc:
            raise ModelError(self._redact(f"model request failed: {exc}")) from exc
        except json.JSONDecodeError as exc:
            raise ModelError("model endpoint returned invalid JSON") from exc
        if not isinstance(body, dict):
            raise ModelError("model endpoint returned an unexpected response")
        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ModelError("model endpoint returned no choices")
        message = choices[0].get("message", {})
        content = message.get("content")
        if isinstance(content, list):
            content = "".join(
                str(part.get("text", ""))
                for part in content
                if isinstance(part, dict)
            )
        if not isinstance(content, str) or not content.strip():
            raise ModelError("model endpoint returned an empty answer")
        return content

    def _redact(self, message: str) -> str:
        if self.config.api_key:
            return message.replace(self.config.api_key, "***")
        return message


class BridgeModelClient:
    """File bridge for local runs driven by an external subagent.

    Each call writes a request file and waits for a response file. The driver
    is outside Forgel; it can be a Claude Code subagent, another harness or a
    human. This keeps a local run from spending provider budget.
    """

    def __init__(
        self,
        directory: Path,
        timeout: float = 900.0,
        poll_interval: float = 0.5,
    ) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.poll_interval = poll_interval

    def complete(
        self,
        messages: Sequence[ModelMessage],
        model: str | None = None,
    ) -> str:
        request_id = (
            datetime_stamp()
            + "-"
            + uuid.uuid4().hex[:8]
        )
        request = {
            "id": request_id,
            "model": model or "",
            "messages": [
                {"role": message.role, "content": message.content}
                for message in messages
            ],
            "created_at": unix_now(),
        }
        write_json(self.directory / f"{request_id}.request.json", request)
        response_path = self.directory / f"{request_id}.response.json"
        text_path = self.directory / f"{request_id}.response.txt"
        error_path = self.directory / f"{request_id}.error.json"
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            if text_path.exists():
                content = text_path.read_text(encoding="utf-8")
                if content.strip():
                    return content
            if response_path.exists():
                try:
                    data = json.loads(
                        response_path.read_text(encoding="utf-8")
                    )
                except (OSError, json.JSONDecodeError) as exc:
                    raise ModelError(
                        f"bridge response is invalid: {exc}"
                    ) from exc
                content = (
                    data.get("content")
                    if isinstance(data, dict)
                    else data
                )
                if not isinstance(content, str) or not content.strip():
                    raise ModelError("bridge response is empty")
                return content
            if error_path.exists():
                try:
                    data = json.loads(
                        error_path.read_text(encoding="utf-8")
                    )
                    detail = (
                        data.get("error", data)
                        if isinstance(data, dict)
                        else data
                    )
                except (OSError, json.JSONDecodeError):
                    detail = "driver reported an error"
                raise ModelError(f"bridge driver error: {detail}")
            time.sleep(self.poll_interval)
        raise ModelError(
            f"bridge timed out after {self.timeout:g}s; "
            f"request {request_id} is in {self.directory}"
        )


def datetime_stamp() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")


def unix_now() -> float:
    return time.time()


class ScriptedModelClient:
    """Return canned responses and record the prompts for inspection."""

    def __init__(self, responses: Sequence[str]) -> None:
        self._responses = list(responses)
        self.requests: list[list[ModelMessage]] = []

    def complete(
        self,
        messages: Sequence[ModelMessage],
        model: str | None = None,
    ) -> str:
        self.requests.append(list(messages))
        if not self._responses:
            raise ModelError("scripted model client has no response left")
        return self._responses.pop(0)


def project_model_name(
    control: Path, environ: Mapping[str, str] | None = None
) -> str:
    env = environ if environ is not None else os.environ
    override = env.get("FORGEL_MODEL_NAME", "").strip()
    if override:
        return override
    try:
        config = load_project_config(control)
    except (ConfigError, OSError):
        config = None
    if config is not None and config.models.default:
        return config.models.default
    return DEFAULT_MODEL


def build_model_client(
    home: Path,
    environ: Mapping[str, str] | None = None,
    log: Callable[[str], None] | None = None,
) -> ModelClient | None:
    """Build the configured client, or return ``None`` when no model is set."""

    env = environ if environ is not None else os.environ
    mode = env.get("FORGEL_MODEL_MODE", "auto").strip().lower()
    if mode == "off":
        return None
    if mode in {"bridge", "subagent"}:
        directory = Path(
            env.get("FORGEL_MODEL_BRIDGE_DIR", home / "model-bridge")
        )
        return BridgeModelClient(directory)
    if mode == "script":
        path = home / "model-script.json"
        if not path.exists():
            if log:
                log(f"[model] script mode: {path} does not exist")
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            if log:
                log(f"[model] cannot read {path}: {exc}")
            return None
        responses = data.get("responses", []) if isinstance(data, dict) else data
        if not isinstance(responses, list):
            if log:
                log(f"[model] {path} must contain a list of responses")
            return None
        return ScriptedModelClient([str(item) for item in responses])

    key = get_secret(home, "model.api_key", env)
    if not key:
        return None
    base_url = env.get("FORGEL_MODEL_BASE_URL", "").strip()
    if not base_url:
        try:
            base_url = str(daemon_config.get_value(home, "models.base_url"))
        except daemon_config.DaemonConfigError as exc:
            if log:
                log(f"[model] invalid daemon configuration: {exc}")
            return None
    if not base_url.startswith(("http://", "https://")):
        if log:
            log(f"[model] invalid base URL: {base_url!r}")
        return None
    return OpenAICompatibleClient(
        ModelConfig(base_url=base_url, api_key=key)
    )
