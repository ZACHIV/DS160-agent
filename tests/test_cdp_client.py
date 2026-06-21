from __future__ import annotations

import unittest
from pathlib import Path
import tempfile
from unittest.mock import patch

from visa_agent.browser.cdp_client import (
    CDPWebSocket,
    capture_page_screenshot,
    list_debug_targets,
    find_target_websocket_url,
)


class CDPClientTests(unittest.TestCase):
    def test_cdp_websocket_uses_websocket_client_library(self) -> None:
        ws = CDPWebSocket("ws://127.0.0.1:9222/devtools/page/test")
        self.assertIsNone(ws._ws)
        self.assertEqual(ws.ws_url, "ws://127.0.0.1:9222/devtools/page/test")
        self.assertEqual(ws._message_id, 0)

    def test_call_requires_connection(self) -> None:
        ws = CDPWebSocket("ws://127.0.0.1:9222/devtools/page/test")
        with self.assertRaises(AssertionError):
            ws.call("Runtime.evaluate", {"expression": "1+1"})

    def test_connect_and_close_are_idempotent(self) -> None:
        # close() without connect() should be safe
        ws = CDPWebSocket("ws://127.0.0.1:9222/devtools/page/test")
        ws.close()
        self.assertIsNone(ws._ws)

    def test_list_debug_targets_is_callable(self) -> None:
        self.assertTrue(callable(list_debug_targets))

    def test_find_target_websocket_url_is_callable(self) -> None:
        self.assertTrue(callable(find_target_websocket_url))

    def test_capture_page_screenshot_writes_decoded_image(self) -> None:
        class FakeCDP:
            def __init__(self, ws_url: str) -> None:
                self.ws_url = ws_url

            def __enter__(self) -> "FakeCDP":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def call(self, method: str, params: dict | None = None) -> dict:
                if method == "Page.captureScreenshot":
                    return {"result": {"data": "aGVsbG8="}}
                return {"result": {}}

        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "shot.png"
            with patch("visa_agent.browser.cdp_client.CDPWebSocket", FakeCDP):
                result = capture_page_screenshot("ws://test", dest)

            self.assertEqual(result, dest)
            self.assertEqual(dest.read_bytes(), b"hello")


if __name__ == "__main__":
    unittest.main()
