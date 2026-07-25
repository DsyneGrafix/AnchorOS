"""Dependency-light HTTP application for AnchorIntel API v1."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from email import policy
from email.parser import BytesParser
from typing import Any
from urllib.parse import parse_qs, urlparse

from .errors import ApiError
from .openapi import build_openapi
from .service import AnchorIntelService
from .web import (
    archive_detail,
    archive_form,
    dossier_detail,
    dossier_form,
    error_page,
    evidence_detail,
    evidence_form,
    knowledge_module_detail,
    knowledge_module_list,
    knowledge_review_detail,
    knowledge_review_form,
    opportunity_detail,
    opportunity_edit,
    opportunity_list,
    spatial_assessment_detail,
    spatial_assessment_form,
)


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

    @classmethod
    def binary(
        cls, status: int, value: bytes, content_type: str, headers: dict[str, str]
    ) -> "Response":
        return cls(status, value, {"Content-Type": content_type, **headers})


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

    def _multipart_body(
        self, headers: dict[str, str], body: bytes
    ) -> tuple[dict[str, str], dict[str, Any] | None]:
        content_type = headers.get("content-type", "")
        if "multipart/form-data" not in content_type.lower():
            raise ApiError(400, "invalid_multipart", "Expected multipart/form-data")
        if len(body) > self.service.max_file_size + 1024 * 1024:
            raise ApiError(413, "file_too_large", "Multipart request exceeds the upload limit")
        message = BytesParser(policy=policy.default).parsebytes(
            f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode()
            + body
        )
        if not message.is_multipart():
            raise ApiError(400, "invalid_multipart", "Multipart request could not be parsed")
        fields: dict[str, str] = {}
        upload: dict[str, Any] | None = None
        for part in message.iter_parts():
            if part.get_content_disposition() != "form-data":
                continue
            name = part.get_param("name", header="content-disposition")
            if not name:
                continue
            filename = part.get_filename()
            if filename is not None and name == "file":
                if upload is not None:
                    raise ApiError(400, "multiple_files", "Only one evidence file is allowed")
                upload = {
                    "filename": filename,
                    "content_type": part.get_content_type(),
                    "content": part.get_payload(decode=True) or b"",
                }
            elif filename is None:
                value = part.get_payload(decode=True) or b""
                fields[name] = value.decode(part.get_content_charset() or "utf-8")
        return fields, upload

    @staticmethod
    def _business_json_request(
        method: str, headers: dict[str, str]
    ) -> bool:
        if "application/json" in headers.get("content-type", "").lower():
            return True
        if method in {"PATCH", "DELETE"}:
            return True
        return "text/html" not in headers.get("accept", "").lower()

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
            business_json = self._business_json_request(method.upper(), normalized_headers)
            if (
                path == "/opportunities"
                or path.startswith("/opportunities/")
                or path.startswith("/knowledge-modules")
            ) and not business_json:
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
            return Response.json(200, {"status": "ok", "service": "anchorintel-api", "version": "0.6.0"})
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

        if method == "GET" and path == "/knowledge-modules":
            modules = self.service.list_knowledge_modules()
            if self._business_json_request(method, headers):
                return Response.json(200, {"items": modules})
            return Response.text(
                200, knowledge_module_list(modules), "text/html; charset=utf-8"
            )

        match = re.fullmatch(r"/knowledge-modules/([^/]+)", path)
        if match and method == "GET":
            module = self.service.get_knowledge_module(match.group(1))
            if self._business_json_request(method, headers):
                return Response.json(200, module)
            return Response.text(
                200, knowledge_module_detail(module), "text/html; charset=utf-8"
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

        match = re.fullmatch(r"/opportunities/([^/]+)/evidence/new", path)
        if match and method == "GET":
            return Response.text(
                200,
                evidence_form(self.service.get_opportunity(match.group(1))),
                "text/html; charset=utf-8",
            )

        match = re.fullmatch(r"/opportunities/([^/]+)/evidence", path)
        if match:
            opportunity_id = match.group(1)
            if method == "GET":
                include_archived = (
                    query.get("include_archived", ["false"])[0].lower() == "true"
                )
                records = self.service.list_managed_evidence(
                    opportunity_id, include_archived
                )
                if self._business_json_request(method, headers):
                    return Response.json(200, {"items": records})
                opportunity = self.service.get_opportunity(opportunity_id)
                return Response.text(
                    200,
                    opportunity_detail(opportunity, records),
                    "text/html; charset=utf-8",
                )
            if method == "POST":
                content_type = headers.get("content-type", "").lower()
                if "application/json" in content_type:
                    fields = self._json_body(body)
                    upload = None
                else:
                    fields, upload = self._multipart_body(headers, body)
                result = self.service.create_managed_evidence(
                    opportunity_id,
                    fields,
                    "anchorintel-ui" if actor == "anonymous" else actor,
                    upload,
                )
                location = (
                    f"/opportunities/{opportunity_id}/evidence/{result['evidence_id']}"
                )
                if "application/json" in content_type or self._business_json_request(
                    method, headers
                ):
                    return Response.json(201, result, {"Location": location})
                return Response.redirect(location)

        match = re.fullmatch(
            r"/opportunities/([^/]+)/evidence/([^/]+)/edit", path
        )
        if match:
            opportunity_id, evidence_id = match.groups()
            if method == "GET":
                return Response.text(
                    200,
                    evidence_form(
                        self.service.get_opportunity(opportunity_id),
                        self.service.get_managed_evidence(opportunity_id, evidence_id),
                    ),
                    "text/html; charset=utf-8",
                )
            if method == "POST":
                form = self._form_body(body)
                try:
                    revision = int(form.pop("revision", ""))
                except ValueError as exc:
                    raise ApiError(400, "invalid_revision", "Revision must be an integer") from exc
                result = self.service.update_managed_evidence(
                    opportunity_id,
                    evidence_id,
                    form,
                    "anchorintel-ui" if actor == "anonymous" else actor,
                    revision,
                )
                return Response.redirect(
                    f"/opportunities/{opportunity_id}/evidence/{result['evidence_id']}"
                )

        match = re.fullmatch(
            r"/opportunities/([^/]+)/evidence/([^/]+)/archive", path
        )
        if match and method == "POST":
            opportunity_id, evidence_id = match.groups()
            content_type = headers.get("content-type", "").lower()
            if "application/json" in content_type:
                request = self._json_body(body)
                raw_revision = request.get("revision")
            else:
                raw_revision = self._form_body(body).get("revision")
            try:
                revision = int(raw_revision) if raw_revision not in {None, ""} else self._expected_revision(headers)
            except (TypeError, ValueError) as exc:
                raise ApiError(400, "invalid_revision", "Revision must be an integer") from exc
            result = self.service.archive_managed_evidence(
                opportunity_id,
                evidence_id,
                "anchorintel-ui" if actor == "anonymous" else actor,
                revision,
            )
            if "application/json" in content_type or self._business_json_request(method, headers):
                return Response.json(200, result)
            return Response.redirect(
                f"/opportunities/{opportunity_id}?notice=Evidence+archived"
            )

        match = re.fullmatch(
            r"/opportunities/([^/]+)/evidence/([^/]+)/file", path
        )
        if match and method == "GET":
            opportunity_id, evidence_id = match.groups()
            file_path, evidence = self.service.evidence_file(opportunity_id, evidence_id)
            return Response.binary(
                200,
                file_path.read_bytes(),
                str(evidence.get("file_type") or "application/octet-stream"),
                {
                    "Content-Disposition": f'inline; filename="{evidence["file_name"]}"',
                    "X-Content-Type-Options": "nosniff",
                    "ETag": f'"sha256:{evidence["sha256"]}"',
                },
            )

        match = re.fullmatch(r"/opportunities/([^/]+)/evidence/([^/]+)", path)
        if match:
            opportunity_id, evidence_id = match.groups()
            if method == "GET":
                result = self.service.get_managed_evidence(opportunity_id, evidence_id)
                if self._business_json_request(method, headers):
                    return Response.json(200, result, {"ETag": f'"{result["revision"]}"'})
                return Response.text(
                    200,
                    evidence_detail(
                        self.service.get_opportunity(opportunity_id, include_archived=True), result
                    ),
                    "text/html; charset=utf-8",
                )
            if method == "PATCH":
                result = self.service.update_managed_evidence(
                    opportunity_id,
                    evidence_id,
                    self._json_body(body),
                    actor,
                    self._expected_revision(headers),
                )
                return Response.json(200, result, {"ETag": f'"{result["revision"]}"'})

        match = re.fullmatch(r"/opportunities/([^/]+)/knowledge-reviews/new", path)
        if match and method == "GET":
            opportunity_id = match.group(1)
            return Response.text(
                200,
                knowledge_review_form(
                    self.service.get_opportunity(opportunity_id),
                    self.service.list_knowledge_modules(),
                ),
                "text/html; charset=utf-8",
            )

        match = re.fullmatch(r"/opportunities/([^/]+)/knowledge-reviews", path)
        if match:
            opportunity_id = match.group(1)
            if method == "GET":
                reviews = self.service.list_knowledge_reviews(opportunity_id)
                if self._business_json_request(method, headers):
                    return Response.json(200, {"items": reviews})
                return Response.text(
                    200,
                    opportunity_detail(
                        self.service.get_opportunity(opportunity_id),
                        self.service.list_managed_evidence(
                            opportunity_id, include_archived=True
                        ),
                        knowledge_reviews=reviews,
                        knowledge_modules=self.service.list_knowledge_modules(),
                        assessments=self.service.list_operational_assessments(
                            opportunity_id
                        ),
                    ),
                    "text/html; charset=utf-8",
                )
            if method == "POST":
                content_type = headers.get("content-type", "").lower()
                request = (
                    self._json_body(body)
                    if "application/json" in content_type
                    else self._form_body(body)
                )
                module_id = str(request.get("module_id", "")).strip()
                if not module_id:
                    raise ApiError(
                        400, "invalid_knowledge_review", "module_id is required"
                    )
                result = self.service.run_knowledge_review(
                    opportunity_id,
                    module_id,
                    "anchorintel-ui" if actor == "anonymous" else actor,
                    str(request.get("review_status", "Completed")),
                )
                location = f"/opportunities/{opportunity_id}/knowledge-reviews/{result['review_id']}"
                if "application/json" in content_type or self._business_json_request(
                    method, headers
                ):
                    return Response.json(201, result, {"Location": location})
                return Response.redirect(location)

        match = re.fullmatch(
            r"/opportunities/([^/]+)/knowledge-reviews/([^/]+)/(complete|supersede)",
            path,
        )
        if match and method == "POST":
            opportunity_id, review_id, action = match.groups()
            content_type = headers.get("content-type", "").lower()
            request = (
                self._json_body(body)
                if "application/json" in content_type
                else self._form_body(body)
            )
            if action == "complete":
                raw_revision = request.get("revision")
                try:
                    revision = (
                        int(raw_revision)
                        if raw_revision not in {None, ""}
                        else self._expected_revision(headers)
                    )
                except (TypeError, ValueError) as exc:
                    raise ApiError(
                        400, "invalid_revision", "Revision must be an integer"
                    ) from exc
                result = self.service.complete_knowledge_review(
                    opportunity_id,
                    review_id,
                    "anchorintel-ui" if actor == "anonymous" else actor,
                    revision,
                )
            else:
                result = self.service.supersede_knowledge_review(
                    opportunity_id,
                    review_id,
                    "anchorintel-ui" if actor == "anonymous" else actor,
                )
            location = f"/opportunities/{opportunity_id}/knowledge-reviews/{result['review_id']}"
            if "application/json" in content_type or self._business_json_request(
                method, headers
            ):
                return Response.json(200, result, {"Location": location})
            return Response.redirect(location)

        match = re.fullmatch(
            r"/opportunities/([^/]+)/knowledge-reviews/([^/]+)", path
        )
        if match and method == "GET":
            opportunity_id, review_id = match.groups()
            result = self.service.get_knowledge_review(opportunity_id, review_id)
            if self._business_json_request(method, headers):
                return Response.json(
                    200, result, {"ETag": f'"{result["revision"]}"'}
                )
            return Response.text(
                200,
                knowledge_review_detail(
                    self.service.get_opportunity(opportunity_id, include_archived=True), result
                ),
                "text/html; charset=utf-8",
            )

        match = re.fullmatch(r"/opportunities/([^/]+)/assessments/new", path)
        if match and method == "GET":
            opportunity_id = match.group(1)
            return Response.text(
                200,
                spatial_assessment_form(
                    self.service.get_opportunity(opportunity_id, include_archived=True),
                    self.service.assessment_readiness(opportunity_id),
                ),
                "text/html; charset=utf-8",
            )

        match = re.fullmatch(r"/opportunities/([^/]+)/assessments", path)
        if match:
            opportunity_id = match.group(1)
            if method == "GET":
                records = self.service.list_operational_assessments(opportunity_id)
                if self._business_json_request(method, headers):
                    return Response.json(200, {"items": records})
                return Response.text(
                    200,
                    opportunity_detail(
                        self.service.get_opportunity(opportunity_id),
                        self.service.list_managed_evidence(
                            opportunity_id, include_archived=True
                        ),
                        knowledge_reviews=self.service.list_knowledge_reviews(
                            opportunity_id
                        ),
                        knowledge_modules=self.service.list_knowledge_modules(),
                        assessments=records,
                    ),
                    "text/html; charset=utf-8",
                )
            if method == "POST":
                content_type = headers.get("content-type", "").lower()
                request = (
                    self._json_body(body)
                    if "application/json" in content_type
                    else self._form_body(body)
                )
                result = self.service.run_spatial_assessment(
                    opportunity_id,
                    "anchorintel-ui" if actor == "anonymous" else actor,
                    str(request.get("knowledge_review_id", "")).strip() or None,
                    str(
                        request.get(
                            "reason", "S.P.A.T.I.A.L. assessment requested"
                        )
                    ),
                )
                location = (
                    f"/opportunities/{opportunity_id}/assessments/"
                    f"{result['assessment_id']}"
                )
                if "application/json" in content_type or self._business_json_request(
                    method, headers
                ):
                    return Response.json(201, result, {"Location": location})
                return Response.redirect(location)

        match = re.fullmatch(
            r"/opportunities/([^/]+)/assessments/([^/]+)/replay", path
        )
        if match and method == "POST":
            opportunity_id, assessment_id = match.groups()
            replay = self.service.replay_operational_assessment(
                opportunity_id,
                assessment_id,
                "anchorintel-ui" if actor == "anonymous" else actor,
            )
            if self._business_json_request(method, headers):
                return Response.json(200, replay)
            state = "matched" if replay["match"] else "did+not+match"
            return Response.redirect(
                f"/opportunities/{opportunity_id}/assessments/{assessment_id}"
                f"?notice=Replay+{state}+the+stored+hash"
            )

        match = re.fullmatch(
            r"/opportunities/([^/]+)/assessments/([^/]+)", path
        )
        if match and method == "GET":
            opportunity_id, assessment_id = match.groups()
            result = self.service.get_operational_assessment(
                opportunity_id, assessment_id
            )
            if self._business_json_request(method, headers):
                return Response.json(200, result)
            return Response.text(
                200,
                spatial_assessment_detail(
                    self.service.get_opportunity(opportunity_id, include_archived=True),
                    result,
                    query.get("notice", [""])[0],
                ),
                "text/html; charset=utf-8",
            )

        match = re.fullmatch(r"/opportunities/([^/]+)/dossiers/new", path)
        if match and method == "GET":
            opportunity_id = match.group(1)
            return Response.text(
                200,
                dossier_form(
                    self.service.get_opportunity(opportunity_id),
                    self.service.dossier_readiness(opportunity_id),
                ),
                "text/html; charset=utf-8",
            )

        match = re.fullmatch(r"/opportunities/([^/]+)/dossiers", path)
        if match:
            opportunity_id = match.group(1)
            if method == "GET":
                records = self.service.list_dossiers(opportunity_id)
                if self._business_json_request(method, headers):
                    return Response.json(200, {"items": records})
                return Response.text(
                    200,
                    opportunity_detail(
                        self.service.get_opportunity(opportunity_id),
                        self.service.list_managed_evidence(
                            opportunity_id, include_archived=True
                        ),
                        knowledge_reviews=self.service.list_knowledge_reviews(
                            opportunity_id
                        ),
                        knowledge_modules=self.service.list_knowledge_modules(),
                        assessments=self.service.list_operational_assessments(
                            opportunity_id
                        ),
                        dossiers=records,
                    ),
                    "text/html; charset=utf-8",
                )
            if method == "POST":
                content_type = headers.get("content-type", "").lower()
                request = (
                    self._json_body(body)
                    if "application/json" in content_type
                    else self._form_body(body)
                )
                result = self.service.generate_dossier(
                    opportunity_id,
                    "anchorintel-ui" if actor == "anonymous" else actor,
                    str(request.get("assessment_id", "")).strip() or None,
                )
                location = (
                    f"/opportunities/{opportunity_id}/dossiers/"
                    f"{result['dossier_id']}"
                )
                if "application/json" in content_type or self._business_json_request(
                    method, headers
                ):
                    return Response.json(201, result, {"Location": location})
                return Response.redirect(location)

        match = re.fullmatch(
            r"/opportunities/([^/]+)/dossiers/([^/]+)/replay", path
        )
        if match and method == "POST":
            opportunity_id, dossier_id = match.groups()
            replay = self.service.replay_dossier(
                opportunity_id,
                dossier_id,
                "anchorintel-ui" if actor == "anonymous" else actor,
            )
            if self._business_json_request(method, headers):
                return Response.json(200, replay)
            state = "matched" if replay["match"] else "did+not+match"
            return Response.redirect(
                f"/opportunities/{opportunity_id}/dossiers/{dossier_id}"
                f"?notice=Replay+{state}+all+stored+artifacts"
            )

        match = re.fullmatch(
            r"/opportunities/([^/]+)/dossiers/([^/]+)/(html|pdf|json)", path
        )
        if match and method == "GET":
            opportunity_id, dossier_id, artifact = match.groups()
            payload, content_type, filename = self.service.dossier_artifact(
                opportunity_id, dossier_id, artifact
            )
            return Response.binary(
                200,
                payload,
                content_type,
                {
                    "Content-Disposition": f'attachment; filename="{filename}"',
                },
            )

        match = re.fullmatch(r"/opportunities/([^/]+)/dossiers/([^/]+)", path)
        if match and method == "GET":
            opportunity_id, dossier_id = match.groups()
            result = self.service.get_dossier(opportunity_id, dossier_id)
            if self._business_json_request(method, headers):
                return Response.json(200, result)
            return Response.text(
                200,
                dossier_detail(
                    self.service.get_opportunity(opportunity_id, include_archived=True),
                    result,
                    query.get("notice", [""])[0],
                ),
                "text/html; charset=utf-8",
            )

        match = re.fullmatch(r"/opportunities/([^/]+)/archives/new", path)
        if match and method == "GET":
            opportunity_id = match.group(1)
            return Response.text(
                200,
                archive_form(
                    self.service.get_opportunity(opportunity_id),
                    self.service.archive_readiness(opportunity_id),
                ),
                "text/html; charset=utf-8",
            )

        match = re.fullmatch(r"/opportunities/([^/]+)/archives", path)
        if match:
            opportunity_id = match.group(1)
            if method == "GET":
                records = self.service.list_archives(opportunity_id)
                if self._business_json_request(method, headers):
                    return Response.json(200, {"items": records})
                return Response.text(
                    200,
                    opportunity_detail(
                        self.service.get_opportunity(
                            opportunity_id, include_archived=True
                        ),
                        self.service.list_managed_evidence(
                            opportunity_id, include_archived=True
                        ),
                        knowledge_reviews=self.service.list_knowledge_reviews(
                            opportunity_id
                        ),
                        knowledge_modules=self.service.list_knowledge_modules(),
                        assessments=self.service.list_operational_assessments(
                            opportunity_id
                        ),
                        dossiers=self.service.list_dossiers(opportunity_id),
                        archives=records,
                    ),
                    "text/html; charset=utf-8",
                )
            if method == "POST":
                content_type = headers.get("content-type", "").lower()
                request = (
                    self._json_body(body)
                    if "application/json" in content_type
                    else self._form_body(body)
                )
                result = self.service.create_archive(
                    opportunity_id,
                    "anchorintel-ui" if actor == "anonymous" else actor,
                    str(
                        request.get(
                            "reason", "BOOT-0020 lifecycle completion"
                        )
                    ),
                )
                location = (
                    f"/opportunities/{opportunity_id}/archives/"
                    f"{result['archive_id']}"
                )
                if "application/json" in content_type or self._business_json_request(
                    method, headers
                ):
                    return Response.json(201, result, {"Location": location})
                return Response.redirect(location)

        match = re.fullmatch(
            r"/opportunities/([^/]+)/archives/([^/]+)/download", path
        )
        if match and method == "GET":
            opportunity_id, archive_id = match.groups()
            payload, content_type, filename = self.service.archive_artifact(
                opportunity_id,
                archive_id,
                "anchorintel-ui" if actor == "anonymous" else actor,
            )
            return Response.binary(
                200,
                payload,
                content_type,
                {"Content-Disposition": f'attachment; filename="{filename}"'},
            )

        match = re.fullmatch(
            r"/opportunities/([^/]+)/archives/([^/]+)/replay", path
        )
        if match and method == "POST":
            opportunity_id, archive_id = match.groups()
            replay = self.service.replay_archive(
                opportunity_id,
                archive_id,
                "anchorintel-ui" if actor == "anonymous" else actor,
            )
            if self._business_json_request(method, headers):
                return Response.json(200, replay)
            return Response.redirect(
                f"/opportunities/{opportunity_id}/archives/{archive_id}"
                f"?notice=Archive+replay+{replay['result']}"
            )

        match = re.fullmatch(r"/opportunities/([^/]+)/archives/([^/]+)", path)
        if match and method == "GET":
            opportunity_id, archive_id = match.groups()
            result = self.service.get_archive(opportunity_id, archive_id)
            if self._business_json_request(method, headers):
                return Response.json(200, result)
            return Response.text(
                200,
                archive_detail(
                    self.service.get_opportunity(
                        opportunity_id, include_archived=True
                    ),
                    result,
                    query.get("notice", [""])[0],
                ),
                "text/html; charset=utf-8",
            )

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
            opportunity = self.service.get_opportunity(
                match.group(1), include_archived=True
            )
            return Response.text(
                200,
                opportunity_detail(
                    opportunity,
                    self.service.list_managed_evidence(
                        match.group(1), include_archived=True
                    ),
                    query.get("notice", [""])[0],
                    self.service.list_knowledge_reviews(match.group(1)),
                    self.service.list_knowledge_modules(),
                    self.service.list_operational_assessments(match.group(1)),
                    self.service.list_dossiers(match.group(1)),
                    self.service.list_archives(match.group(1)),
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
