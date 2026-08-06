"""Filesystem receipt store for deterministic AIN-201 proof runs."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonPipelineStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, pipeline_id: str, kind: str) -> Path:
        return self.root / f"{pipeline_id}.{kind}.json"

    def save_manifest(self, pipeline_id: str, payload: dict[str, Any]) -> Path:
        path = self._path(pipeline_id, "manifest")
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return path

    def save_receipt(self, pipeline_id: str, payload: dict[str, Any]) -> Path:
        path = self._path(pipeline_id, "receipt")
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return path

    def load_manifest(self, pipeline_id: str) -> dict[str, Any]:
        return json.loads(self._path(pipeline_id, "manifest").read_text(encoding="utf-8"))

    def load_receipt(self, pipeline_id: str) -> dict[str, Any]:
        return json.loads(self._path(pipeline_id, "receipt").read_text(encoding="utf-8"))
