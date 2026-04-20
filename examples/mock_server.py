"""Local HTTP server that mimics the TruLayer ingestion + feedback endpoints.

Used by the demos and smoke tests to observe the end-to-end data flow
without needing a real backend. Stores every received payload in memory
and exposes it via `get_received()`.
"""
from __future__ import annotations

import contextlib
import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

_received: dict[str, list[dict[str, Any]]] = {"batches": [], "feedback": []}
_lock = threading.Lock()


def get_received() -> dict[str, list[dict[str, Any]]]:
    with _lock:
        return {"batches": list(_received["batches"]), "feedback": list(_received["feedback"])}


def reset() -> None:
    with _lock:
        _received["batches"].clear()
        _received["feedback"].clear()


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("content-length", "0"))
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            return

        with _lock:
            if self.path.startswith("/v1/ingest/batch"):
                _received["batches"].append(payload)
            elif self.path.startswith("/v1/feedback"):
                _received["feedback"].append(payload)
            else:
                self.send_response(404)
                self.end_headers()
                return

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return  # quiet


@contextlib.contextmanager
def run_mock_server():
    """Context manager: start server on a free port, yield its base URL."""
    reset()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    server = HTTPServer(("127.0.0.1", port), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2.0)


if __name__ == "__main__":
    import time

    with run_mock_server() as url:
        print(f"Mock TruLayer ingestion server listening on {url}")
        print("Point TRULAYER_ENDPOINT at this URL to observe demo traffic.")
        print("Press Ctrl-C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nReceived:")
            print(json.dumps(get_received(), indent=2, default=str))
