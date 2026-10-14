import json
import sys
import unittest
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))

from tool_client import ModelToolClient, ToolServiceError


class ToolClientTests(unittest.TestCase):
    def test_detect_sends_only_case_id_and_server_token(self):
        requests = []

        def handler(request):
            requests.append(request)
            return httpx.Response(200, json={"case_id": "demo-001", "run_id": "run-1", "findings": []})

        client = ModelToolClient("http://model:8100", "secret", transport=httpx.MockTransport(handler))
        result = client.detect("demo-001")
        self.assertEqual(result["run_id"], "run-1")
        self.assertEqual(requests[0].url.path, "/detect")
        self.assertEqual(requests[0].headers["authorization"], "Bearer secret")
        self.assertEqual(json.loads(requests[0].content), {"case_id": "demo-001"})

    def test_classify_sends_ids_instead_of_raw_findings(self):
        requests = []

        def handler(request):
            requests.append(request)
            return httpx.Response(200, json={"case_id": "demo-001", "findings": []})

        client = ModelToolClient("http://model:8100", "secret", transport=httpx.MockTransport(handler))
        client.classify("demo-001", "run-1", ["c001"])
        self.assertEqual(requests[0].url.path, "/identify")
        self.assertEqual(json.loads(requests[0].content), {
            "case_id": "demo-001", "run_id": "run-1", "candidate_ids": ["c001"]
        })

    def test_missing_token_fails_closed(self):
        with self.assertRaises(ToolServiceError):
            ModelToolClient("http://model:8100", "")

    def test_http_failure_hides_server_path_and_body(self):
        def handler(request):
            return httpx.Response(500, text="D:/private/patient123/scan")

        client = ModelToolClient("http://model:8100", "secret", transport=httpx.MockTransport(handler))
        with self.assertRaises(ToolServiceError) as caught:
            client.detect("demo-001")
        self.assertIn("500", str(caught.exception))
        self.assertNotIn("private", str(caught.exception))

    def test_connection_error_hides_target_address(self):
        def handler(request):
            raise httpx.ConnectError("private-host/internal")

        client = ModelToolClient("http://model:8100", "secret", transport=httpx.MockTransport(handler))
        with self.assertRaises(ToolServiceError) as caught:
            client.detect("demo-001")
        self.assertNotIn("private-host", str(caught.exception))

    def test_unregistered_case_has_machine_readable_error_code(self):
        def handler(request):
            return httpx.Response(404, text="D:/private/patient123/scan")

        client = ModelToolClient("http://model:8100", "secret", transport=httpx.MockTransport(handler))
        with self.assertRaises(ToolServiceError) as caught:
            client.detect("demo-001")
        self.assertEqual(caught.exception.code, "CASE_NOT_REGISTERED")
        self.assertNotIn("private", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
