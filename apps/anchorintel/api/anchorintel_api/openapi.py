"""Static OpenAPI contract for AnchorIntel API v1."""

from __future__ import annotations


def build_openapi() -> dict:
    json_body = {
        "required": True,
        "content": {"application/json": {"schema": {"type": "object"}}},
    }
    opportunity_parameter = {
        "name": "opportunity_id",
        "in": "path",
        "required": True,
        "schema": {"type": "string"},
    }
    evidence_parameter = {
        "name": "evidence_id",
        "in": "path",
        "required": True,
        "schema": {"type": "string", "pattern": "^EV-[0-9]{6}$"},
    }
    evidence_json_body = {
        "required": True,
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/EvidenceInput"}
            }
        },
    }
    evidence_create_body = {
        "required": True,
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/EvidenceInput"}
            },
            "multipart/form-data": {
                "schema": {
                    "allOf": [
                        {"$ref": "#/components/schemas/EvidenceInput"},
                        {
                            "type": "object",
                            "properties": {
                                "file": {"type": "string", "format": "binary"}
                            },
                        },
                    ]
                }
            },
        },
    }
    common_evidence_errors = {
        "400": {"description": "Invalid evidence metadata or filename"},
        "404": {"description": "Opportunity or evidence not found"},
        "409": {"description": "Revision conflict or archived record"},
    }
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "AnchorIntel API",
            "version": "0.2.0",
            "description": (
                "AnchorOS service interface for opportunity and evidence lifecycle "
                "management. Sprint 2 adds managed evidence metadata, external file "
                "storage, SHA-256 hashing, archiving, audit events, and persisted "
                "Attach Evidence lifecycle behavior while preserving the existing v1 API."
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
            "/opportunities/{opportunity_id}/evidence": {
                "parameters": [opportunity_parameter],
                "get": {
                    "tags": ["Evidence"],
                    "summary": "List active evidence for an opportunity",
                    "parameters": [
                        {
                            "name": "include_archived",
                            "in": "query",
                            "schema": {"type": "boolean", "default": False},
                        }
                    ],
                    "responses": {
                        "200": {"description": "Evidence collection"},
                        "404": {"description": "Opportunity not found"},
                    },
                },
                "post": {
                    "tags": ["Evidence"],
                    "summary": "Create metadata-only or file-backed evidence",
                    "requestBody": evidence_create_body,
                    "responses": {
                        "201": {"description": "Evidence created"},
                        **common_evidence_errors,
                        "413": {"description": "Uploaded file exceeds the configured limit"},
                    },
                },
            },
            "/opportunities/{opportunity_id}/evidence/{evidence_id}": {
                "parameters": [opportunity_parameter, evidence_parameter],
                "get": {
                    "tags": ["Evidence"],
                    "summary": "Retrieve an evidence record",
                    "responses": {
                        "200": {"description": "Evidence record"},
                        "404": {"description": "Opportunity or evidence not found"},
                    },
                },
                "patch": {
                    "tags": ["Evidence"],
                    "summary": "Revise evidence metadata",
                    "parameters": [
                        {
                            "name": "If-Match",
                            "in": "header",
                            "schema": {"type": "integer"},
                            "description": "Expected evidence revision",
                        }
                    ],
                    "requestBody": evidence_json_body,
                    "responses": {"200": {"description": "Evidence updated"}, **common_evidence_errors},
                },
            },
            "/opportunities/{opportunity_id}/evidence/{evidence_id}/archive": {
                "parameters": [opportunity_parameter, evidence_parameter],
                "post": {
                    "tags": ["Evidence"],
                    "summary": "Recoverably archive evidence",
                    "requestBody": {
                        "required": False,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {"revision": {"type": "integer"}},
                                }
                            }
                        },
                    },
                    "responses": {"200": {"description": "Evidence archived"}, **common_evidence_errors},
                },
            },
            "/opportunities/{opportunity_id}/evidence/{evidence_id}/file": {
                "parameters": [opportunity_parameter, evidence_parameter],
                "get": {
                    "tags": ["Evidence"],
                    "summary": "View or download the attached evidence file",
                    "responses": {
                        "200": {
                            "description": "Stored evidence file",
                            "content": {"application/octet-stream": {"schema": {"type": "string", "format": "binary"}}},
                        },
                        "404": {"description": "Record or attached file not found"},
                    },
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
                    "summary": "Read the application audit log",
                    "responses": {"200": {"description": "Audit records"}},
                }
            },
            "/v1/openapi.json": {
                "get": {"summary": "OpenAPI contract", "responses": {"200": {"description": "Contract"}}}
            },
        },
        "components": {
            "schemas": {
                "EvidenceInput": {
                    "type": "object",
                    "required": ["title", "evidence_type", "evidence_status", "evidence_confidence"],
                    "properties": {
                        "evidence_id": {"type": "string", "pattern": "^EV-[0-9]{6}$"},
                        "title": {"type": "string", "minLength": 1},
                        "evidence_type": {
                            "type": "string",
                            "enum": ["Document", "Dataset", "Web Source", "Field Observation", "Photograph", "Correspondence", "Regulatory Record", "Financial Record", "Technical Record", "Other"],
                        },
                        "source": {"type": "string"},
                        "source_date": {"type": "string", "format": "date"},
                        "date_collected": {"type": "string", "format": "date"},
                        "description": {"type": "string"},
                        "evidence_status": {
                            "type": "string",
                            "enum": ["Collected", "Under Review", "Accepted", "Questioned", "Superseded"],
                        },
                        "evidence_confidence": {
                            "type": "string",
                            "enum": ["Unknown", "Low", "Moderate", "High", "Verified"],
                        },
                        "notes": {"type": "string"},
                    },
                }
            }
        },
    }
