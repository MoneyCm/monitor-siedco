import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from sisc_heartbeat import build_payload, send_heartbeat


class SiscHeartbeatTests(unittest.TestCase):
    def test_builds_warning_payload_for_independent_and_missing_cutoffs(self):
        summary = {
            "Homicidios": {
                "2026": 10,
                "fecha_corte_2026": "08/06/2026",
                "estado": "OK",
            },
            "Capturas": {
                "2026": 20,
                "fecha_corte_2026": "10/06/2026",
                "estado": "OK",
            },
            "Recuperados": {
                "2026": 2,
                "fecha_corte_2026": None,
                "estado": "OK",
            },
        }
        with patch("sisc_heartbeat._load_json", side_effect=[summary, summary]):
            payload = build_payload(
                Path("actual.json"),
                Path("anterior.json"),
                now=datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc),
            )

        self.assertEqual(payload["status"], "CURRENT")
        self.assertEqual(payload["quality_status"], "WARNING")
        self.assertEqual(payload["source_cutoff_date"], "2026-06-10")
        self.assertEqual(payload["indicator_count"], 3)
        self.assertNotIn("last_change_detected_at", payload)
        self.assertTrue(any("cortes independientes" in item for item in payload["warnings"]))

    def test_failed_workflow_does_not_claim_a_success(self):
        with patch("sisc_heartbeat._load_json", return_value=None):
            payload = build_payload(
                Path("missing.json"),
                Path("previous.json"),
                outcome="failure",
                now=datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc),
            )

        self.assertEqual(payload["status"], "ERROR")
        self.assertEqual(payload["quality_status"], "ERROR")
        self.assertNotIn("last_success_at", payload)

    def test_missing_secret_is_a_soft_failure(self):
        self.assertFalse(
            send_heartbeat({"status": "CURRENT"}, service_key="", oidc_token="")
        )

    def test_oidc_identity_is_sent_as_bearer_token(self):
        class Response:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

        with patch("sisc_heartbeat.urlopen", return_value=Response()) as mocked_urlopen:
            sent = send_heartbeat(
                {"status": "CURRENT"},
                api_url="https://example.test/api",
                service_key="",
                oidc_token="short-lived-token",
            )

        request = mocked_urlopen.call_args.args[0]
        self.assertTrue(sent)
        self.assertEqual(request.get_header("Authorization"), "Bearer short-lived-token")
        self.assertIsNone(request.get_header("X-sisc-source-key"))


if __name__ == "__main__":
    unittest.main()
