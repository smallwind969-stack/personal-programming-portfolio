import os
import unittest
from unittest.mock import MagicMock, patch

import agent.llm_client as llm_client
from agent.llm_client import LLMClientError, generate_with_llm_api


class LLMClientTests(unittest.TestCase):
    def test_missing_api_key_raises_error(self):
        env = {key: value for key, value in os.environ.items() if key not in ("LLM_API_KEY", "OPENAI_API_KEY")}
        with patch.dict(os.environ, env, clear=True), patch.object(llm_client, "llm_api_config", None):
            with self.assertRaises(LLMClientError):
                generate_with_llm_api("hello")

    def test_reads_api_key_from_project_config(self):
        config = MagicMock()
        config.API_KEY = "test-key"
        config.API_BASE = "https://example.test/v1"
        config.MODEL = "test-model"
        config.TIMEOUT = 10
        config.TEMPERATURE = 0.1
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"choices":[{"message":{"content":"ok"}}]}'

        env = {key: value for key, value in os.environ.items() if key not in ("LLM_API_KEY", "OPENAI_API_KEY")}
        with patch.dict(os.environ, env, clear=True), \
                patch.object(llm_client, "llm_api_config", config), \
                patch("agent.llm_client.urllib.request.urlopen", return_value=response) as urlopen:
            text, metadata = generate_with_llm_api("hello")

        self.assertEqual(text, "ok")
        self.assertEqual(metadata["api_base"], "https://example.test/v1")
        self.assertEqual(metadata["model"], "test-model")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.headers["User-agent"], "curl/8.0.0")
        self.assertEqual(request.headers["Accept"], "application/json")


if __name__ == "__main__":
    unittest.main()
