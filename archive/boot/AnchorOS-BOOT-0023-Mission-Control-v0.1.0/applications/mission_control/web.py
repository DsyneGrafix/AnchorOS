from __future__ import annotations

import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Any
from urllib.parse import parse_qs, urlparse

from .runtime import MissionControlRuntime


class MissionControlServer:
    """Dependency-free local HTTP server for the Mission Control dashboard."""

    def __init__(self, runtime: MissionControlRuntime, host: str, port: int) -> None:
        self.runtime = runtime
        self.host = host
        self.requested_port = port
        self.port = port
        self._server: ThreadingHTTPServer | None = None
        self._thread: Thread | None = None
        self._base = Path(__file__).resolve().parent

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def start(self) -> None:
        if self._server is not None:
            return
        handler = self._make_handler()
        last_error: OSError | None = None
        for candidate in range(self.requested_port, self.requested_port + 11):
            try:
                self._server = ThreadingHTTPServer((self.host, candidate), handler)
                self.port = candidate
                break
            except OSError as error:
                last_error = error
        if self._server is None:
            raise RuntimeError("Mission Control could not bind ports 8080-8090") from last_error
        self._thread = Thread(
            target=self._server.serve_forever,
            name="anchoros-mission-control",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        server = self._server
        if server is None:
            return
        server.shutdown()
        server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=3)
        self._server = None
        self._thread = None

    def _make_handler(self) -> type[BaseHTTPRequestHandler]:
        runtime = self.runtime
        base = self._base

        class Handler(BaseHTTPRequestHandler):
            server_version = "AnchorOSMissionControl/0.1"

            def log_message(self, format: str, *args: object) -> None:
                return

            def do_GET(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                path = parsed.path
                if path == "/":
                    self._send_file(base / "templates" / "dashboard.html", "text/html; charset=utf-8")
                    return
                if path.startswith("/static/"):
                    target = (base / path.lstrip("/")).resolve()
                    static_root = (base / "static").resolve()
                    if static_root not in target.parents:
                        self.send_error(HTTPStatus.FORBIDDEN)
                        return
                    content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
                    self._send_file(target, content_type)
                    return
                snapshot = runtime.snapshot()
                routes: dict[str, Any] = {
                    "/api/v1/status": snapshot,
                    "/api/v1/health": snapshot.get("health", {}),
                    "/api/v1/services": snapshot.get("services", []),
                    "/api/v1/frameworks": snapshot.get("frameworks", []),
                    "/api/v1/applications": snapshot.get("applications", []),
                    "/api/v1/manifest": snapshot.get("manifest", {}),
                    "/api/v1/audit": snapshot.get("audit", []),
                    "/api/v1/pipeline": snapshot.get("pipeline", {}),
                }
                if path == "/api/v1/events":
                    query = parse_qs(parsed.query)
                    try:
                        after = int(query.get("after", ["0"])[0])
                    except ValueError:
                        after = 0
                    self._send_json({"events": runtime.events(after=after), "status": snapshot})
                    return
                if path in routes:
                    self._send_json(routes[path])
                    return
                self.send_error(HTTPStatus.NOT_FOUND)

            def _send_json(self, payload: Any) -> None:
                body = json.dumps(payload, indent=2, default=str).encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def _send_file(self, path: Path, content_type: str) -> None:
                if not path.is_file():
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                body = path.read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

        return Handler
