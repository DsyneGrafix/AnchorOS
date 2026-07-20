"""Static OpenAPI contract for AnchorIntel API v1."""

from __future__ import annotations


def build_openapi() -> dict:
    json_body = {
        "required": True,
        "content": {"application/json": {"schema": {"type": "object"}}},
    }
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "AnchorIntel API",
            "version": "0.1.0",
            "description": (
                "AnchorOS service interface for the complete S.P.A.T.I.A.L. "
                "infrastructure opportunity assessment lifecycle."
            ),
        },
        "servers": [{"url": "http://127.0.0.1:8080"}],
        "tags": [
            {"name": "Opportunities"},
            {"name": "Evidence"},
            {"name": "Assessments"},
            {"name": "Reports"},
            {"name": "Lifecycle"},
            {"name": "Administration"},
        ],
        "paths": {
            "/health": {
                "get": {"summary": "Service health", "responses": {"200": {"description": "Healthy"}}}
            },
            "/v1/opportunities": {
                "get": {
                    "tags": ["Opportunities"],
                    "summary": "List opportunities",
                    "responses": {"200": {"description": "Opportunity collection"}},
                },
                "post": {
                    "tags": ["Opportunities"],
                    "summary": "Create an opportunity",
                    "requestBody": json_body,
                    "responses": {"201": {"description": "Created"}},
                },
            },
            "/v1/opportunities/{id}": {
                "parameters": [
                    {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}
                ],
                "get": {
                    "tags": ["Opportunities"],
                    "summary": "Retrieve an opportunity",
                    "responses": {"200": {"description": "Opportunity"}},
                },
                "put": {
                    "tags": ["Opportunities"],
                    "summary": "Replace an opportunity record",
                    "requestBody": json_body,
                    "responses": {"200": {"description": "Updated"}},
                },
                "delete": {
                    "tags": ["Opportunities"],
                    "summary": "Archive an opportunity",
                    "responses": {"200": {"description": "Archived"}},
                },
            },
            "/v1/evidence": {
                "get": {
                    "tags": ["Evidence"],
                    "summary": "List evidence, optionally by opportunity",
                    "responses": {"200": {"description": "Evidence collection"}},
                },
                "post": {
                    "tags": ["Evidence"],
                    "summary": "Create evidence",
                    "requestBody": json_body,
                    "responses": {"201": {"description": "Created"}},
                },
            },
            "/v1/evidence/{id}": {
                "parameters": [
                    {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}
                ],
                "get": {
                    "tags": ["Evidence"],
                    "summary": "Retrieve evidence",
                    "responses": {"200": {"description": "Evidence"}},
                },
                "patch": {
                    "tags": ["Evidence"],
                    "summary": "Update or reclassify evidence without promotion",
                    "requestBody": json_body,
                    "responses": {"200": {"description": "Updated"}},
                },
            },
            "/v1/evidence/{id}/verify": {
                "parameters": [
                    {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}
                ],
                "post": {
                    "tags": ["Evidence"],
                    "summary": "Promote Assumption to Supported or Supported to Verified",
                    "requestBody": json_body,
                    "responses": {"200": {"description": "Promoted"}},
                },
            },
            "/v1/assessments/run": {
                "post": {
                    "tags": ["Assessments"],
                    "summary": "Run a S.P.A.T.I.A.L. assessment",
                    "requestBody": json_body,
                    "responses": {"201": {"description": "Assessment completed"}},
                }
            },
            "/v1/assessments/{id}": {
                "parameters": [
                    {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}
                ],
                "get": {
                    "tags": ["Assessments"],
                    "summary": "Retrieve an assessment",
                    "responses": {"200": {"description": "Assessment"}},
                },
            },
            "/v1/reports/json": {
                "post": {
                    "tags": ["Reports"],
                    "summary": "Generate the stored JSON decision report",
                    "requestBody": json_body,
                    "responses": {"200": {"description": "JSON report"}},
                }
            },
            "/v1/reports/markdown": {
                "post": {
                    "tags": ["Reports"],
                    "summary": "Generate the stored Markdown decision report",
                    "requestBody": json_body,
                    "responses": {
                        "200": {
                            "description": "Markdown report",
                            "content": {"text/markdown": {"schema": {"type": "string"}}},
                        }
                    },
                }
            },
            "/v1/lifecycle/reviews/due": {
                "get": {
                    "tags": ["Lifecycle"],
                    "summary": "List opportunities due for review",
                    "responses": {"200": {"description": "Due reviews"}},
                }
            },
            "/v1/lifecycle/revalidate": {
                "post": {
                    "tags": ["Lifecycle"],
                    "summary": "Revalidate an assessed opportunity",
                    "requestBody": json_body,
                    "responses": {"201": {"description": "Revalidated"}},
                }
            },
            "/v1/lifecycle/holds": {
                "get": {
                    "tags": ["Lifecycle"],
                    "summary": "List Hold opportunities",
                    "responses": {"200": {"description": "Hold queue"}},
                }
            },
            "/v1/lifecycle/monitors": {
                "get": {
                    "tags": ["Lifecycle"],
                    "summary": "List Monitor opportunities",
                    "responses": {"200": {"description": "Monitor queue"}},
                }
            },
            "/v1/lifecycle/pursue": {
                "get": {
                    "tags": ["Lifecycle"],
                    "summary": "List Pursue opportunities",
                    "responses": {"200": {"description": "Pursue queue"}},
                }
            },
            "/v1/admin/audit": {
                "get": {
                    "tags": ["Administration"],
                    "summary": "Read the append-only audit trail",
                    "responses": {"200": {"description": "Audit records"}},
                }
            },
            "/v1/openapi.json": {
                "get": {"summary": "OpenAPI contract", "responses": {"200": {"description": "Contract"}}}
            },
        },
    }
