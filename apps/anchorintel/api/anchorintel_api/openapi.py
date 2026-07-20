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
    module_parameter = {
        "name": "module_id",
        "in": "path",
        "required": True,
        "schema": {"type": "string", "pattern": "^AKM-[A-Z0-9]+-[A-Z0-9]+-[0-9]{3}$"},
    }
    review_parameter = {
        "name": "review_id",
        "in": "path",
        "required": True,
        "schema": {"type": "string", "pattern": "^KR-[0-9]{6}$"},
    }
    assessment_parameter = {
        "name": "assessment_id",
        "in": "path",
        "required": True,
        "schema": {"type": "string", "pattern": "^AS-[0-9]{6}$"},
    }
    dossier_parameter = {
        "name": "dossier_id",
        "in": "path",
        "required": True,
        "schema": {"type": "string", "pattern": "^ED-[0-9]{6}$"},
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
            "version": "0.5.0",
            "description": (
                "AnchorOS service interface for opportunity, evidence, deterministic "
                "Knowledge Review, S.P.A.T.I.A.L. assessment, and Executive Opportunity "
                "Dossier lifecycle management. Sprint 5 adds ED identifiers, persisted "
                "report snapshots, deterministic HTML/PDF/JSON exports, replay hashes, "
                "and dynamic dossier lifecycle eligibility."
            ),
        },
        "servers": [{"url": "http://127.0.0.1:8080"}],
        "tags": [
            {"name": "Opportunities"},
            {"name": "Evidence"},
            {"name": "Knowledge"},
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
            "/knowledge-modules": {
                "get": {
                    "tags": ["Knowledge"],
                    "summary": "List active version-controlled Knowledge Modules",
                    "responses": {"200": {"description": "Knowledge Module collection"}},
                }
            },
            "/knowledge-modules/{module_id}": {
                "parameters": [module_parameter],
                "get": {
                    "tags": ["Knowledge"],
                    "summary": "Retrieve a Knowledge Module definition and integrity hash",
                    "responses": {
                        "200": {"description": "Knowledge Module"},
                        "404": {"description": "Knowledge Module not found"},
                    },
                },
            },
            "/opportunities/{opportunity_id}/knowledge-reviews": {
                "parameters": [opportunity_parameter],
                "get": {
                    "tags": ["Knowledge"],
                    "summary": "List persisted Knowledge Reviews with dynamic staleness",
                    "responses": {
                        "200": {"description": "Knowledge Review collection"},
                        "404": {"description": "Opportunity not found"},
                    },
                },
                "post": {
                    "tags": ["Knowledge"],
                    "summary": "Run a deterministic Knowledge Module review",
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/KnowledgeReviewRun"}}},
                    },
                    "responses": {
                        "201": {"description": "Knowledge Review persisted"},
                        "400": {"description": "Invalid review request"},
                        "404": {"description": "Opportunity or module not found"},
                        "409": {"description": "Opportunity archived or module inactive"},
                        "422": {"description": "No deterministic module executor is installed"},
                    },
                },
            },
            "/opportunities/{opportunity_id}/knowledge-reviews/{review_id}": {
                "parameters": [opportunity_parameter, review_parameter],
                "get": {
                    "tags": ["Knowledge"],
                    "summary": "Retrieve a Knowledge Review and evidence trace",
                    "responses": {
                        "200": {"description": "Knowledge Review"},
                        "404": {"description": "Opportunity or review not found"},
                    },
                },
            },
            "/opportunities/{opportunity_id}/knowledge-reviews/{review_id}/complete": {
                "parameters": [opportunity_parameter, review_parameter],
                "post": {
                    "tags": ["Knowledge"],
                    "summary": "Complete a current draft Knowledge Review",
                    "requestBody": {"required": False, "content": {"application/json": {"schema": {"type": "object", "properties": {"revision": {"type": "integer"}}}}}},
                    "responses": {
                        "200": {"description": "Review completed"},
                        "404": {"description": "Review not found"},
                        "409": {"description": "Review stale, superseded, or revision conflict"},
                    },
                },
            },
            "/opportunities/{opportunity_id}/knowledge-reviews/{review_id}/supersede": {
                "parameters": [opportunity_parameter, review_parameter],
                "post": {
                    "tags": ["Knowledge"],
                    "summary": "Rerun the module over current inputs and supersede the prior review",
                    "responses": {
                        "200": {"description": "Successor review persisted"},
                        "404": {"description": "Review, opportunity, or module not found"},
                        "409": {"description": "Review is not active"},
                    },
                },
            },
            "/opportunities/{opportunity_id}/assessments": {
                "parameters": [opportunity_parameter],
                "get": {
                    "tags": ["Assessments"],
                    "summary": "List persisted operational assessments with dynamic staleness",
                    "responses": {
                        "200": {"description": "Assessment collection"},
                        "404": {"description": "Opportunity not found"},
                    },
                },
                "post": {
                    "tags": ["Assessments"],
                    "summary": "Run the installed S.P.A.T.I.A.L. engine over current persisted lifecycle inputs",
                    "requestBody": {
                        "required": False,
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/SpatialAssessmentRun"}}},
                    },
                    "responses": {
                        "201": {"description": "AS assessment persisted"},
                        "404": {"description": "Opportunity or Knowledge Review not found"},
                        "409": {"description": "Inputs missing, incomplete, archived, or stale"},
                        "422": {"description": "Derived snapshot violates the engine contract"},
                    },
                },
            },
            "/opportunities/{opportunity_id}/assessments/{assessment_id}": {
                "parameters": [opportunity_parameter, assessment_parameter],
                "get": {
                    "tags": ["Assessments"],
                    "summary": "Retrieve a traceable operational assessment",
                    "responses": {
                        "200": {"description": "Operational assessment"},
                        "404": {"description": "Assessment not found for opportunity"},
                    },
                },
            },
            "/opportunities/{opportunity_id}/assessments/{assessment_id}/replay": {
                "parameters": [opportunity_parameter, assessment_parameter],
                "post": {
                    "tags": ["Assessments"],
                    "summary": "Replay the immutable stored snapshot and compare its hash",
                    "responses": {
                        "200": {"description": "Replay comparison"},
                        "404": {"description": "Assessment not found for opportunity"},
                        "409": {"description": "Stored snapshot cannot be replayed"},
                    },
                },
            },
            "/opportunities/{opportunity_id}/dossiers": {
                "parameters": [opportunity_parameter],
                "get": {
                    "tags": ["Reports"],
                    "summary": "List persisted Executive Opportunity Dossiers",
                    "responses": {
                        "200": {"description": "Dossier collection"},
                        "404": {"description": "Opportunity not found"},
                    },
                },
                "post": {
                    "tags": ["Reports"],
                    "summary": "Generate a deterministic dossier from current persisted records",
                    "requestBody": {
                        "required": False,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/DossierGenerate"}
                            }
                        },
                    },
                    "responses": {
                        "201": {"description": "Dossier persisted or idempotently reused"},
                        "404": {"description": "Opportunity or assessment not found"},
                        "409": {"description": "Current persisted inputs are not report-ready"},
                    },
                },
            },
            "/opportunities/{opportunity_id}/dossiers/{dossier_id}": {
                "parameters": [opportunity_parameter, dossier_parameter],
                "get": {
                    "tags": ["Reports"],
                    "summary": "Retrieve a persisted Executive Opportunity Dossier",
                    "responses": {
                        "200": {"description": "Dossier metadata and canonical document"},
                        "404": {"description": "Dossier not found for opportunity"},
                    },
                },
            },
            "/opportunities/{opportunity_id}/dossiers/{dossier_id}/replay": {
                "parameters": [opportunity_parameter, dossier_parameter],
                "post": {
                    "tags": ["Reports"],
                    "summary": "Re-render the immutable snapshot and compare all stored artifacts",
                    "responses": {
                        "200": {"description": "Dossier replay comparison"},
                        "404": {"description": "Dossier not found for opportunity"},
                    },
                },
            },
            "/opportunities/{opportunity_id}/dossiers/{dossier_id}/{format}": {
                "parameters": [
                    opportunity_parameter,
                    dossier_parameter,
                    {
                        "name": "format",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string", "enum": ["html", "pdf", "json"]},
                    },
                ],
                "get": {
                    "tags": ["Reports"],
                    "summary": "Download an exact persisted or canonical dossier export",
                    "responses": {
                        "200": {
                            "description": "Dossier export",
                            "content": {
                                "text/html": {"schema": {"type": "string"}},
                                "application/pdf": {"schema": {"type": "string", "format": "binary"}},
                                "application/json": {"schema": {"type": "object"}},
                            },
                        },
                        "404": {"description": "Dossier or export format not found"},
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
                },
                "KnowledgeReviewRun": {
                    "type": "object",
                    "required": ["module_id"],
                    "properties": {
                        "module_id": {"type": "string", "example": "AKM-GEO-FL-001"},
                        "review_status": {
                            "type": "string",
                            "enum": ["Draft", "Ready", "Incomplete", "Completed"],
                            "default": "Completed",
                        },
                    },
                },
                "SpatialAssessmentRun": {
                    "type": "object",
                    "properties": {
                        "knowledge_review_id": {
                            "type": "string",
                            "pattern": "^KR-[0-9]{6}$",
                            "description": "Optional explicit completed current review; defaults to the current lifecycle-eligible review.",
                        },
                        "reason": {"type": "string"},
                    },
                },
                "DossierGenerate": {
                    "type": "object",
                    "properties": {
                        "assessment_id": {
                            "type": "string",
                            "pattern": "^AS-[0-9]{6}$",
                            "description": "Optional current assessment; defaults to the lifecycle-eligible assessment.",
                        }
                    },
                },
            }
        },
    }
