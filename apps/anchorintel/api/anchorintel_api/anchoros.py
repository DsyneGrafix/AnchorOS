"""AnchorOS lifecycle adapter for the AnchorIntel API service."""

from __future__ import annotations

from threading import Thread

from .app import AnchorIntelApplication
from .repository import Repository
from .server import create_server
from .service import AnchorIntelService


class AnchorIntelAnchorOSService:
    """Small lifecycle surface that can be registered by an AnchorOS module adapter."""

    service_id = "AOS-SVC-ANCHORINTEL-API"
    version = "0.3.0"

    def __init__(self, database_path="data/anchorintel.db", host="127.0.0.1", port=8080):
        self.database_path = database_path
        self.host = host
        self.port = port
        self.repository: Repository | None = None
        self.server = None
        self.thread: Thread | None = None
        self.state = "Discovered"

    def register(self) -> dict:
        self.state = "Registered"
        return self.health()

    def start(self) -> dict:
        if self.thread and self.thread.is_alive():
            return self.health()
        self.repository = Repository(self.database_path)
        application = AnchorIntelApplication(AnchorIntelService(self.repository))
        self.server = create_server(application, self.host, self.port)
        self.port = self.server.server_address[1]
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.state = "Running"
        return self.health()

    def stop(self) -> dict:
        self.state = "Stopping"
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
        if self.thread is not None:
            self.thread.join(timeout=5)
        if self.repository is not None:
            self.repository.close()
        self.state = "Stopped"
        return self.health()

    def health(self) -> dict:
        return {
            "service_id": self.service_id,
            "version": self.version,
            "state": self.state,
            "host": self.host,
            "port": self.port,
        }
