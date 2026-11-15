"""Health endpoint tests. They use the Django test client and need no
Postgres server or S3 endpoint."""
from django.test import TestCase


class HealthEndpointTests(TestCase):
    def test_healthz_returns_ok(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_healthz_is_registered_in_urlconf(self):
        from django.urls import reverse

        self.assertEqual(reverse("healthz"), "/healthz")
