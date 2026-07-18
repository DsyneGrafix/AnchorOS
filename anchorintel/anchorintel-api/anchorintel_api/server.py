"""Standard-library HTTP transport for AnchorIntel API."""

from __future__ import annotations

import argparse
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .app import AnchorIntelApplication
from .repository import Repository
from .service import AnchorIntelService


def handler_for(application: AnchorIntelApplication):
    class Handler(BaseHTTPRequestHandler):
        server_version = "AnchorIntelAPI/0.1.0"

        def _serve(self):
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length) if length else b""
            response = application.handle(
                self.command, self.path, dict(self.headers.items()), body
            )
            self.send_response(response.status)
            for name, value in response.headers.items():
                self.send_header(name, value)
            self.send_header("Content-Length", str(len(response.body)))
            self.end_headers()
            self.wfile.write(response.body)

        do_GET = _serve
        do_POST = _serve
        do_PUT = _serve
        do_PATCH = _serve
        do_DELETE = _serve

        def log_message(self, format, *args):
            if os.environ.get("ANCHORINTEL_ACCESS_LOG", "1") != "0":
                super().log_message(format, *args)

    return Handler


def create_server(
    application: AnchorIntelApplication, host: str = "127.0.0.1", port: int = 8080
) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), handler_for(application))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the AnchorIntel API v1 service")
    parser.add_argument("--host", default=os.environ.get("ANCHORINTEL_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("ANCHORINTEL_PORT", "8080")))
    parser.add_argument(
        "--database",
        default=os.environ.get("ANCHORINTEL_DATABASE", "data/anchorintel.db"),
    )
    args = parser.parse_args(argv)

    repository = Repository(args.database)
    application = AnchorIntelApplication(AnchorIntelService(repository))
    server = create_server(application, args.host, args.port)
    bound_port = server.server_address[1]
    print(f"AnchorIntel API v1 listening on http://{args.host}:{bound_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        repository.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
