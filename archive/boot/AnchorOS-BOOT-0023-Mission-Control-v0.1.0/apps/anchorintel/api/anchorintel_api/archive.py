"""Deterministic BOOT-0020 archive package construction and replay verification."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from typing import Any, Mapping


ARCHIVE_FORMAT_VERSION = "1.0.0"
REQUIRED_ARCHIVE_FILES = (
    "manifest.json",
    "opportunity.json",
    "evidence.json",
    "knowledge-review.json",
    "assessment.json",
    "dossier.json",
    "dossier.html",
    "dossier.pdf",
    "audit-summary.json",
    "replay-summary.json",
)


def canonical_json(value: Any) -> bytes:
    """Render stable, human-readable JSON for an archive member."""

    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
        .encode("utf-8")
        + b"\n"
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    info.create_system = 3
    return info


def build_archive_package(
    *,
    archive_id: str,
    opportunity_id: str,
    archive_timestamp: str,
    provenance: Mapping[str, Any],
    record_count: int,
    members: Mapping[str, bytes],
) -> tuple[bytes, dict[str, Any]]:
    """Create byte-identical ZIP output for identical arguments."""

    expected_members = set(REQUIRED_ARCHIVE_FILES) - {"manifest.json"}
    if set(members) != expected_members:
        missing = sorted(expected_members - set(members))
        extra = sorted(set(members) - expected_members)
        raise ValueError(f"Invalid archive members; missing={missing}, extra={extra}")
    file_entries = [
        {
            "name": name,
            "sha256": sha256_bytes(members[name]),
            "size": len(members[name]),
        }
        for name in sorted(members)
    ]
    manifest = {
        "archive_format_version": ARCHIVE_FORMAT_VERSION,
        "archive_id": archive_id,
        "opportunity_id": opportunity_id,
        "archive_timestamp": archive_timestamp,
        "record_count": record_count,
        "file_count": len(REQUIRED_ARCHIVE_FILES),
        "provenance": dict(provenance),
        "files": file_entries,
        "boundary_notice": (
            "This package contains persisted AnchorIntel records and exports. "
            "Archive creation did not browse the internet, invoke external AI, "
            "or rerun upstream analysis."
        ),
    }
    all_members = {"manifest.json": canonical_json(manifest), **dict(members)}
    stream = io.BytesIO()
    with zipfile.ZipFile(
        stream, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for name in REQUIRED_ARCHIVE_FILES:
            archive.writestr(_zip_info(name), all_members[name])
    return stream.getvalue(), manifest


def verify_archive_package(
    payload: bytes,
    *,
    expected_package_hash: str,
    expected_manifest: Mapping[str, Any],
    expected_provenance: Mapping[str, Any],
) -> dict[str, Any]:
    """Verify package bytes, member hashes, identities, and provenance chain."""

    reasons: list[str] = []
    computed_package_hash = sha256_bytes(payload)
    checks: dict[str, bool] = {
        "package_hash": computed_package_hash == expected_package_hash,
        "manifest_integrity": False,
        "member_set": False,
        "member_hashes": False,
        "record_ids": False,
        "provenance_chain": False,
        "dossier_replay_hash": False,
        "assessment_replay_hash": False,
        "knowledge_module_hash": False,
        "revisions": False,
    }
    if not checks["package_hash"]:
        reasons.append("The archive package SHA-256 does not match the stored hash.")
        return {
            "result": "FAIL",
            "match": False,
            "checks": checks,
            "reasons": reasons,
            "stored_package_hash": expected_package_hash,
            "computed_package_hash": computed_package_hash,
        }
    try:
        with zipfile.ZipFile(io.BytesIO(payload), "r") as archive:
            names = archive.namelist()
            safe_names = all(
                name and not name.startswith(("/", "\\")) and ".." not in name.split("/")
                for name in names
            )
            checks["member_set"] = (
                safe_names
                and len(names) == len(set(names))
                and set(names) == set(REQUIRED_ARCHIVE_FILES)
            )
            if not checks["member_set"]:
                reasons.append("The archive member set is missing, duplicated, extra, or unsafe.")
            manifest = json.loads(archive.read("manifest.json"))
            checks["manifest_integrity"] = manifest == dict(expected_manifest)
            if not checks["manifest_integrity"]:
                reasons.append("manifest.json does not match the persisted manifest.")
            member_hashes_ok = True
            for entry in manifest.get("files", []):
                name = str(entry.get("name", ""))
                try:
                    member = archive.read(name)
                except KeyError:
                    member_hashes_ok = False
                    continue
                if sha256_bytes(member) != entry.get("sha256") or len(member) != entry.get("size"):
                    member_hashes_ok = False
            checks["member_hashes"] = member_hashes_ok and len(
                manifest.get("files", [])
            ) == len(REQUIRED_ARCHIVE_FILES) - 1
            if not checks["member_hashes"]:
                reasons.append("One or more included files failed SHA-256 or size verification.")

            opportunity = json.loads(archive.read("opportunity.json"))
            evidence = json.loads(archive.read("evidence.json"))
            review = json.loads(archive.read("knowledge-review.json"))
            assessment = json.loads(archive.read("assessment.json"))
            dossier = json.loads(archive.read("dossier.json"))
            replay = json.loads(archive.read("replay-summary.json"))
            provenance = manifest.get("provenance", {})
            checks["record_ids"] = (
                opportunity.get("opportunity_id") == provenance.get("opportunity", {}).get("id")
                and [item.get("evidence_id") for item in evidence]
                == [item.get("id") for item in provenance.get("evidence", [])]
                and review.get("review_id") == provenance.get("knowledge_review", {}).get("id")
                and assessment.get("assessment_id") == provenance.get("assessment", {}).get("id")
                and dossier.get("dossier_id") == provenance.get("dossier", {}).get("id")
            )
            if not checks["record_ids"]:
                reasons.append("Included record identifiers do not match the manifest.")
            checks["provenance_chain"] = provenance == dict(expected_provenance)
            if not checks["provenance_chain"]:
                reasons.append("The manifest provenance chain does not match the archive record.")
            checks["dossier_replay_hash"] = (
                dossier.get("replay_hash") == provenance.get("dossier", {}).get("replay_hash")
                == replay.get("dossier", {}).get("stored_replay_hash")
            )
            checks["assessment_replay_hash"] = (
                assessment.get("replay_hash")
                == provenance.get("assessment", {}).get("replay_hash")
                == replay.get("assessment", {}).get("replay_hash")
            )
            checks["knowledge_module_hash"] = (
                review.get("module_integrity_hash")
                == provenance.get("knowledge_review", {}).get("module_integrity_hash")
                == replay.get("knowledge_review", {}).get("module_integrity_hash")
            )
            checks["revisions"] = (
                opportunity.get("revision") == provenance.get("opportunity", {}).get("revision")
                and [item.get("revision") for item in evidence]
                == [item.get("revision") for item in provenance.get("evidence", [])]
                and review.get("revision") == provenance.get("knowledge_review", {}).get("revision")
                and assessment.get("revision") == provenance.get("assessment", {}).get("revision")
                and dossier.get("revision") == provenance.get("dossier", {}).get("revision")
            )
            for key, label in (
                ("dossier_replay_hash", "Dossier replay hash"),
                ("assessment_replay_hash", "Assessment replay hash"),
                ("knowledge_module_hash", "Knowledge Module hash"),
                ("revisions", "Record revisions"),
            ):
                if not checks[key]:
                    reasons.append(f"{label} verification failed.")
    except Exception as exc:
        reasons.append(f"The archive package could not be parsed safely: {type(exc).__name__}.")
    match = all(checks.values())
    return {
        "result": "PASS" if match else "FAIL",
        "match": match,
        "checks": checks,
        "reasons": list(dict.fromkeys(reasons)),
        "stored_package_hash": expected_package_hash,
        "computed_package_hash": computed_package_hash,
    }
