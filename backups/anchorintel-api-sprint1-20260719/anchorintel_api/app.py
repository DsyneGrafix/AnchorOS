"""Dependency-light HTTP application for AnchorIntel API v1."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, urlparse

from .errors import ApiError
from .openapi import build_openapi
from .service import AnchorIntelService
from .web import error_page, opportunity_detail, opportunity_edit, opportunity_list


@dataclass
class Response:
    status: int
    body: bytes
    headers: dict[str, str] = field(default_factory=dict)

    @classmethod
    def json(cls, status: int, value: Any, headers: dict[str, str] | None = None) -> "Response":
        payload = json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n"
        merged = {"Content-Type": "application/json; charset=utf-8"}
        merged.update(headers or {})
        return cls(status, payload, merged)

    @classmethod
    def text(
        cls, status: int, value: str, content_type: str = "text/plain; charset=utf-8"
    ) -> "Response":
        return cls(status, value.encode("utf-8"), {"Content-Type": content_type})

    @classmethod
    def redirect(cls, location: str, status: int = 303) -> "Response":
        return cls(status, b"", {"Location": location})


class AnchorIntelApplication:
    def __init__(self, service: AnchorIntelService):
        self.service = service

    @staticmethod
    def _json_body(body: bytes) -> dict[str, Any]:
        if not body:
            return {}
        try:
            value = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ApiError(400, "invalid_json", "Request body must be valid JSON") from exc
        if not isinstance(value, dict):
            raise ApiError(400, "invalid_json_shape", "Request body must be a JSON object")
        return value

    @staticmethod
    def _expected_revision(headers: dict[str, str]) -> int | None:
        raw = headers.get("if-match", "").strip().strip('"')
        if not raw:
            return None
        try:
            return int(raw)
        except ValueError as exc:
            raise ApiError(400, "invalid_if_match", "If-Match must contain an integer revision") from exc

    @staticmethod
    def _form_body(body: bytes) -> dict[str, str]:
        try:
            decoded = body.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ApiError(400, "invalid_form", "Form body must be UTF-8") from exc
        return {key: values[-1] for key, values in parse_qs(decoded, keep_blank_values=True).items()}

    def handle(
        self,
        method: str,
        target: str,
        headers: dict[str, str] | None = None,
        body: bytes = b"",
    ) -> Response:
        normalized_headers = {key.lower(): value for key, value in (headers or {}).items()}
        actor = normalized_headers.get("x-actor", "anonymous")
        request_id = normalized_headers.get("x-request-id", str(uuid.uuid4()))
        parsed = urlparse(target)
        path = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query)
        try:
            response = self._dispatch(
                method.upper(), path, query, normalized_headers, body, actor
            )
        except ApiError as exc:
            if path == "/opportunities" or path.startswith("/opportunities/"):
                response = Response.text(
                    exc.status, error_page(exc.status, exc.message), "text/html; charset=utf-8"
                )
            else:
                response = Response.json(
                    exc.status,
                    {
                        "error": {
                            "code": exc.code,
                            "message": exc.message,
                            "details": exc.details,
                        },
                        "request_id": request_id,
                    },
                )
        except Exception:
            response = Response.json(
                500,
                {
                    "error": {
                        "code": "internal_error",
                        "message": "The service could not complete the request",
                        "details": {},
                    },
                    "request_id": request_id,
                },
            )
        response.headers["X-Request-ID"] = request_id
        return response

    def _dispatch(self, method, path, query, headers, body, actor) -> Response:
        if method == "GET" and path == "/":
            return Response.redirect("/opportunities")
        if method == "GET" and path == "/health":
            return Response.json(200, {"status": "ok", "service": "anchorintel-api", "version": "0.1.0"})
        if method == "GET" and path == "/v1/openapi.json":
            return Response.json(200, build_openapi())

        if method == "GET" and path == "/opportunities":
            include_archived = query.get("include_archived", ["false"])[0].lower() == "true"
            notice = query.get("notice", [""])[0]
            return Response.text(
                200,
                opportunity_list(
                    self.service.list_opportunities(include_archived), include_archived, notice
                ),
                "text/html; charset=utf-8",
            )

        match = re.fullmatch(r"/opportunities/([^/]+)/edit", path)
        if match:
            opportunity_id = match.group(1)
            if method == "GET":
                return Response.text(
                    200,
                    opportunity_edit(self.service.get_opportunity(opportunity_id)),
                    "text/html; charset=utf-8",
                )
            if method == "POST":
                form = self._form_body(body)
                try:
                    revision = int(form.pop("revision", ""))
                except ValueError as exc:
                    raise ApiError(400, "invalid_revision", "Revision must be an integer") from exc
                result = self.service.edit_opportunity(
                    opportunity_id,
                    form,
                    "anchorintel-ui" if actor == "anonymous" else actor,
                    revision,
                )
                return Response.redirect(f"/opportunities/{result['opportunity_id']}")

        match = re.fullmatch(r"/opportunities/([^/]+)/archive", path)
        if match and method == "POST":
            self.service.archive_opportunity(
                match.group(1), "anchorintel-ui" if actor == "anonymous" else actor
            )
            return Response.redirect(
                "/opportunities?include_archived=true&notice=Opportunity+archived"
            )

        match = re.fullmatch(r"/opportunities/([^/]+)", path)
        if match and method == "GET":
            include_archived = query.get("include_archived", ["false"])[0].lower() == "true"
            return Response.text(
                200,
                opportunity_detail(
                    self.service.get_opportunity(match.group(1), include_archived)
                ),
                "text/html; charset=utf-8",
            )

        if path == "/v1/opportunities":
            if method == "POST":
                result = self.service.create_opportunity(self._json_body(body), actor)
                return Response.json(201, result, {"Location": f"/v1/opportunities/{result['opportunity_id']}"})
            if method == "GET":
                include_archived = query.get("include_archived", ["false"])[0].lower() == "true"
                return Response.json(200, {"items": self.service.list_opportunities(include_archived)})

        match = re.fullmatch(r"/v1/opportunities/([^/]+)", path)
        if match:
            opportunity_id = match.group(1)
            if method == "GET":
                result = self.service.get_opportunity(opportunity_id)
                return Response.json(200, result, {"ETag": f'"{result["revision"]}"'})
            if method == "PUT":
                result = self.service.update_opportunity(
                    opportunity_id,
                    self._json_body(body),
                    actor,
                    self._expected_revision(headers),
                )
                return Response.json(200, result, {"ETag": f'"{result["revision"]}"'})
            if method == "DELETE":
                return Response.json(200, self.service.archive_opportunity(opportunity_id, actor))

        if path == "/v1/evidence":
            if method == "POST":
                result = self.service.create_evidence(self._json_body(body), actor)
                return Response.json(201, result, {"Location": f"/v1/evidence/{result['evidence_id']}"})
            if method == "GET":
                opportunity_id = query.get("opportunity_id", [None])[0]
                return Response.json(200, {"items": self.service.list_evidence(opportunity_id)})

        match = re.fullmatch(r"/v1/evidence/([^/]+)/verify", path)
        if match and method == "POST":
            result = self.service.verify_evidence(
                match.group(1), self._json_body(body), actor, self._expected_revision(headers)
            )
            return Response.json(200, result, {"ETag": f'"{result["revision"]}"'})

        match = re.fullmatch(r"/v1/evidence/([^/]+)", path)
        if match:
            evidence_id = match.group(1)
            if method == "GET":
                result = self.service.get_evidence(evidence_id)
                return Response.json(200, result, {"ETag": f'"{result["revision"]}"'})
            if method == "PATCH":
                result = self.service.patch_evidence(
                    evidence_id,
                    self._json_body(body),
                    actor,
                    self._expected_revision(headers),
                )
                return Response.json(200, result, {"ETag": f'"{result["revision"]}"'})

        if path == "/v1/assessments/run" and method == "POST":
            request = self._json_body(body)
            opportunity_id = str(request.get("opportunity_id", "")).strip()
            if not opportunity_id:
                raise ApiError(400, "invalid_assessment", "opportunity_id is required")
            result = self.service.run_assessment(
                opportunity_id,
                actor,
                request.get("assessment_date"),
                reason=str(request.get("reason", "Assessment requested")),
            )
            return Response.json(201, result, {"Location": f"/v1/assessments/{result['assessment_id']}"})

        match = re.fullmatch(r"/v1/assessments/([^/]+)", path)
        if match and method == "GET":
            return Response.json(200, self.service.get_assessment(match.group(1)))

        if path in {"/v1/reports/json", "/v1/reports/markdown"} and method == "POST":
            request = self._json_body(body)
            assessment_id = str(request.get("assessment_id", "")).strip()
            if not assessment_id:
                raise ApiError(400, "invalid_report", "assessment_id is required")
            if path.endswith("/json"):
                return Response.json(200, self.service.report_json(assessment_id))
            return Response.text(
                200, self.service.report_markdown(assessment_id), "text/markdown; charset=utf-8"
            )

        if path == "/v1/lifecycle/reviews/due" and method == "GET":
            as_of = query.get("as_of", [None])[0]
            return Response.json(200, {"items": self.service.reviews_due(as_of)})
        if path == "/v1/lifecycle/revalidate" and method == "POST":
            result = self.service.revalidate(self._json_body(body), actor)
            return Response.json(201, result, {"Location": f"/v1/assessments/{result['assessment_id']}"})
        if path == "/v1/lifecycle/holds" and method == "GET":
            return Response.json(200, {"items": self.service.list_state("Hold")})
        if path == "/v1/lifecycle/monitors" and method == "GET":
            return Response.json(200, {"items": self.service.list_state("Monitor")})
        if path == "/v1/lifecycle/pursue" and method == "GET":
            return Response.json(200, {"items": self.service.list_state("Pursue")})

        if path == "/v1/admin/audit" and method == "GET":
            raw_limit = query.get("limit", ["100"])[0]
            try:
                limit = int(raw_limit)
            except ValueError as exc:
                raise ApiError(400, "invalid_limit", "limit must be an integer") from exc
            return Response.json(200, {"items": self.service.audit(limit)})

        raise ApiError(404, "route_not_found", f"No {method} route exists for {path}")
