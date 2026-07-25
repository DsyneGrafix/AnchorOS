"""Load a complete S.P.A.T.I.A.L. profile through AnchorIntel's HTTP API."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def request(base_url: str, method: str, path: str, payload: dict | None = None):
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"X-Actor": "example-client"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = Request(f"{base_url.rstrip('/')}{path}", body, headers, method=method)
    try:
        with urlopen(req, timeout=10) as response:
            content = response.read()
            content_type = response.headers.get("Content-Type", "")
            return (
                json.loads(content)
                if "application/json" in content_type
                else content.decode("utf-8")
            )
    except HTTPError as exc:
        content = exc.read().decode("utf-8")
        raise SystemExit(f"API request failed ({exc.code}): {content}") from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("profile", type=Path, help="Complete engine-compatible JSON profile")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    args = parser.parse_args()

    opportunity = json.loads(args.profile.read_text(encoding="utf-8"))
    evidence = opportunity.pop("evidence")
    assessment_date = opportunity.get("assessment_date") or None
    created = request(args.base_url, "POST", "/v1/opportunities", opportunity)
    opportunity_id = created["opportunity_id"]
    for item in evidence:
        item["opportunity_id"] = opportunity_id
        request(args.base_url, "POST", "/v1/evidence", item)

    result = request(
        args.base_url,
        "POST",
        "/v1/assessments/run",
        {"opportunity_id": opportunity_id, "assessment_date": assessment_date},
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
