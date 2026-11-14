from __future__ import annotations

import io
import json
import unittest
import urllib.error

from forgel.providers.github_api import GithubAPI, GithubAPIError


class Response:
    def __init__(self, body: dict) -> None:
        self._body = json.dumps(body).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> Response:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def opener(routes: dict[str, object]):
    def call(request, timeout: float = 0) -> Response:
        url = request.full_url
        for needle, payload in routes.items():
            if needle in url:
                if isinstance(payload, urllib.error.HTTPError):
                    raise payload
                return Response(payload)  # type: ignore[arg-type]
        raise AssertionError(f"unexpected URL: {url}")

    return call


def _http_error(code: int, message: str) -> urllib.error.HTTPError:
    body = io.BytesIO(json.dumps({"message": message}).encode("utf-8"))
    return urllib.error.HTTPError(
        "https://api.github.com/x", code, message, {}, body
    )


class GithubAPITest(unittest.TestCase):
    def test_create_repo_posts_to_the_org_endpoint(self) -> None:
        seen: dict = {}

        def recording(request, timeout: float = 0) -> Response:
            seen["url"] = request.full_url
            seen["method"] = request.get_method()
            seen["body"] = json.loads(request.data.decode("utf-8"))
            return Response(
                {
                    "full_name": "acme/billing",
                    "clone_url": "https://github.com/acme/billing.git",
                }
            )

        api = GithubAPI("tok", opener=recording)
        created = api.create_repo(
            "acme", "billing", private=True, description="Billing"
        )
        self.assertEqual(seen["url"], "https://api.github.com/orgs/acme/repos")
        self.assertEqual(seen["method"], "POST")
        self.assertEqual(seen["body"]["name"], "billing")
        self.assertEqual(seen["body"]["private"], True)
        self.assertEqual(seen["body"]["auto_init"], False)
        self.assertEqual(created["full_name"], "acme/billing")

    def test_check_state_green_pending_failed(self) -> None:
        green = GithubAPI(
            "tok",
            opener=opener(
                {
                    "check-runs": {
                        "check_runs": [
                            {"name": "test", "status": "completed", "conclusion": "success"}
                        ]
                    }
                }
            ),
        )
        self.assertEqual(green.check_state("o/r", "abc").state, "green")

        pending = GithubAPI(
            "tok",
            opener=opener(
                {
                    "check-runs": {
                        "check_runs": [
                            {"name": "test", "status": "in_progress", "conclusion": None}
                        ]
                    }
                }
            ),
        )
        self.assertEqual(pending.check_state("o/r", "abc").state, "pending")

        failed = GithubAPI(
            "tok",
            opener=opener(
                {
                    "check-runs": {
                        "check_runs": [
                            {"name": "test", "status": "completed", "conclusion": "failure"}
                        ]
                    }
                }
            ),
        )
        report = failed.check_state("o/r", "abc")
        self.assertEqual(report.state, "failed")
        self.assertEqual(report.failed, ["test"])

    def test_combined_status_fallback(self) -> None:
        api = GithubAPI(
            "tok",
            opener=opener(
                {
                    "check-runs": {"check_runs": []},
                    "commits/abc/status": {
                        "state": "success",
                        "total_count": 1,
                    },
                }
            ),
        )
        self.assertEqual(api.check_state("o/r", "abc").state, "green")

    def test_no_checks(self) -> None:
        api = GithubAPI(
            "tok",
            opener=opener(
                {
                    "check-runs": {"check_runs": []},
                    "commits/abc/status": {
                        "state": "pending",
                        "total_count": 0,
                    },
                }
            ),
        )
        self.assertEqual(api.check_state("o/r", "abc").state, "none")

    def test_merge_error_is_typed(self) -> None:
        api = GithubAPI(
            "tok",
            opener=opener({"merge": _http_error(405, "Pull Request is not mergeable")}),
        )
        with self.assertRaises(GithubAPIError) as raised:
            api.merge_pull("o/r", 1)
        self.assertEqual(raised.exception.status, 405)
        self.assertIn("not mergeable", raised.exception.message)

    def test_token_is_redacted(self) -> None:
        api = GithubAPI(
            "secret-token",
            opener=opener(
                {"merge": _http_error(405, "bad secret-token value")}
            ),
        )
        with self.assertRaises(GithubAPIError) as raised:
            api.merge_pull("o/r", 1)
        self.assertNotIn("secret-token", raised.exception.message)


if __name__ == "__main__":
    unittest.main()
