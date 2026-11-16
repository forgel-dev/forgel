from __future__ import annotations

import json
import time
import unittest
import urllib.error
from unittest.mock import patch

from forgel.model import (
    ModelConfig,
    ModelError,
    ModelMessage,
    OpenAICompatibleClient,
)


class _Response:
    def __init__(self, body: dict) -> None:
        self._data = json.dumps(body).encode("utf-8")

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None

    def read(self) -> bytes:
        return self._data


def _body(content: str = "ok") -> dict:
    return {
        "choices": [{"message": {"content": content}}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 3},
    }


class ModelDeadlineTest(unittest.TestCase):
    def test_a_hanging_call_hits_the_total_deadline(self) -> None:
        def opener(_request, timeout=None):
            time.sleep(5)
            return _Response(_body("late"))

        client = OpenAICompatibleClient(
            ModelConfig(
                base_url="https://example.test/v1",
                api_key="secret-key",
                timeout=1,
                total_timeout=0.1,
                retries=0,
            ),
            opener=opener,
        )
        with self.assertRaises(ModelError) as ctx:
            client.complete([ModelMessage("user", "hello")])
        self.assertIn("deadline", str(ctx.exception))


class ModelRetryTest(unittest.TestCase):
    def _client(self, opener, retries: int = 3) -> OpenAICompatibleClient:
        return OpenAICompatibleClient(
            ModelConfig(
                base_url="https://example.test/v1",
                api_key="secret-key",
                timeout=1,
                retries=retries,
                retry_backoff=(0, 0, 0),
            ),
            opener=opener,
        )

    def test_one_timeout_is_retried(self) -> None:
        calls: list[int] = []

        def opener(_request, timeout=None):
            calls.append(1)
            if len(calls) == 1:
                raise TimeoutError("The read operation timed out")
            return _Response(_body())

        client = self._client(opener)
        with patch("forgel.model.time.sleep"):
            answer = client.complete([ModelMessage("user", "hi")])
        self.assertEqual(answer, "ok")
        self.assertEqual(len(calls), 2)
        self.assertEqual(client.last_usage["prompt_tokens"], 11)

    def test_repeated_timeouts_become_infrastructure_error(self) -> None:
        calls: list[int] = []

        def opener(_request, timeout=None):
            calls.append(1)
            raise TimeoutError("The read operation timed out")

        client = self._client(opener, retries=2)
        with patch("forgel.model.time.sleep"):
            with self.assertRaises(ModelError) as raised:
                client.complete([ModelMessage("user", "hi")])
        self.assertIn("after 3 attempts", str(raised.exception))
        self.assertEqual(len(calls), 3)

    def test_auth_error_is_not_retried(self) -> None:
        calls: list[int] = []

        def opener(_request, timeout=None):
            calls.append(1)
            raise urllib.error.HTTPError(
                "https://example.test", 401, "Unauthorized", {}, None
            )

        client = self._client(opener)
        with patch("forgel.model.time.sleep"):
            with self.assertRaises(ModelError):
                client.complete([ModelMessage("user", "hi")])
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
