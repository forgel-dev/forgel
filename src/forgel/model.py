"""Model client for project conversations.

Production uses an OpenAI-compatible endpoint (DeepSeek by default) with the
key and URL from the environment or the local secret store. Local runs and
tests can use a scripted client, which returns pre-generated responses; that is
how a subagent with the same prompt can stand in for a model call.
"""

from __future__ import annotations

import http.client
import json
import os
import threading
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
    timeout: float = 600.0
    total_timeout: float = 3_600.0
    retries: int = 5
    retry_backoff: tuple[float, ...] = (1.0, 3.0, 9.0)


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
        self.last_usage: dict[str, Any] | None = None

    def complete(
        self,
        messages: Sequence[ModelMessage],
        model: str | None = None,
    ) -> str:
        total = float(self.config.total_timeout or 0)
        if total <= 0:
            return self._complete(messages, model)
        result: dict[str, Any] = {}
        errors: list[BaseException] = []

        def run() -> None:
            try:
                result["text"] = self._complete(messages, model)
            except BaseException as exc:  # noqa: BLE001 - re-raised below
                errors.append(exc)

        worker = threading.Thread(target=run, daemon=True)
        worker.start()
        worker.join(total)
        if worker.is_alive():
            raise ModelError(
                f"model call exceeded the {total:g}s deadline"
            )
        if errors:
            raise errors[0]
        return str(result.get("text") or "")

    def _complete(
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
        request_url = f"{self.config.base_url.rstrip('/')}/chat/completions"
        attempts = max(1, min(int(self.config.retries) + 1, 10))
        body: Any = None
        self.last_usage = None
        for attempt in range(1, attempts + 1):
            request = urllib.request.Request(
                request_url,
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
                break
            except urllib.error.HTTPError as exc:
                if exc.code in {429, 500, 502, 503, 504} and (
                    attempt < attempts
                ):
                    self._retry_sleep(attempt)
                    continue
                raise ModelError(
                    self._redact(
                        f"model request failed after {attempt} attempt(s): "
                        f"HTTP {exc.code}"
                    )
                ) from exc
            except http.client.HTTPException as exc:
                # A dropped chunked response (IncompleteRead), a reset stream
                # or a bad status line is a transport failure: retry a fresh
                # request instead of crashing the task as an external defect.
                if attempt < attempts:
                    self._retry_sleep(attempt)
                    continue
                raise ModelError(
                    self._redact(
                        "model request failed after "
                        f"{attempts} attempts: {exc}"
                    )
                ) from exc
            except (urllib.error.URLError, OSError) as exc:
                if attempt < attempts:
                    self._retry_sleep(attempt)
                    continue
                raise ModelError(
                    self._redact(
                        "model request failed after "
                        f"{attempts} attempts: {exc}"
                    )
                ) from exc
            except json.JSONDecodeError as exc:
                if attempt < attempts:
                    self._retry_sleep(attempt)
                    continue
                raise ModelError(
                    "model endpoint returned invalid JSON"
                ) from exc
            except UnicodeDecodeError as exc:
                if attempt < attempts:
                    self._retry_sleep(attempt)
                    continue
                raise ModelError(
                    "model endpoint returned an unreadable body"
                ) from exc
        if body is None:
            raise ModelError("model request failed")
        if not isinstance(body, dict):
            raise ModelError("model endpoint returned an unexpected response")
        usage = body.get("usage")
        if isinstance(usage, dict):
            self.last_usage = usage
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

    def _retry_sleep(self, attempt: int) -> None:
        backoff = self.config.retry_backoff or (1.0,)
        delay = backoff[min(attempt - 1, len(backoff) - 1)]
        if delay > 0:
            time.sleep(delay)

    def _redact(self, message: str) -> str:
        if self.config.api_key:
            return message.replace(self.config.api_key, "***")
        return message


class BridgeModelClient:
    """File bridge for local runs driven by an external subagent.

    Each call writes a request file and waits for a response file. The driver
    is outside Forgel; it can be an external subagent, another agent or a
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


def cache_tokens(usage: Mapping[str, Any]) -> tuple[int, int]:
    """Provider cache hit and miss tokens, whatever shape the usage takes."""

    try:
        hit = usage.get("prompt_cache_hit_tokens")
        if hit is None:
            details = usage.get("prompt_tokens_details")
            if isinstance(details, Mapping):
                hit = details.get("cached_tokens")
        hit = int(hit or 0)
        miss = usage.get("prompt_cache_miss_tokens")
        if miss is None:
            miss = max(0, int(usage.get("prompt_tokens") or 0) - hit)
        miss = int(miss or 0)
    except (TypeError, ValueError):
        return 0, 0
    return max(0, hit), max(0, miss)


class UsageCounter:
    """Wrap a client and total the provider usage of every call."""

    def __init__(self, client: ModelClient) -> None:
        self.client = client
        self.calls = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.cache_hit_tokens = 0
        self.cache_miss_tokens = 0

    def complete(
        self,
        messages: Sequence[ModelMessage],
        model: str | None = None,
    ) -> str:
        text = self.client.complete(messages, model=model)
        self.calls += 1
        usage = getattr(self.client, "last_usage", None)
        if isinstance(usage, dict):
            self.input_tokens += int(usage.get("prompt_tokens") or 0)
            self.output_tokens += int(
                usage.get("completion_tokens") or 0
            )
            hit, miss = cache_tokens(usage)
            self.cache_hit_tokens += hit
            self.cache_miss_tokens += miss
        return text


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
    try:
        timeout = float(env.get("FORGEL_MODEL_TIMEOUT", "600"))
    except ValueError:
        timeout = 600.0
    if timeout <= 0:
        timeout = 600.0
    try:
        retries = int(env.get("FORGEL_MODEL_RETRIES", "5"))
    except ValueError:
        retries = 5
    try:
        total_timeout = float(
            env.get("FORGEL_MODEL_TOTAL_TIMEOUT", "3600")
        )
    except ValueError:
        total_timeout = 3_600.0
    if total_timeout <= 0:
        total_timeout = 3_600.0
    retries = max(0, min(retries, 10))
    backoff: list[float] = []
    for item in env.get("FORGEL_MODEL_RETRY_BACKOFF", "1,3,9").split(","):
        try:
            value = float(item.strip())
        except ValueError:
            continue
        if value >= 0:
            backoff.append(value)
    return OpenAICompatibleClient(
        ModelConfig(
            base_url=base_url,
            api_key=key,
            timeout=timeout,
            total_timeout=total_timeout,
            retries=retries,
            retry_backoff=tuple(backoff) or (1.0,),
        )
    )
