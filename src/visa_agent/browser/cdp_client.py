"""Chrome DevTools Protocol client over WebSocket.

Uses the websocket-client library for all WebSocket protocol handling,
replacing a hand-rolled implementation that previously lived here.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from types import TracebackType
from typing import Any
from urllib.request import urlopen

import websocket


def list_debug_targets(port: int = 9222) -> list[dict[str, Any]]:
    with urlopen(f"http://127.0.0.1:{port}/json/list") as response:
        return json.loads(response.read().decode())


def find_target_websocket_url(url_substring: str = "", port: int = 9222) -> str:
    targets = list_debug_targets(port=port)
    for target in targets:
        if url_substring in (target.get("url") or ""):
            ws_url = target.get("webSocketDebuggerUrl")
            if ws_url:
                return str(ws_url)
    raise RuntimeError(
        f"No target found containing {url_substring!r} on port {port}"
    )


class CDPWebSocket:
    """A thin wrapper around websocket-client for CDP request/response.

    Usage:
        with CDPWebSocket(ws_url) as client:
            result = client.call("Runtime.evaluate", {"expression": "1+1"})
    """

    def __init__(self, ws_url: str) -> None:
        self.ws_url = ws_url
        self._ws: websocket.WebSocket | None = None
        self._message_id = 0

    def __enter__(self) -> "CDPWebSocket":
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def connect(self) -> None:
        self._ws = websocket.create_connection(self.ws_url, timeout=10)
        self._message_id = 0

    def close(self) -> None:
        if self._ws is not None:
            try:
                self._ws.close()
            finally:
                self._ws = None

    def call(
        self, method: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        assert self._ws is not None, "WebSocket not connected"
        self._message_id += 1
        message_id = self._message_id
        payload = {"id": message_id, "method": method, "params": params or {}}
        self._ws.send(json.dumps(payload))
        while True:
            raw = self._ws.recv()
            if not raw:
                raise RuntimeError("WebSocket closed by remote endpoint")
            message = json.loads(raw)
            if message.get("id") == message_id:
                return message


def capture_page_screenshot(
    ws_url: str,
    dest: Path,
    *,
    format: str = "png",
    capture_beyond_viewport: bool = False,
) -> Path:
    """Capture the current browser page screenshot through CDP."""
    with CDPWebSocket(ws_url) as client:
        client.call("Page.enable")
        response = client.call(
            "Page.captureScreenshot",
            {
                "format": format,
                "captureBeyondViewport": capture_beyond_viewport,
            },
        )

    data = response.get("result", {}).get("data")
    if not isinstance(data, str) or not data:
        raise RuntimeError("CDP screenshot response did not include image data")

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(base64.b64decode(data))
    return dest
