
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cof_id_sequences (
    entity_type TEXT NOT NULL,
    year INTEGER NOT NULL CHECK (year BETWEEN 2000 AND 9999),
    last_value INTEGER NOT NULL DEFAULT 0 CHECK (last_value >= 0),
    PRIMARY KEY (entity_type, year)
);

CREATE TABLE IF NOT EXISTS markets (
    market_id TEXT PRIMARY KEY,
    cof_market_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL UNIQUE,
    definition TEXT NOT NULL,
    owner TEXT,
    lifecycle_state TEXT NOT NULL CHECK (
        lifecycle_state IN ('Observed','Investigating','Qualified','Active','Scaling','Monitor','Archive')
    ),
    decision_outcome TEXT CHECK (
        decision_outcome IS NULL OR decision_outcome IN ('Pursue','Validate','Monitor','Hold','Reject')
    ),
    priority TEXT NOT NULL DEFAULT 'Medium' CHECK (priority IN ('High','Medium','Low')),
    geographic_scope TEXT,
    status TEXT NOT NULL DEFAULT 'Active' CHECK (status IN ('Active','Archived')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    archived_at TEXT
);

CREATE TABLE IF NOT EXISTS organizations (
    organization_id TEXT PRIMARY KEY,
    cof_organization_id TEXT NOT NULL UNIQUE,
    legal_name TEXT NOT NULL,
    common_name TEXT,
    normalized_name TEXT NOT NULL,
    primary_domain TEXT,
    external_identifier TEXT,
    industry TEXT,
    sector TEXT,
    role TEXT NOT NULL,
    website TEXT,
    headquarters TEXT,
    relationship_stage TEXT NOT NULL DEFAULT 'Identified' CHECK (
        relationship_stage IN (
            'Identified','Researching','Engaged','Relationship Established',
            'Active Opportunity','Customer','Strategic Partner','Archived'
        )
    ),
    cof_status TEXT NOT NULL DEFAULT 'Observed' CHECK (
        cof_status IN ('Observed','Investigating','Validate','Monitor','Hold','Pursue','Reject','Archive')
    ),
    strategic_value TEXT,
    priority TEXT NOT NULL DEFAULT 'Medium' CHECK (priority IN ('High','Medium','Low')),
    owner TEXT,
    last_reviewed_at TEXT,
    next_review_at TEXT,
    status TEXT NOT NULL DEFAULT 'Active' CHECK (status IN ('Active','Archived')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    archived_at TEXT,
    UNIQUE(normalized_name, primary_domain)
);

CREATE TABLE IF NOT EXISTS market_organization_memberships (
    membership_id TEXT PRIMARY KEY,
    cof_membership_id TEXT NOT NULL UNIQUE,
    market_id TEXT NOT NULL REFERENCES markets(market_id) ON DELETE RESTRICT,
    organization_id TEXT NOT NULL REFERENCES organizations(organization_id) ON DELETE RESTRICT,
    relevance TEXT NOT NULL DEFAULT 'Primary' CHECK (relevance IN ('Primary','Secondary','Adjacent','Ecosystem')),
    market_role TEXT,
    priority TEXT NOT NULL DEFAULT 'Medium' CHECK (priority IN ('High','Medium','Low')),
    lifecycle_state TEXT NOT NULL DEFAULT 'Investigating' CHECK (
        lifecycle_state IN ('Observed','Investigating','Qualified','Active','Scaling','Monitor','Archive')
    ),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(market_id, organization_id)
);

CREATE TABLE IF NOT EXISTS contacts (
    contact_id TEXT PRIMARY KEY,
    cof_contact_id TEXT NOT NULL UNIQUE,
    organization_id TEXT NOT NULL REFERENCES organizations(organization_id) ON DELETE RESTRICT,
    full_name TEXT NOT NULL,
    title TEXT,
    department TEXT,
    email TEXT,
    phone TEXT,
    linkedin_url TEXT,
    decision_role TEXT,
    relationship_owner TEXT,
    relationship_strength INTEGER CHECK (relationship_strength BETWEEN 0 AND 20),
    last_contact_at TEXT,
    next_action TEXT,
    next_action_at TEXT,
    status TEXT NOT NULL DEFAULT 'Active' CHECK (status IN ('Active','Inactive','Archived')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS relationships (
    relationship_id TEXT PRIMARY KEY,
    cof_relationship_id TEXT NOT NULL UNIQUE,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    relationship_stage TEXT,
    strength_score INTEGER CHECK (strength_score BETWEEN 0 AND 20),
    owner TEXT,
    established_at TEXT,
    last_interaction_at TEXT,
    next_review_at TEXT,
    status TEXT NOT NULL DEFAULT 'Active' CHECK (status IN ('Active','Inactive','Archived')),
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (NOT (source_type = target_type AND source_id = target_id))
);

CREATE TABLE IF NOT EXISTS opportunities (
    opportunity_id TEXT PRIMARY KEY,
    cof_opportunity_id TEXT NOT NULL UNIQUE,
    organization_id TEXT NOT NULL REFERENCES organizations(organization_id) ON DELETE RESTRICT,
    market_id TEXT REFERENCES markets(market_id) ON DELETE RESTRICT,
    name TEXT NOT NULL,
    opportunity_type TEXT NOT NULL,
    problem_hypothesis TEXT,
    description TEXT,
    estimated_value REAL CHECK (estimated_value IS NULL OR estimated_value >= 0),
    currency TEXT NOT NULL DEFAULT 'USD',
    lifecycle_state TEXT NOT NULL DEFAULT 'Research' CHECK (
        lifecycle_state IN ('Research','Validate','Develop','Proposal','Pilot','Won','Lost','Closed')
    ),
    decision_outcome TEXT CHECK (
        decision_outcome IS NULL OR decision_outcome IN ('Pursue','Validate','Monitor','Hold','Reject')
    ),
    owner TEXT,
    review_date TEXT,
    next_action TEXT,
    next_action_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    closed_at TEXT
);

CREATE TABLE IF NOT EXISTS topics (
    topic_id TEXT PRIMARY KEY,
    cof_topic_id TEXT NOT NULL UNIQUE,
    market_id TEXT REFERENCES markets(market_id) ON DELETE RESTRICT,
    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    description TEXT,
    priority TEXT NOT NULL DEFAULT 'Medium' CHECK (priority IN ('High','Medium','Low')),
    trend_direction TEXT CHECK (
        trend_direction IS NULL OR trend_direction IN ('Rising','Stable','Declining','Unknown')
    ),
    status TEXT NOT NULL DEFAULT 'Active' CHECK (status IN ('Active','Archived')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(market_id, normalized_name)
);

CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    title TEXT NOT NULL,
    publisher TEXT,
    url TEXT,
    publication_date TEXT,
    accessed_at TEXT NOT NULL,
    author TEXT,
    checksum_sha256 TEXT,
    confidentiality TEXT NOT NULL DEFAULT 'Public' CHECK (
        confidentiality IN ('Public','Internal','Confidential','Restricted')
    ),
    status TEXT NOT NULL DEFAULT 'Active' CHECK (status IN ('Active','Archived')),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS intelligence_signals (
    signal_id TEXT PRIMARY KEY,
    cof_signal_id TEXT NOT NULL UNIQUE,
    signal_type TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT,
    observed_at TEXT NOT NULL,
    market_id TEXT REFERENCES markets(market_id) ON DELETE RESTRICT,
    organization_id TEXT REFERENCES organizations(organization_id) ON DELETE RESTRICT,
    topic_id TEXT REFERENCES topics(topic_id) ON DELETE RESTRICT,
    source_id TEXT REFERENCES sources(source_id) ON DELETE RESTRICT,
    materiality TEXT NOT NULL DEFAULT 'Medium' CHECK (materiality IN ('High','Medium','Low')),
    direction TEXT CHECK (direction IS NULL OR direction IN ('Positive','Neutral','Negative','Unknown')),
    ai_generated INTEGER NOT NULL DEFAULT 0 CHECK (ai_generated IN (0,1)),
    human_review_status TEXT NOT NULL DEFAULT 'Pending' CHECK (
        human_review_status IN ('Pending','Accepted','Rejected','Not Required')
    ),
    reviewed_by TEXT,
    reviewed_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence (
    evidence_id TEXT PRIMARY KEY,
    cof_evidence_id TEXT NOT NULL UNIQUE,
    source_id TEXT NOT NULL REFERENCES sources(source_id) ON DELETE RESTRICT,
    assertion TEXT NOT NULL,
    evidence_type TEXT NOT NULL,
    classification TEXT NOT NULL CHECK (
        classification IN ('Verified','Supported','Assumption','Unknown','Disputed')
    ),
    confidence REAL CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
    source_date TEXT,
    captured_at TEXT NOT NULL,
    reviewer TEXT,
    review_date TEXT,
    expires_at TEXT,
    status TEXT NOT NULL DEFAULT 'Active' CHECK (
        status IN ('Active','Expired','Superseded','Archived')
    ),
    content_hash TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence_links (
    evidence_link_id TEXT PRIMARY KEY,
    evidence_id TEXT NOT NULL REFERENCES evidence(evidence_id) ON DELETE RESTRICT,
    subject_type TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    assertion_supported TEXT,
    relevance TEXT CHECK (relevance IS NULL OR relevance IN ('High','Medium','Low')),
    link_type TEXT NOT NULL DEFAULT 'Supports' CHECK (
        link_type IN ('Supports','Weakens','Contextualizes','Supersedes')
    ),
    created_by TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(evidence_id, subject_type, subject_id, assertion_supported)
);

CREATE TABLE IF NOT EXISTS assessments (
    assessment_id TEXT PRIMARY KEY,
    cof_assessment_id TEXT NOT NULL UNIQUE,
    governing_reference TEXT,
    assessment_type TEXT NOT NULL,
    subject_type TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    method_id TEXT NOT NULL,
    decision TEXT NOT NULL,
    summary TEXT NOT NULL,
    reviewer TEXT NOT NULL,
    assessment_date TEXT NOT NULL,
    next_review_at TEXT,
    status TEXT NOT NULL CHECK (
        status IN ('Draft','Under Review','Approved','Superseded','Archived')
    ),
    supersedes_assessment_id TEXT REFERENCES assessments(assessment_id) ON DELETE RESTRICT,
    approval_actor TEXT,
    approved_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assessment_evidence (
    assessment_id TEXT NOT NULL REFERENCES assessments(assessment_id) ON DELETE RESTRICT,
    evidence_id TEXT NOT NULL REFERENCES evidence(evidence_id) ON DELETE RESTRICT,
    purpose TEXT,
    created_at TEXT NOT NULL,
    PRIMARY KEY (assessment_id, evidence_id)
);

CREATE TABLE IF NOT EXISTS scorecards (
    scorecard_id TEXT PRIMARY KEY,
    cof_scorecard_id TEXT NOT NULL UNIQUE,
    subject_type TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    score_model TEXT NOT NULL,
    model_version TEXT NOT NULL,
    criterion_scores_json TEXT NOT NULL,
    criterion_rationales_json TEXT,
    maximum_score REAL NOT NULL CHECK (maximum_score > 0),
    total_score REAL NOT NULL CHECK (total_score >= 0 AND total_score <= maximum_score),
    normalized_score REAL NOT NULL CHECK (normalized_score >= 0 AND normalized_score <= 100),
    gate_result TEXT,
    decision_outcome TEXT,
    recommendation TEXT,
    reviewer TEXT NOT NULL,
    assessment_date TEXT NOT NULL,
    next_review_at TEXT,
    effective_at TEXT NOT NULL,
    expires_at TEXT,
    supersedes_scorecard_id TEXT REFERENCES scorecards(scorecard_id) ON DELETE RESTRICT,
    status TEXT NOT NULL CHECK (
        status IN ('Draft','Under Review','Approved','Superseded','Expired','Archived')
    ),
    created_at TEXT NOT NULL,
    CHECK (supersedes_scorecard_id IS NULL OR supersedes_scorecard_id <> scorecard_id)
);

CREATE TABLE IF NOT EXISTS scorecard_evidence (
    scorecard_id TEXT NOT NULL REFERENCES scorecards(scorecard_id) ON DELETE RESTRICT,
    evidence_id TEXT NOT NULL REFERENCES evidence(evidence_id) ON DELETE RESTRICT,
    criterion_name TEXT,
    created_at TEXT NOT NULL,
    PRIMARY KEY (scorecard_id, evidence_id, criterion_name)
);

CREATE TABLE IF NOT EXISTS assumptions (
    assumption_id TEXT PRIMARY KEY,
    cof_assumption_id TEXT NOT NULL UNIQUE,
    subject_type TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    statement TEXT NOT NULL,
    owner TEXT,
    status TEXT NOT NULL CHECK (
        status IN ('Open','Supported','Refuted','Resolved','Expired','Archived')
    ),
    confidence REAL CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
    review_date TEXT,
    resolution TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS risks (
    risk_id TEXT PRIMARY KEY,
    cof_risk_id TEXT NOT NULL UNIQUE,
    subject_type TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    category TEXT,
    likelihood INTEGER CHECK (likelihood BETWEEN 1 AND 5),
    impact INTEGER CHECK (impact BETWEEN 1 AND 5),
    risk_score INTEGER GENERATED ALWAYS AS (
        CASE
            WHEN likelihood IS NULL OR impact IS NULL THEN NULL
            ELSE likelihood * impact
        END
    ) STORED,
    mitigation TEXT,
    owner TEXT,
    status TEXT NOT NULL CHECK (
        status IN ('Open','Monitoring','Mitigated','Accepted','Closed','Archived')
    ),
    review_date TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS actions (
    action_id TEXT PRIMARY KEY,
    cof_action_id TEXT NOT NULL UNIQUE,
    subject_type TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    description TEXT NOT NULL,
    owner TEXT,
    priority TEXT NOT NULL DEFAULT 'Medium' CHECK (priority IN ('High','Medium','Low')),
    due_at TEXT,
    status TEXT NOT NULL CHECK (
        status IN ('Open','In Progress','Blocked','Completed','Cancelled','Archived')
    ),
    completion_evidence_id TEXT REFERENCES evidence(evidence_id) ON DELETE RESTRICT,
    completed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS lifecycle_events (
    lifecycle_event_id TEXT PRIMARY KEY,
    cof_lifecycle_event_id TEXT NOT NULL UNIQUE,
    subject_type TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    previous_state TEXT,
    new_state TEXT NOT NULL,
    reason TEXT,
    actor TEXT NOT NULL,
    related_evidence_id TEXT REFERENCES evidence(evidence_id) ON DELETE RESTRICT,
    related_assessment_id TEXT REFERENCES assessments(assessment_id) ON DELETE RESTRICT,
    event_hash TEXT,
    occurred_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS registry_audit_log (
    audit_id TEXT PRIMARY KEY,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    subject_type TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    previous_value_json TEXT,
    new_value_json TEXT,
    reason TEXT,
    related_evidence_id TEXT REFERENCES evidence(evidence_id) ON DELETE RESTRICT,
    occurred_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_org_normalized_name ON organizations(normalized_name);
CREATE INDEX IF NOT EXISTS idx_org_status_priority ON organizations(cof_status, priority);
CREATE INDEX IF NOT EXISTS idx_membership_market ON market_organization_memberships(market_id);
CREATE INDEX IF NOT EXISTS idx_membership_org ON market_organization_memberships(organization_id);
CREATE INDEX IF NOT EXISTS idx_contacts_org ON contacts(organization_id);
CREATE INDEX IF NOT EXISTS idx_opportunities_org ON opportunities(organization_id);
CREATE INDEX IF NOT EXISTS idx_opportunities_state ON opportunities(lifecycle_state);
CREATE INDEX IF NOT EXISTS idx_signals_org_date ON intelligence_signals(organization_id, observed_at);
CREATE INDEX IF NOT EXISTS idx_evidence_source ON evidence(source_id);
CREATE INDEX IF NOT EXISTS idx_evidence_classification ON evidence(classification);
CREATE INDEX IF NOT EXISTS idx_evidence_links_subject ON evidence_links(subject_type, subject_id);
CREATE INDEX IF NOT EXISTS idx_assessments_subject ON assessments(subject_type, subject_id, assessment_date);
CREATE INDEX IF NOT EXISTS idx_scorecards_subject ON scorecards(subject_type, subject_id, score_model, assessment_date);
CREATE INDEX IF NOT EXISTS idx_actions_due ON actions(status, due_at);
CREATE INDEX IF NOT EXISTS idx_lifecycle_subject ON lifecycle_events(subject_type, subject_id, occurred_at);

CREATE TRIGGER IF NOT EXISTS trg_scorecards_no_update_approved
BEFORE UPDATE ON scorecards
WHEN OLD.status IN ('Approved','Superseded','Expired','Archived')
BEGIN
    SELECT RAISE(ABORT, 'Approved or historical scorecards are immutable');
END;

CREATE TRIGGER IF NOT EXISTS trg_scorecards_no_delete
BEFORE DELETE ON scorecards
BEGIN
    SELECT RAISE(ABORT, 'Scorecards cannot be deleted');
END;

CREATE TRIGGER IF NOT EXISTS trg_evidence_no_delete
BEFORE DELETE ON evidence
BEGIN
    SELECT RAISE(ABORT, 'Evidence cannot be deleted');
END;

CREATE TRIGGER IF NOT EXISTS trg_assessments_no_delete
BEFORE DELETE ON assessments
BEGIN
    SELECT RAISE(ABORT, 'Assessments cannot be deleted');
END;

CREATE TRIGGER IF NOT EXISTS trg_lifecycle_no_update
BEFORE UPDATE ON lifecycle_events
BEGIN
    SELECT RAISE(ABORT, 'Lifecycle events are append-only');
END;

CREATE TRIGGER IF NOT EXISTS trg_lifecycle_no_delete
BEFORE DELETE ON lifecycle_events
BEGIN
    SELECT RAISE(ABORT, 'Lifecycle events are append-only');
END;
