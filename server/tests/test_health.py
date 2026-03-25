import unittest

from fastapi.testclient import TestClient

from server.app.main import app


class HealthApiTests(unittest.TestCase):
    def test_healthz_returns_ok_payload(self) -> None:
        client = TestClient(app)

        response = client.get("/healthz")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "service": "databaseleaning-gui-api"})
