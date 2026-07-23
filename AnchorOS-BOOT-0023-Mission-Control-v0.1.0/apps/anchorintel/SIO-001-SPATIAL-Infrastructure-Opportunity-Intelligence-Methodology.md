# SIO-001 — S.P.A.T.I.A.L. Infrastructure Opportunity Intelligence Methodology

**Document family:** Sirius Logic Systems Opportunity Intelligence  
**Identifier:** SIO-001  
**Version:** 0.1  
**Status:** Working Draft  
**Primary application:** AnchorFiber  
**Owner:** Sirius Logic Systems  
**Date:** 18 July 2026

## 1. Purpose

S.P.A.T.I.A.L. is a repeatable, evidence-first methodology for discovering, evaluating, comparing, and advancing infrastructure opportunities. It converts scattered market, geographic, asset, funding, regulatory, and technical signals into a bounded decision: **Pursue, Validate, Monitor, Hold, or Reject**.

The methodology's one job is to determine whether an observed infrastructure need is sufficiently real, reachable, valuable, and aligned to justify the next investment of time or money.

S.P.A.T.I.A.L. does not certify engineering feasibility, promise funding, predict contract awards, or replace legal, financial, environmental, or professional engineering review.

## 2. The S.P.A.T.I.A.L. sequence

| Stage | Name | Controlling question | Required output |
|---|---|---|---|
| **S** | **Scope & Signals** | What opportunity is being examined, where, for whom, and which signals justify attention? | Opportunity frame and signal register |
| **P** | **Pressure & Problem** | What infrastructure pressure exists, how consequential is it, and who experiences it? | Problem statement and pressure profile |
| **A** | **Assets, Actors & Authority** | Which assets, owners, users, decision-makers, jurisdictions, and authorities control the opportunity? | Asset–actor–authority map |
| **T** | **Technical & Temporal Fit** | Can a credible solution be delivered within the physical, operational, dependency, and timing constraints? | Technical fit assessment and dependency map |
| **I** | **Investment & Implementation Path** | Is there a credible path from need to funding, procurement, deployment, operation, and support? | Investment and implementation pathway |
| **A** | **Alignment & Advantage** | Does the opportunity fit AnchorFiber and Sirius Logic Systems, and is there a defensible reason to participate? | Alignment, differentiation, and boundary assessment |
| **L** | **Lifecycle Decision & Learning** | What decision is justified now, what must happen next, and what evidence would change the decision? | Decision record, action plan, and learning loop |

The stages are sequential for control purposes, but evidence may be collected in parallel. No later-stage enthusiasm may repair an unsupported earlier-stage claim.

## 3. Governing principles

1. **Evidence before enthusiasm.** Attractive wording is not evidence of an addressable opportunity.
2. **Need is not demand.** A real infrastructure problem becomes an opportunity only when a reachable actor has authority, intent, and a plausible resource path.
3. **Geography matters.** Infrastructure opportunities are constrained by place, jurisdiction, terrain, existing assets, rights-of-way, permitting, and local operating conditions.
4. **Timing is part of feasibility.** A technically sound solution may be unsuitable if funding, procurement, permitting, construction, or operational windows do not align.
5. **Authority must be mapped.** The beneficiary, buyer, asset owner, operator, regulator, funder, and approver may be different entities.
6. **Unknowns remain visible.** Missing information is recorded as uncertainty; it is not silently converted into an assumption.
7. **Claims remain bounded.** The methodology supports an opportunity decision, not a guarantee of engineering, commercial, regulatory, or funding success.
8. **The next step must be proportional.** Early evidence justifies inexpensive validation; stronger evidence may justify partner outreach, field assessment, proposal development, or investment.

## 4. Evidence classification

Every material entry SHALL be labeled with one of the following evidence states:

| State | Meaning | Examples |
|---|---|---|
| **V — Verified fact** | Directly supported by an authoritative, current, inspectable source | Official plan, issued solicitation, asset record, regulator filing, adopted budget |
| **S — Supported inference** | Reasonably derived from two or more credible facts, with reasoning stated | Likely middle-mile gap inferred from service maps and route topology |
| **A — Assumption** | Provisionally accepted for analysis but not yet supported | Assumed pole access or customer take rate |
| **U — Unknown** | Material information is missing or contradictory | Unconfirmed route ownership or funding eligibility |
| **D — Disputed** | Credible sources conflict | Conflicting coverage, cost, ownership, or schedule information |

Each record SHOULD include source, publication or observation date, retrieval date, geographic scope, claim supported, confidence, and staleness risk.

### 4.1 Source hierarchy

When sources conflict, use the following default priority:

1. Controlling law, regulation, permit, order, or formally adopted public record.
2. Asset-owner, procuring-authority, or funding-agency record.
3. Audited or independently verified operational data.
4. Current engineering study, mapping dataset, or utility filing.
5. Credible industry reporting or vendor documentation.
6. Stakeholder interview or field observation with date and attribution.
7. Marketing content, social posts, unattributed claims, or model-generated summaries.

Lower-ranked sources may generate a lead but SHALL NOT independently support a high-confidence decision.

## 5. Stage requirements

### 5.1 S — Scope & Signals

Define the opportunity before analyzing it.

Required fields:

- opportunity identifier and working title;
- location and geographic boundary;
- infrastructure class and use case;
- affected population, facilities, routes, or operations;
- initiating signals and their dates;
- proposed customer or beneficiary class;
- time horizon;
- exclusions and adjacent issues;
- analyst and review date.

Signal categories may include service gaps, capacity constraints, outages, new construction, public plans, grant programs, capital budgets, regulatory deadlines, anchor-institution demand, route redundancy needs, asset deterioration, resilience needs, or technology transitions.

**Gate S:** The opportunity SHALL NOT advance unless at least one credible signal identifies a bounded place, infrastructure condition, and affected actor. Generic market growth is insufficient.

### 5.2 P — Pressure & Problem

Translate signals into an operationally specific problem.

Assess:

- current condition and desired condition;
- frequency, duration, scale, and trend of the pressure;
- operational, economic, safety, resilience, equity, or compliance consequence;
- who experiences the consequence;
- current workaround and its cost or limitation;
- trigger or deadline that creates urgency;
- evidence that the affected actor recognizes the problem;
- cost of delay and cost of inaction.

Use this bounded problem statement:

> **[Actor or asset]** experiences **[measurable infrastructure condition]** in **[location]**, causing **[observable consequence]** under **[current or expected conditions]**. A viable response must achieve **[bounded outcome]** by **[time or trigger]** without violating **[key constraints]**.

**Gate P:** A problem is not commercially actionable unless both the condition and a consequential effect are supported. An inferred need with no identifiable consequence remains a research lead.

### 5.3 A — Assets, Actors & Authority

Map the physical and institutional system surrounding the opportunity.

The assessment SHALL identify, when applicable:

- relevant existing assets and their owners;
- condition, capacity, coverage, age, and known constraints;
- customers, beneficiaries, and affected communities;
- buyer, budget owner, procurement authority, and final approver;
- operator and long-term maintainer;
- regulators, permitting bodies, utilities, rights-of-way owners, and tribal or local authorities;
- likely delivery, engineering, construction, technology, and finance partners;
- stakeholders able to delay, reshape, or stop the opportunity;
- data owners and access constraints.

The methodology SHALL distinguish these roles rather than treating “the customer” as one entity.

**Gate A:** The opportunity SHALL NOT receive a Pursue recommendation when no reachable actor has a plausible route to authorize, procure, fund, or sponsor the next step.

### 5.4 T — Technical & Temporal Fit

Determine whether a credible solution pathway exists without presenting a preliminary screen as an engineering design.

Assess:

- target capability and minimum acceptable outcome;
- existing architecture and integration boundary;
- route, capacity, power, backhaul, environmental, civil, cyber, safety, and interoperability constraints;
- dependencies and single points of failure;
- data and field-validation requirements;
- standards, licensing, permitting, and compliance considerations;
- deployment phases and critical path;
- technology maturity and supplier availability;
- operating model, maintenance burden, and lifecycle support;
- earliest credible service date and schedule uncertainty;
- failure modes, resilience requirements, and exit or recovery options.

For AnchorFiber, the screen SHOULD consider premises, sites, routes, networks, conduits, fiber cables, handholes, splice points, capacity, occupancy, redundancy, and service dependencies where relevant.

**Gate T:** A candidate may advance with technical unknowns only when the unknowns are explicit, resolvable through a bounded next step, and not known fatal constraints.

### 5.5 I — Investment & Implementation Path

Test whether the opportunity can move from need to funded execution.

Assess:

- capital and operating cost range, basis, and uncertainty;
- value created or loss avoided;
- paying customer and payment mechanism;
- public, private, blended, grant, loan, tax-credit, or owner-funded pathways;
- eligibility, match, reimbursement, and compliance conditions;
- procurement vehicle and likely acquisition cycle;
- commercial model, including build, lease, manage, subscribe, license, or partner;
- delivery capacity and partner requirements;
- implementation phases, decision points, and cash timing;
- ownership, revenue, maintenance, and risk allocation;
- off-ramps if funding or authorization fails.

**Gate I:** Funding availability alone SHALL NOT be treated as demand. The record must connect a defined problem, eligible actor, allowed use, credible applicant or buyer, and implementable scope.

### 5.6 A — Alignment & Advantage

Determine whether Sirius Logic Systems and AnchorFiber should participate.

Evaluate:

- fit with AnchorFiber's infrastructure intelligence and asset-domain capabilities;
- fit with AnchorOS as the operating platform;
- potential value from AnchorStack continuation-validity concepts without implying that AnchorStack validates engineering inputs or certifies infrastructure;
- reuse of existing modules, models, evidence structures, or workflows;
- differentiated value compared with common GIS, asset-management, network-planning, engineering, and construction tools;
- access to required domain expertise and partners;
- intellectual-property, data-rights, security, and contractual boundaries;
- reference-customer, repeatability, and product-learning value;
- reputational, execution, concentration, and mission-drift risk;
- explicit reasons not to pursue.

The preferred AnchorFiber role is a bounded intelligence, coordination, evidence, or operational-workflow role that complements licensed engineering, construction, legal, financial, and regulatory professionals.

**Gate A:** Strategic excitement SHALL NOT override a weak customer path, fatal technical constraint, unacceptable risk, or responsibility outside the company's competence and authority.

### 5.7 L — Lifecycle Decision & Learning

Issue a controlled decision and define when it expires.

Permitted decisions:

| Decision | Meaning | Required next action |
|---|---|---|
| **Pursue** | Evidence supports a defined, reachable opportunity | Approve a bounded capture, partner, pilot, or proposal plan |
| **Validate** | Promising but one or more material uncertainties block pursuit | Execute named evidence-gathering actions |
| **Monitor** | Real signal, but timing, authority, or resources are not yet actionable | Assign triggers and a review date |
| **Hold** | Opportunity may be viable but is misaligned with current capacity or priorities | Record the reason and re-entry conditions |
| **Reject** | Evidence shows a fatal constraint, poor fit, unacceptable risk, or no credible path | Close the case while preserving the decision record |

Every decision SHALL include:

- decision and date;
- supporting facts and inferences;
- decisive unknowns or limitations;
- score and gate results;
- named owner;
- authorized next action and resource ceiling;
- review or expiration date;
- triggers that require reassessment;
- conditions for escalation, hold, or closure;
- lessons reusable across other opportunities.

**Gate L:** No opportunity remains “active” without an owner, next action, review date, and explicit resource boundary.

## 6. Scoring model

Each dimension is scored from 0 to 5 using only the current evidence record.

| Dimension | Weight | 0 | 3 | 5 |
|---|---:|---|---|---|
| Problem evidence and consequence | 15 | Speculative | Supported need and consequence | Verified, measured, urgent problem |
| Customer, actor, and authority clarity | 15 | Unknown | Key actors identified | Reachable sponsor/buyer and authority path verified |
| Technical and temporal fit | 15 | Fatal or unknown | Plausible with resolvable gaps | Credible, bounded path with acceptable dependencies |
| Funding and procurement path | 15 | None identified | Plausible mechanism | Eligible, timed, and sponsor-linked pathway |
| Strategic alignment | 15 | Outside mission | Partial fit | Strong AnchorFiber fit and reusable capability |
| Differentiated advantage | 10 | Commodity/no role | Some advantage | Clear, defensible, buyer-relevant advantage |
| Delivery readiness | 10 | No capacity/path | Partners or phased path plausible | Capable team, partners, and delivery model identified |
| Risk and uncertainty position | 5 | Unacceptable/unbounded | Material but manageable | Bounded risks with credible controls and off-ramps |

For each dimension:

`weighted points = (dimension score ÷ 5) × dimension weight`

The total Opportunity Confidence Score is the sum of weighted points on a 0–100 scale.

### 6.1 Decision bands

| Score | Default interpretation |
|---:|---|
| **80–100** | Pursue, subject to all mandatory gates |
| **65–79** | Validate or conditional Pursue with tightly bounded next action |
| **45–64** | Monitor or Validate |
| **25–44** | Hold; do not allocate proposal or build resources |
| **0–24** | Reject or archive as an unsupported lead |

Scores guide comparison; they do not override gates. Any fatal legal, ethical, authority, safety, solvency, technical, or mission-boundary issue requires Hold or Reject regardless of score.

### 6.2 Confidence modifier

Record the proportion of material claims classified V, S, A, U, and D. A high numeric score dominated by assumptions or unknowns SHALL be labeled **provisional**.

Recommended confidence labels:

- **High:** decisive claims are verified and current; no material dispute remains.
- **Moderate:** the decision rests on supported inferences with resolvable gaps.
- **Low:** one or more decisive claims remain assumptions, unknowns, stale, or disputed.

## 7. Opportunity record

Each evaluated opportunity SHALL maintain one controlled record containing:

1. Opportunity brief.
2. Signal register.
3. Problem and pressure profile.
4. Asset–actor–authority map.
5. Technical and dependency screen.
6. Funding, procurement, and implementation pathway.
7. AnchorFiber alignment and boundary assessment.
8. Evidence register with V/S/A/U/D labels.
9. Scorecard and gate results.
10. Risk, limitation, and unresolved-question register.
11. Decision record and authorized next step.
12. Review history and learning notes.

Recommended identifier: `SIO-[YEAR]-[NNN]`.

## 8. Review cycle

### 8.1 Discovery review

Confirm that the lead has a bounded geography, infrastructure condition, affected actor, and credible initiating signal.

### 8.2 Evidence review

Challenge source authority, currency, geographic fit, contradictions, assumptions, and missing decisive evidence.

### 8.3 Domain review

Use appropriate specialists to challenge technical, operational, financial, procurement, legal, regulatory, environmental, community, and delivery assumptions. External review is challenge evidence, not endorsement.

### 8.4 Decision review

Approve the decision, next action, resource ceiling, owner, and expiration date. Record accepted, modified, deferred, rejected, and out-of-scope comments with reasons.

### 8.5 Revalidation review

Reopen an opportunity when a material condition changes, including:

- new solicitation, grant, budget, or regulatory action;
- changed customer authority or sponsorship;
- route, asset, ownership, or coverage correction;
- material cost, schedule, supplier, or technology change;
- loss or addition of a delivery partner;
- new competing solution;
- expired evidence;
- changed AnchorFiber capability or company capacity.

No previous Pursue decision survives automatically when its justifying conditions materially change.

## 9. Proof and limitations

S.P.A.T.I.A.L. owns these bounded claims:

- **SIO-C1:** Infrastructure opportunity decisions can be made traceable to explicit signals, evidence, assumptions, scores, gates, and review dates.
- **SIO-C2:** The method distinguishes infrastructure need from reachable, fundable demand.
- **SIO-C3:** The method exposes asset, actor, authority, technical, temporal, investment, alignment, and lifecycle constraints before substantial pursuit resources are committed.
- **SIO-C4:** The method supports repeatable comparison and revalidation of opportunity decisions.

S.P.A.T.I.A.L. does **not** claim to:

- certify source truth, engineering design, cybersecurity, safety, legal compliance, funding eligibility, or financial returns;
- replace field surveys, licensed engineering, legal counsel, environmental review, procurement review, or customer due diligence;
- guarantee awards, customers, deployment, revenue, or operational outcomes;
- determine continuation validity for operating infrastructure systems;
- establish authority that has not been granted by the relevant owner or institution.

These claims remain proposed until the methodology is exercised against representative opportunities, decision records are produced, and scoring consistency is reviewed.

## 10. Initial verification plan

Version 0.1 SHOULD be tested against at least three different opportunity types:

1. a rural or underserved broadband/fiber opportunity;
2. a critical-facility resilience or route-redundancy opportunity;
3. a municipal, utility, industrial, defense, or data-center infrastructure opportunity.

For each case, retain the complete opportunity record, decision, reviewer comments, elapsed analysis time, and later outcome. Compare whether different reviewers reach materially similar scores from the same evidence and whether the gates prevent premature pursuit.

Minimum acceptance criteria for Version 0.2:

- every required field can be completed or explicitly marked unknown;
- every score can be traced to evidence;
- fatal constraints override the numeric score;
- the decision names a bounded next action and expiration date;
- reviewers can distinguish fact, inference, assumption, unknown, and dispute;
- no output is mistaken for engineering, legal, funding, or commercial certification;
- lessons from completed cases produce documented threshold or worksheet improvements.

## Appendix A — Rapid S.P.A.T.I.A.L. screen

Use this screen to decide whether a lead deserves a full record.

| Question | Yes | Partial | No/Unknown | Evidence reference |
|---|:---:|:---:|:---:|---|
| Is the geography bounded? | ☐ | ☐ | ☐ | |
| Is there a credible infrastructure signal? | ☐ | ☐ | ☐ | |
| Is the affected actor identifiable? | ☐ | ☐ | ☐ | |
| Is the consequence observable or measurable? | ☐ | ☐ | ☐ | |
| Is there a plausible authority or sponsor path? | ☐ | ☐ | ☐ | |
| Is a credible technical response conceivable? | ☐ | ☐ | ☐ | |
| Is there a timing trigger or decision window? | ☐ | ☐ | ☐ | |
| Is there a plausible funding or procurement mechanism? | ☐ | ☐ | ☐ | |
| Is there a bounded AnchorFiber role? | ☐ | ☐ | ☐ | |
| Can the next uncertainty be resolved at proportionate cost? | ☐ | ☐ | ☐ | |

**Rapid-screen disposition:** Full assessment / Monitor / Archive  
**Reason:**  
**Owner:**  
**Review date:**

## Appendix B — Decision record

**Opportunity ID:**  
**Title:**  
**Decision:** Pursue / Validate / Monitor / Hold / Reject  
**Opportunity Confidence Score:**  
**Confidence label:** High / Moderate / Low  
**Mandatory gates:** S Pass/Fail; P Pass/Fail; A Pass/Fail; T Pass/Fail; I Pass/Fail; A Pass/Fail; L Pass/Fail  

**Verified facts:**  
**Supported inferences:**  
**Material assumptions:**  
**Unknowns or disputes:**  
**Fatal constraints:**  
**Known limitations:**  
**Authorized next action:**  
**Resource ceiling:**  
**Owner:**  
**Decision date:**  
**Expiration/review date:**  
**Revalidation triggers:**  
**Approver:**

## Revision history

| Version | Date | Status | Change |
|---|---|---|---|
| 0.1 | 18 July 2026 | Working Draft | Initial methodology, stages, gates, scoring model, evidence rules, review cycle, and worksheets |
