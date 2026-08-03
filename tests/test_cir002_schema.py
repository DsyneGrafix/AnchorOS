
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from anchorinsight_registry.db import RegistryDatabase, utc_now


class CIR002SchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "registry.db"
        self.db = RegistryDatabase(self.database_path)
        self.db.initialize()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_schema_health(self) -> None:
        health = self.db.health()
        self.assertEqual(health["status"], "HEALTHY")
        self.assertEqual(health["schema_version"], 1)
        self.assertEqual(health["foreign_key_issues"], 0)
        self.assertEqual(health["integrity"], "ok")

    def test_cof_ids_are_sequential(self) -> None:
        first = self.db.next_cof_id("organization", 2026)
        second = self.db.next_cof_id("organization", 2026)
        self.assertEqual(first, "COF-ORG-2026-001")
        self.assertEqual(second, "COF-ORG-2026-002")

    def test_cps_energy_profile(self) -> None:
        market = self.db.create_market(
            name="Electric Cooperatives",
            definition="Member-owned electric distribution cooperatives.",
            cof_market_id="COF-MKT-2026-001",
        )
        organization = self.db.create_organization(
            legal_name="City Public Service Board of San Antonio",
            common_name="CPS Energy",
            role="Infrastructure Owner",
            sector="Municipal Utility",
            cof_organization_id="COF-ORG-2026-001",
        )
        self.db.add_market_membership(
            market["market_id"], organization["organization_id"]
        )
        self.db.create_scorecard(
            subject_type="Organization",
            subject_id=organization["organization_id"],
            score_model="Organization Score",
            model_version="1.0",
            criterion_scores={"Fit": 5, "Value": 4},
            maximum_score=10,
            decision_outcome="Validate",
            reviewer="Ricky",
        )
        profile = self.db.organization_profile(organization["organization_id"])
        self.assertEqual(
            profile["organization"]["cof_organization_id"],
            "COF-ORG-2026-001",
        )
        self.assertEqual(len(profile["markets"]), 1)
        self.assertEqual(len(profile["scorecards"]), 1)

    def test_organization_can_belong_to_multiple_markets(self) -> None:
        m1 = self.db.create_market(
            name="Utilities", definition="Utility market."
        )
        m2 = self.db.create_market(
            name="Infrastructure Enterprises",
            definition="Infrastructure enterprise market.",
        )
        organization = self.db.create_organization(
            legal_name="Example Utility",
            role="Infrastructure Owner",
        )
        self.db.add_market_membership(
            m1["market_id"], organization["organization_id"]
        )
        self.db.add_market_membership(
            m2["market_id"],
            organization["organization_id"],
            relevance="Secondary",
        )
        profile = self.db.organization_profile(organization["organization_id"])
        self.assertEqual(len(profile["markets"]), 2)

    def test_duplicate_cof_id_is_rejected(self) -> None:
        self.db.create_organization(
            legal_name="Organization One",
            role="Infrastructure Owner",
            cof_organization_id="COF-ORG-2026-001",
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.create_organization(
                legal_name="Organization Two",
                role="Infrastructure Owner",
                cof_organization_id="COF-ORG-2026-001",
            )

    def test_foreign_key_integrity_is_enforced(self) -> None:
        now = utc_now()
        with self.assertRaises(sqlite3.IntegrityError):
            with self.db.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO market_organization_memberships(
                        membership_id, cof_membership_id, market_id,
                        organization_id, relevance, priority,
                        lifecycle_state, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, 'Primary', 'High',
                              'Investigating', ?, ?)
                    """,
                    (
                        self.db.internal_id(),
                        "COF-MEM-2026-001",
                        "missing-market",
                        "missing-organization",
                        now,
                        now,
                    ),
                )

    def test_approved_scorecard_is_immutable(self) -> None:
        organization = self.db.create_organization(
            legal_name="Immutable Score Organization",
            role="Infrastructure Owner",
        )
        scorecard = self.db.create_scorecard(
            subject_type="Organization",
            subject_id=organization["organization_id"],
            score_model="OVS",
            model_version="1.0",
            criterion_scores={"Financial Stability": 5},
            maximum_score=5,
            decision_outcome="Pursue",
            reviewer="Ricky",
            status="Approved",
        )
        with self.assertRaises(sqlite3.DatabaseError):
            with self.db.transaction() as connection:
                connection.execute(
                    "UPDATE scorecards SET total_score = 1 WHERE scorecard_id = ?",
                    (scorecard["scorecard_id"],),
                )

    def test_historical_scorecard_cannot_be_deleted(self) -> None:
        organization = self.db.create_organization(
            legal_name="History Organization",
            role="Infrastructure Owner",
        )
        scorecard = self.db.create_scorecard(
            subject_type="Organization",
            subject_id=organization["organization_id"],
            score_model="OVS",
            model_version="1.0",
            criterion_scores={"Financial Stability": 5},
            maximum_score=5,
            decision_outcome="Pursue",
            reviewer="Ricky",
        )
        with self.assertRaises(sqlite3.DatabaseError):
            with self.db.transaction() as connection:
                connection.execute(
                    "DELETE FROM scorecards WHERE scorecard_id = ?",
                    (scorecard["scorecard_id"],),
                )

    def test_evidence_requires_source(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            with self.db.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO evidence(
                        evidence_id, cof_evidence_id, source_id, assertion,
                        evidence_type, classification, captured_at,
                        status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'Active', ?)
                    """,
                    (
                        self.db.internal_id(),
                        "COF-EVD-2026-001",
                        "missing-source",
                        "Test assertion",
                        "Document",
                        "Supported",
                        utc_now(),
                        utc_now(),
                    ),
                )

    def test_lifecycle_events_are_append_only(self) -> None:
        organization = self.db.create_organization(
            legal_name="Lifecycle Organization",
            role="Infrastructure Owner",
        )
        event_id = self.db.internal_id()
        now = utc_now()
        with self.db.transaction() as connection:
            connection.execute(
                """
                INSERT INTO lifecycle_events(
                    lifecycle_event_id, cof_lifecycle_event_id,
                    subject_type, subject_id, event_type, previous_state,
                    new_state, actor, occurred_at, created_at
                ) VALUES (?, ?, 'Organization', ?, 'status.changed',
                          'Observed', 'Validate', 'Ricky', ?, ?)
                """,
                (
                    event_id,
                    self.db.next_cof_id("lifecycle_event"),
                    organization["organization_id"],
                    now,
                    now,
                ),
            )
        with self.assertRaises(sqlite3.DatabaseError):
            with self.db.transaction() as connection:
                connection.execute(
                    "UPDATE lifecycle_events SET new_state='Pursue' WHERE lifecycle_event_id=?",
                    (event_id,),
                )


if __name__ == "__main__":
    unittest.main()
