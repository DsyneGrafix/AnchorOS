"""AIN-104 — Flask web adapter for AnchorInsight."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from flask import Flask, abort, jsonify, render_template, request

from anchorinsight_registry import (
    CommercialIntelligenceRegistryService,
    NotFoundError,
    OrganizationIntelligenceProfileService,
    ScoringDecisionService,
)


def create_app(
    database_path: str | Path | None = None,
    *,
    testing: bool = False,
) -> Flask:
    base_dir = Path(__file__).resolve().parent
    app = Flask(
        __name__,
        template_folder=str(base_dir / "templates"),
        static_folder=str(base_dir / "static"),
    )
    app.config["TESTING"] = testing
    app.config["JSON_SORT_KEYS"] = False

    if database_path is None:
        database_path = Path("data") / "anchorinsight.db"

    registry = CommercialIntelligenceRegistryService(database_path)
    scoring = ScoringDecisionService(registry)
    profiles = OrganizationIntelligenceProfileService(registry, scoring)

    app.extensions["anchorinsight.registry"] = registry
    app.extensions["anchorinsight.scoring"] = scoring
    app.extensions["anchorinsight.profiles"] = profiles

    @app.get("/")
    def dashboard():
        organizations = registry.list_organizations(limit=200)
        cards = [profiles.build_compact_card(item["cof_organization_id"]) for item in organizations]
        summary = {
            "organization_count": len(cards),
            "pursue_count": sum(1 for card in cards if card["decision"] == "Pursue"),
            "validate_count": sum(1 for card in cards if card["decision"] == "Validate"),
            "open_action_count": sum(card["open_actions"] for card in cards),
        }
        return render_template("dashboard.html", cards=cards, summary=summary)

    @app.get("/organizations")
    def organizations():
        search = request.args.get("q") or None
        market = request.args.get("market") or None
        status = request.args.get("status") or None
        records = registry.list_organizations(
            market_identifier=market,
            cof_status=status,
            search=search,
            limit=500,
        )
        cards = [profiles.build_compact_card(item["cof_organization_id"]) for item in records]
        return render_template(
            "organizations.html",
            cards=cards,
            query=search or "",
            selected_status=status or "",
        )

    @app.get("/organizations/<identifier>")
    def organization_profile(identifier: str):
        try:
            profile = profiles.build_profile(identifier)
        except NotFoundError:
            abort(404)
        return render_template("organization_profile.html", profile=profile)

    @app.get("/api/health")
    def api_health():
        return jsonify({
            "web": {"name": "AnchorInsight Web Adapter", "version": "1.0.0", "status": "HEALTHY"},
            "profile": profiles.health(),
        })

    @app.get("/api/organizations")
    def api_organizations():
        records = registry.list_organizations(
            market_identifier=request.args.get("market") or None,
            cof_status=request.args.get("status") or None,
            search=request.args.get("q") or None,
            limit=min(int(request.args.get("limit", "200")), 1000),
        )
        return jsonify({
            "count": len(records),
            "items": [profiles.build_compact_card(item["cof_organization_id"]) for item in records],
        })

    @app.get("/api/organizations/<identifier>")
    def api_organization_profile(identifier: str):
        try:
            return jsonify(profiles.export_payload(identifier))
        except NotFoundError:
            return jsonify({"error": "organization_not_found", "identifier": identifier}), 404

    @app.errorhandler(404)
    def not_found(_: Any):
        return render_template("404.html"), 404

    return app
