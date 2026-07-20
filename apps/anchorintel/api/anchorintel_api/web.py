"""Server-rendered Opportunity workspace for the AnchorIntel reference build."""

from __future__ import annotations

from datetime import date
from html import escape
from typing import Any, Iterable
from urllib.parse import quote


def _text(value: Any, fallback: str = "—") -> str:
    rendered = str(value).strip() if value is not None else ""
    return escape(rendered or fallback)


def _layout(title: str, content: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)} · AnchorIntel</title>
  <style>
    :root {{ color-scheme: light; --ink:#10211c; --muted:#60716b; --line:#dce5e1;
      --paper:#ffffff; --wash:#f2f7f5; --anchor:#075d4f; --signal:#d9a441;
      --danger:#a6382c; --shadow:0 18px 50px rgba(16,33,28,.09); }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; color:var(--ink); background:linear-gradient(145deg,#edf5f2 0%,#faf8f2 55%,#f5f7f6 100%);
      font:15px/1.55 Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; min-height:100vh; }}
    a {{ color:var(--anchor); text-decoration:none; }} a:hover {{ text-decoration:underline; }}
    header {{ background:#0b2721; color:#fff; border-bottom:4px solid var(--signal); }}
    .bar {{ max-width:1120px; margin:auto; padding:22px 28px; display:flex; align-items:center; justify-content:space-between; gap:20px; }}
    .brand {{ color:#fff; font-size:20px; font-weight:780; letter-spacing:.01em; }}
    .brand span {{ color:#efc66f; }} .tagline {{ color:#b7ccc5; font-size:13px; }}
    main {{ max-width:1120px; margin:auto; padding:48px 28px 72px; }}
    .eyebrow {{ color:var(--anchor); font-size:12px; font-weight:800; letter-spacing:.13em; text-transform:uppercase; }}
    h1 {{ font-size:clamp(30px,5vw,52px); line-height:1.05; letter-spacing:-.04em; margin:8px 0 14px; max-width:900px; }}
    h2 {{ font-size:21px; margin:0 0 18px; }} p {{ margin:0 0 16px; }}
    .lede {{ color:var(--muted); max-width:760px; font-size:17px; }}
    .toolbar {{ display:flex; flex-wrap:wrap; gap:10px; align-items:center; margin:28px 0; }}
    .button,button {{ display:inline-flex; align-items:center; justify-content:center; border:0; border-radius:9px; padding:10px 16px;
      background:var(--anchor); color:#fff; font:inherit; font-weight:750; cursor:pointer; }}
    .button:hover,button:hover {{ filter:brightness(.94); text-decoration:none; }}
    .button.secondary {{ background:#fff; color:var(--anchor); border:1px solid #b9cbc5; }}
    .button.danger,button.danger {{ background:#fff; color:var(--danger); border:1px solid #ddb8b3; }}
    .card {{ background:rgba(255,255,255,.94); border:1px solid var(--line); border-radius:15px; box-shadow:var(--shadow); padding:25px; }}
    .table-wrap {{ overflow-x:auto; }} table {{ width:100%; border-collapse:collapse; }}
    th {{ color:var(--muted); font-size:12px; letter-spacing:.08em; text-transform:uppercase; text-align:left; }}
    th,td {{ padding:15px 12px; border-bottom:1px solid var(--line); vertical-align:top; }} tr:last-child td {{ border:0; }}
    .record-title {{ color:var(--ink); font-weight:780; }}
    .badge {{ display:inline-block; padding:4px 9px; border-radius:999px; background:#e5f2ed; color:var(--anchor); font-size:12px; font-weight:800; }}
    .badge.archived {{ background:#f1e4e1; color:var(--danger); }}
    .badge.file {{ background:#e8edf8; color:#274d83; }} .badge.metadata {{ background:#eef0ef; color:#50605a; }}
    .grid {{ display:grid; grid-template-columns:1.45fr .75fr; gap:22px; margin-top:28px; }}
    .facts {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:0 24px; margin:0; }}
    .facts div {{ border-bottom:1px solid var(--line); padding:14px 0; }} .facts dt {{ color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.07em; }}
    .facts dd {{ margin:4px 0 0; font-weight:700; }}
    .description {{ font-size:17px; line-height:1.7; }}
    .workflow {{ list-style:none; margin:0; padding:0; }} .workflow li {{ display:grid; grid-template-columns:24px 1fr; gap:10px; padding:10px 0; }}
    .workflow .mark {{ width:20px; height:20px; border-radius:50%; border:2px solid #b8c7c2; display:grid; place-items:center; font-size:11px; }}
    .workflow .complete .mark {{ background:var(--anchor); border-color:var(--anchor); color:#fff; }}
    .workflow .pending {{ color:var(--muted); }}
    form {{ margin:0; }} .form-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:18px; }}
    label {{ display:block; font-size:13px; font-weight:750; }} label.full {{ grid-column:1/-1; }}
    input,textarea,select {{ width:100%; margin-top:7px; border:1px solid #b8c9c3; border-radius:9px; padding:11px 12px; background:#fff; color:var(--ink); font:inherit; }}
    textarea {{ min-height:140px; resize:vertical; }} input:focus,textarea:focus,select:focus {{ outline:3px solid rgba(7,93,79,.15); border-color:var(--anchor); }}
    .notice {{ margin:22px 0; border-left:4px solid var(--signal); background:#fff9e9; padding:12px 15px; }}
    .empty {{ text-align:center; color:var(--muted); padding:48px 20px; }}
    .meta {{ color:var(--muted); font-size:13px; }}
    .section-head {{ display:flex; justify-content:space-between; align-items:center; gap:18px; margin-bottom:16px; }}
    .section-head h2 {{ margin:0; }} .hash {{ overflow-wrap:anywhere; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:12px; }}
    @media (max-width:760px) {{ .grid,.form-grid {{ grid-template-columns:1fr; }} label.full {{ grid-column:auto; }} .tagline {{ display:none; }} main {{ padding-top:34px; }} }}
  </style>
</head>
<body>
  <header><div class="bar"><a class="brand" href="/opportunities">Anchor<span>Intel</span></a><div class="tagline"><a style="color:#d7e6e1" href="/knowledge-modules">Knowledge Modules</a> · Infrastructure Opportunity Intelligence</div></div></header>
  <main>{content}</main>
</body>
</html>"""


def opportunity_list(
    opportunities: Iterable[dict[str, Any]],
    include_archived: bool = False,
    notice: str = "",
) -> str:
    items = list(opportunities)
    rows = "".join(
        f"""<tr>
          <td><a class="record-title" href="/opportunities/{quote(str(item['opportunity_id']))}{'?include_archived=true' if item.get('archived') else ''}">{_text(item.get('opportunity_id'))}</a></td>
          <td><a class="record-title" href="/opportunities/{quote(str(item['opportunity_id']))}{'?include_archived=true' if item.get('archived') else ''}">{_text(item.get('title'))}</a><div class="meta">{_text(item.get('organization'))}</div></td>
          <td>{_text(item.get('sector'))}</td>
          <td><span class="badge{' archived' if item.get('archived') else ''}">{'Archived' if item.get('archived') else _text(item.get('status'), 'New')}</span></td>
          <td class="meta">{_text(item.get('updated_at'))}</td>
        </tr>"""
        for item in items
    )
    if not rows:
        rows = '<tr><td class="empty" colspan="5">No opportunities in this view.</td></tr>'
    notice_html = f'<div class="notice">{escape(notice)}</div>' if notice else ""
    toggle = (
        '<a class="button secondary" href="/opportunities">Active opportunities</a>'
        if include_archived
        else '<a class="button secondary" href="/opportunities?include_archived=true">Include archived</a>'
    )
    return _layout(
        "Opportunities",
        f"""<div class="eyebrow">Opportunity Service · BOOT-0020</div>
        <h1>Opportunity intelligence starts here.</h1>
        <p class="lede">Create and steward durable opportunity records before evidence, knowledge modules, assessment, and reporting are applied.</p>
        {notice_html}
        <div class="toolbar">{toggle}<span class="meta">{len(items)} record{'s' if len(items) != 1 else ''}</span></div>
        <section class="card table-wrap"><table>
          <thead><tr><th>ID</th><th>Opportunity</th><th>Sector</th><th>Status</th><th>Updated</th></tr></thead>
          <tbody>{rows}</tbody>
        </table></section>""",
    )


def opportunity_detail(
    record: dict[str, Any],
    evidence_records: Iterable[dict[str, Any]] = (),
    notice: str = "",
    knowledge_reviews: Iterable[dict[str, Any]] = (),
    knowledge_modules: Iterable[dict[str, Any]] = (),
    assessments: Iterable[dict[str, Any]] = (),
) -> str:
    archived = bool(record.get("archived"))
    evidence_items = list(evidence_records)
    active_count = sum(not item.get("archived") for item in evidence_items)
    workflow = record.get("workflow") or []
    workflow_html = "".join(
        f'<li class="{escape(str(step.get("state", "pending")))}"><span class="mark">{"✓" if step.get("state") == "complete" else ""}</span><span>{_text(step.get("label"))}</span></li>'
        for step in workflow
    ) or '<li class="pending"><span class="mark"></span><span>Workflow not initialized</span></li>'
    archive_action = (
        '<span class="badge archived">Archived</span>'
        if archived
        else f"""<form method="post" action="/opportunities/{quote(str(record['opportunity_id']))}/archive">
          <button class="danger" type="submit">Archive opportunity</button>
        </form>"""
    )
    edit_action = "" if archived else f'<a class="button" href="/opportunities/{quote(str(record["opportunity_id"]))}/edit">Edit opportunity</a>'
    notice_html = f'<div class="notice">{escape(notice)}</div>' if notice else ""
    evidence_rows = "".join(
        f"""<tr class="{'archived-row' if item.get('archived') else ''}">
          <td><a class="record-title" href="/opportunities/{quote(str(record['opportunity_id']))}/evidence/{quote(str(item['evidence_id']))}">{_text(item.get('evidence_id'))}</a></td>
          <td><a class="record-title" href="/opportunities/{quote(str(record['opportunity_id']))}/evidence/{quote(str(item['evidence_id']))}">{_text(item.get('title'))}</a><div class="meta">{'Archived evidence' if item.get('archived') else ('File attached' if item.get('file_name') else 'Metadata only')}</div></td>
          <td>{_text(item.get('evidence_type'))}</td>
          <td><span class="badge{' archived' if item.get('archived') else ''}">{'Archived' if item.get('archived') else _text(item.get('evidence_status'))}</span></td>
          <td>{_text(item.get('evidence_confidence'))}</td>
          <td>{_text(item.get('source'))}</td>
          <td>{_text(item.get('date_collected'))}</td>
          <td><a href="/opportunities/{quote(str(record['opportunity_id']))}/evidence/{quote(str(item['evidence_id']))}">View</a></td>
        </tr>"""
        for item in evidence_items
    )
    if not evidence_rows:
        evidence_rows = '<tr><td class="empty" colspan="8">No evidence has been attached.</td></tr>'
    add_evidence = "" if archived else f'<a class="button" href="/opportunities/{quote(str(record["opportunity_id"]))}/evidence/new">Add Evidence</a>'
    review_items = list(knowledge_reviews)
    module_items = list(knowledge_modules)
    review_rows = "".join(
        f"""<tr><td><a class="record-title" href="/opportunities/{quote(str(record['opportunity_id']))}/knowledge-reviews/{quote(str(item['review_id']))}">{_text(item.get('review_id'))}</a></td>
        <td>{_text(item.get('module_id'))}<div class="meta">v{_text(item.get('module_version'))}</div></td>
        <td><span class="badge{' archived' if item.get('stale') else ''}">{'Stale' if item.get('stale') else _text(item.get('review_status'))}</span></td>
        <td>{_text(item.get('confidence'))}</td><td>{_text(item.get('summary', {}).get('finding_count'), '0')} findings · {_text(item.get('summary', {}).get('unknown_count'), '0')} unknowns</td>
        <td class="meta">{_text(item.get('created_at'))}</td><td><a href="/opportunities/{quote(str(record['opportunity_id']))}/knowledge-reviews/{quote(str(item['review_id']))}">View</a></td></tr>"""
        for item in review_items
    ) or '<tr><td class="empty" colspan="7">No Knowledge Module reviews have been run.</td></tr>'
    module_options = "".join(
        f'<option value="{escape(str(item["module_id"]))}">{_text(item.get("module_id"))} · {_text(item.get("name"))} · v{_text(item.get("version"))}</option>'
        for item in module_items if item.get("status") == "Active"
    )
    run_review = ""
    if not archived and module_options:
        run_review = f'<a class="button" href="/opportunities/{quote(str(record["opportunity_id"]))}/knowledge-reviews/new">Run Knowledge Review</a>'
    assessment_items = list(assessments)
    assessment_rows = "".join(
        f"""<tr><td><a class="record-title" href="/opportunities/{quote(str(record['opportunity_id']))}/assessments/{quote(str(item['assessment_id']))}">{_text(item.get('assessment_id'))}</a></td>
        <td><span class="badge{' archived' if item.get('stale') else ''}">{'Stale' if item.get('stale') else _text(item.get('recommendation'))}</span></td>
        <td>{_text(item.get('score'))}/100</td><td>{_text(item.get('evidence_confidence'))}</td><td>{_text(item.get('result', {}).get('risk_profile', {}).get('level'))}</td>
        <td>{_text(item.get('knowledge_review_id'))}</td><td class="meta">{_text(item.get('execution_timestamp'))}</td><td><a href="/opportunities/{quote(str(record['opportunity_id']))}/assessments/{quote(str(item['assessment_id']))}">View</a></td></tr>"""
        for item in assessment_items
    ) or '<tr><td class="empty" colspan="8">No operational assessment has been run.</td></tr>'
    run_assessment = ""
    if not archived and record.get("current_knowledge_review"):
        run_assessment = f'<a class="button" href="/opportunities/{quote(str(record["opportunity_id"]))}/assessments/new">Run S.P.A.T.I.A.L.</a>'
    return _layout(
        str(record.get("title", "Opportunity")),
        f"""<div class="eyebrow">{_text(record.get('opportunity_id'))} · {'Reference opportunity' if record.get('reference_record') else 'Opportunity record'}</div>
        <h1>{_text(record.get('title'))}</h1>
        <p class="lede">{_text(record.get('organization'))} · {_text(record.get('sector'))}</p>
        <div class="toolbar"><a class="button secondary" href="/opportunities{'?include_archived=true' if archived else ''}">← Opportunity list</a>{edit_action}{archive_action}</div>
        {notice_html}
        <div class="grid">
          <section class="card"><h2>Opportunity profile</h2><p class="description">{_text(record.get('description'))}</p>
            <dl class="facts">
              <div><dt>Organization</dt><dd>{_text(record.get('organization'))}</dd></div>
              <div><dt>Status</dt><dd>{'Archived' if archived else _text(record.get('status'), 'New')}</dd></div>
              <div><dt>Sector</dt><dd>{_text(record.get('sector'))}</dd></div>
              <div><dt>Geography</dt><dd>{_text(record.get('geography'))}</dd></div>
              <div><dt>Infrastructure class</dt><dd>{_text(record.get('infrastructure_class'))}</dd></div>
              <div><dt>Lifecycle state</dt><dd>{_text(record.get('lifecycle_state'))}</dd></div>
              <div><dt>Revision</dt><dd>{_text(record.get('revision'))}</dd></div>
              <div><dt>Created</dt><dd>{_text(record.get('created_at'))}</dd></div>
            </dl>
          </section>
          <aside class="card"><h2>S.P.A.T.I.A.L. lifecycle</h2><ol class="workflow">{workflow_html}</ol></aside>
        </div>
        <section class="card table-wrap" style="margin-top:22px">
          <div class="section-head"><div><h2>Evidence</h2><div class="meta">{active_count} active · {len(evidence_items)} total</div></div>{add_evidence}</div>
          <table><thead><tr><th>ID</th><th>Evidence</th><th>Type</th><th>Status</th><th>Confidence</th><th>Source</th><th>Collected</th><th></th></tr></thead>
          <tbody>{evidence_rows}</tbody></table>
        </section>
        <section class="card table-wrap" style="margin-top:22px">
          <div class="section-head"><div><h2>Knowledge Module Review</h2><div class="meta">{len(review_items)} persisted review{'s' if len(review_items) != 1 else ''}; stale results never complete the lifecycle.</div></div><a class="button secondary" href="/knowledge-modules">Module library</a></div>
          {run_review}
          <table style="margin-top:16px"><thead><tr><th>ID</th><th>Module</th><th>Status</th><th>Confidence</th><th>Output</th><th>Created</th><th></th></tr></thead><tbody>{review_rows}</tbody></table>
        </section>
        <section class="card table-wrap" style="margin-top:22px">
          <div class="section-head"><div><h2>S.P.A.T.I.A.L. Assessments</h2><div class="meta">{len(assessment_items)} persisted assessment{'s' if len(assessment_items) != 1 else ''}; stale results do not complete the lifecycle.</div></div>{run_assessment}</div>
          <table><thead><tr><th>ID</th><th>Recommendation</th><th>Score</th><th>Confidence</th><th>Risk</th><th>Review</th><th>Executed</th><th></th></tr></thead><tbody>{assessment_rows}</tbody></table>
        </section>""",
    )


def opportunity_edit(record: dict[str, Any], error: str = "") -> str:
    error_html = f'<div class="notice">{escape(error)}</div>' if error else ""
    return _layout(
        f"Edit {record.get('opportunity_id', 'opportunity')}",
        f"""<div class="eyebrow">Opportunity Service · Edit</div>
        <h1>Edit {_text(record.get('opportunity_id'))}</h1>
        <p class="lede">Changes are revision-controlled and recorded in the administration audit trail.</p>
        {error_html}
        <section class="card" style="margin-top:28px">
          <form method="post" action="/opportunities/{quote(str(record['opportunity_id']))}/edit">
            <input type="hidden" name="revision" value="{_text(record.get('revision'), '1')}">
            <div class="form-grid">
              <label class="full">Title<input required name="title" value="{_text(record.get('title'), '')}"></label>
              <label>Organization<input name="organization" value="{_text(record.get('organization'), '')}"></label>
              <label>Sector<input name="sector" value="{_text(record.get('sector'), '')}"></label>
              <label>Status<select name="status">{_status_options(record.get('status'))}</select></label>
              <label>Geography<input required name="geography" value="{_text(record.get('geography'), '')}"></label>
              <label>Infrastructure class<input required name="infrastructure_class" value="{_text(record.get('infrastructure_class'), '')}"></label>
              <label class="full">Description<textarea name="description">{_text(record.get('description'), '')}</textarea></label>
            </div>
            <div class="toolbar"><button type="submit">Save changes</button><a class="button secondary" href="/opportunities/{quote(str(record['opportunity_id']))}">Cancel</a></div>
          </form>
        </section>""",
    )


def _status_options(selected: Any) -> str:
    selected_value = str(selected or "New")
    values = ["New", "Discovery", "Qualified", "Monitor", "Hold", "Pursue"]
    if selected_value not in values:
        values.append(selected_value)
    return "".join(
        f'<option value="{escape(value)}"{" selected" if value == selected_value else ""}>{escape(value)}</option>'
        for value in values
    )


def _options(values: Iterable[str], selected: Any) -> str:
    selected_value = str(selected or "")
    return "".join(
        f'<option value="{escape(value)}"{" selected" if value == selected_value else ""}>{escape(value)}</option>'
        for value in values
    )


def evidence_form(
    opportunity: dict[str, Any],
    evidence: dict[str, Any] | None = None,
    error: str = "",
) -> str:
    editing = evidence is not None
    item = evidence or {
        "evidence_type": "Document",
        "evidence_status": "Collected",
        "evidence_confidence": "Unknown",
        "date_collected": date.today().isoformat(),
    }
    opportunity_id = str(opportunity["opportunity_id"])
    action = (
        f"/opportunities/{quote(opportunity_id)}/evidence/{quote(str(item['evidence_id']))}/edit"
        if editing
        else f"/opportunities/{quote(opportunity_id)}/evidence"
    )
    error_html = f'<div class="notice">{escape(error)}</div>' if error else ""
    revision = (
        f'<input type="hidden" name="revision" value="{_text(item.get("revision"), "1")}">'
        if editing
        else ""
    )
    file_control = (
        ""
        if editing
        else '<label class="full">Evidence file (optional, 10 MiB maximum)<input type="file" name="file"></label>'
    )
    current_file = (
        f'<div class="notice">Attached file: {_text(item.get("file_name"))}. File replacement is intentionally deferred; metadata may be edited without altering stored bytes.</div>'
        if editing and item.get("file_name")
        else ""
    )
    return _layout(
        f"{'Edit' if editing else 'Add'} Evidence",
        f"""<div class="eyebrow">{_text(opportunity_id)} · Evidence Service</div>
        <h1>{'Edit evidence metadata' if editing else 'Add evidence'}</h1>
        <p class="lede">{_text(opportunity.get('title'))}</p>{error_html}{current_file}
        <section class="card" style="margin-top:28px">
          <form method="post" action="{action}" enctype="{'application/x-www-form-urlencoded' if editing else 'multipart/form-data'}">
            {revision}<div class="form-grid">
              <label class="full">Title<input required name="title" value="{_text(item.get('title'), '')}"></label>
              <label>Evidence type<select required name="evidence_type">{_options(['Document','Dataset','Web Source','Field Observation','Photograph','Correspondence','Regulatory Record','Financial Record','Technical Record','Other'], item.get('evidence_type'))}</select></label>
              <label>Source<input name="source" value="{_text(item.get('source'), '')}"></label>
              <label>Source date<input type="date" name="source_date" value="{_text(item.get('source_date'), '')}"></label>
              <label>Date collected<input type="date" required name="date_collected" value="{_text(item.get('date_collected'), '')}"></label>
              <label>Status<select required name="evidence_status">{_options(['Collected','Under Review','Accepted','Questioned','Superseded'], item.get('evidence_status'))}</select></label>
              <label>Confidence<select required name="evidence_confidence">{_options(['Unknown','Low','Moderate','High','Verified'], item.get('evidence_confidence'))}</select></label>
              <label class="full">Description<textarea name="description">{_text(item.get('description'), '')}</textarea></label>
              <label class="full">Notes<textarea name="notes">{_text(item.get('notes'), '')}</textarea></label>
              {file_control}
            </div>
            <div class="toolbar"><button type="submit">{'Save metadata' if editing else 'Add evidence'}</button><a class="button secondary" href="/opportunities/{quote(opportunity_id)}">Cancel</a></div>
          </form>
        </section>""",
    )


def evidence_detail(opportunity: dict[str, Any], evidence: dict[str, Any]) -> str:
    archived = bool(evidence.get("archived"))
    opportunity_id = str(opportunity["opportunity_id"])
    evidence_id = str(evidence["evidence_id"])
    file_panel = (
        f"""<div class="notice"><strong>Attached file</strong><br>{_text(evidence.get('file_name'))} · {_text(evidence.get('file_type'))} · {_text(evidence.get('file_size'), '0')} bytes<br>
        <span class="hash">SHA-256: {_text(evidence.get('sha256'))}</span><br><a href="/opportunities/{quote(opportunity_id)}/evidence/{quote(evidence_id)}/file">View or download file</a></div>"""
        if evidence.get("file_name")
        else '<div class="notice"><strong>Metadata-only evidence.</strong> No file is attached to this record.</div>'
    )
    actions = (
        '<span class="badge archived">Archived evidence</span>'
        if archived
        else f"""<a class="button" href="/opportunities/{quote(opportunity_id)}/evidence/{quote(evidence_id)}/edit">Edit metadata</a>
        <form method="post" action="/opportunities/{quote(opportunity_id)}/evidence/{quote(evidence_id)}/archive"><input type="hidden" name="revision" value="{_text(evidence.get('revision'), '1')}"><button class="danger" type="submit">Archive evidence</button></form>"""
    )
    return _layout(
        evidence_id,
        f"""<div class="eyebrow">{_text(evidence_id)} · Evidence record</div><h1>{_text(evidence.get('title'))}</h1>
        <p class="lede">Attached to <a href="/opportunities/{quote(opportunity_id)}">{_text(opportunity.get('title'))}</a></p>
        <div class="toolbar"><a class="button secondary" href="/opportunities/{quote(opportunity_id)}">← Opportunity</a>{actions}</div>{file_panel}
        <section class="card"><h2>Evidence metadata</h2><p class="description">{_text(evidence.get('description'))}</p>
          <dl class="facts">
            <div><dt>Internal database ID</dt><dd>{_text(evidence.get('internal_id'))}</dd></div><div><dt>Evidence ID</dt><dd>{_text(evidence_id)}</dd></div>
            <div><dt>Type</dt><dd>{_text(evidence.get('evidence_type'))}</dd></div><div><dt>Status</dt><dd>{'Archived' if archived else _text(evidence.get('evidence_status'))}</dd></div>
            <div><dt>Confidence</dt><dd>{_text(evidence.get('evidence_confidence'))}</dd></div><div><dt>Source</dt><dd>{_text(evidence.get('source'))}</dd></div>
            <div><dt>Source date</dt><dd>{_text(evidence.get('source_date'))}</dd></div><div><dt>Date collected</dt><dd>{_text(evidence.get('date_collected'))}</dd></div>
            <div><dt>Revision</dt><dd>{_text(evidence.get('revision'))}</dd></div><div><dt>Updated</dt><dd>{_text(evidence.get('updated_at'))}</dd></div>
            <div><dt>Archived at</dt><dd>{_text(evidence.get('archived_at'))}</dd></div><div><dt>Storage</dt><dd>{_text(evidence.get('storage_location'))}</dd></div>
          </dl><h2 style="margin-top:24px">Notes</h2><p>{_text(evidence.get('notes'))}</p>
        </section>""",
    )


def knowledge_module_list(modules: Iterable[dict[str, Any]]) -> str:
    items = list(modules)
    rows = "".join(
        f"""<tr><td><a class="record-title" href="/knowledge-modules/{quote(str(item['module_id']))}">{_text(item.get('module_id'))}</a></td>
        <td><a class="record-title" href="/knowledge-modules/{quote(str(item['module_id']))}">{_text(item.get('name'))}</a><div class="meta">{_text(item.get('domain'))} · {_text(item.get('jurisdiction'))}</div></td>
        <td>{_text(item.get('version'))}</td><td><span class="badge">{_text(item.get('status'))}</span></td><td>{_text(item.get('review_question_count'), '0')}</td><td>{_text(item.get('review_date'))}</td></tr>"""
        for item in items
    ) or '<tr><td class="empty" colspan="6">No active Knowledge Modules are installed.</td></tr>'
    return _layout(
        "Knowledge Modules",
        f"""<div class="eyebrow">Knowledge Service · Sprint 3</div><h1>Versioned, bounded review logic.</h1>
        <p class="lede">Modules are local, deterministic definitions with integrity hashes. They do not browse the internet or invoke an AI model.</p>
        <div class="toolbar"><a class="button secondary" href="/opportunities">← Opportunities</a></div>
        <section class="card table-wrap"><table><thead><tr><th>ID</th><th>Module</th><th>Version</th><th>Status</th><th>Questions</th><th>Review date</th></tr></thead><tbody>{rows}</tbody></table></section>""",
    )


def knowledge_review_form(
    opportunity: dict[str, Any], modules: Iterable[dict[str, Any]]
) -> str:
    opportunity_id = str(opportunity["opportunity_id"])
    options = "".join(
        f'<option value="{escape(str(item["module_id"]))}">{_text(item.get("module_id"))} · {_text(item.get("name"))} · v{_text(item.get("version"))}</option>'
        for item in modules
        if item.get("status") == "Active"
    )
    return _layout(
        "Run Knowledge Review",
        f"""<div class="eyebrow">{_text(opportunity_id)} · Knowledge Service</div><h1>Run Knowledge Review</h1>
        <p class="lede">Apply one version-controlled, deterministic module to the current opportunity revision and active evidence trace.</p>
        <section class="card" style="margin-top:28px"><form method="post" action="/opportunities/{quote(opportunity_id)}/knowledge-reviews">
        <div class="form-grid"><label class="full">Knowledge Module<select required name="module_id">{options}</select></label>
        <label>Review status<select name="review_status"><option value="Completed">Completed</option><option value="Draft">Draft</option><option value="Ready">Ready</option><option value="Incomplete">Incomplete</option></select></label></div>
        <div class="notice">This run uses only persisted local records. It does not browse the internet, invoke an external AI model, or independently verify evidence.</div>
        <div class="toolbar"><button type="submit">Run module</button><a class="button secondary" href="/opportunities/{quote(opportunity_id)}">Cancel</a></div></form></section>""",
    )


def knowledge_module_detail(module: dict[str, Any]) -> str:
    questions = "".join(
        f'<li><strong>{_text(item.get("question_id"))}</strong> — {_text(item.get("question"))}</li>'
        for item in module.get("review_questions", [])
    )
    limitations = "".join(f"<li>{_text(item)}</li>" for item in module.get("known_limitations", []))
    return _layout(
        str(module.get("module_id", "Knowledge Module")),
        f"""<div class="eyebrow">{_text(module.get('module_id'))} · v{_text(module.get('version'))}</div><h1>{_text(module.get('name'))}</h1>
        <p class="lede">{_text(module.get('description'))}</p><div class="toolbar"><a class="button secondary" href="/knowledge-modules">← Module library</a><span class="badge">{_text(module.get('status'))}</span></div>
        <div class="grid"><section class="card"><h2>Review questions</h2><ol>{questions}</ol></section><aside class="card"><h2>Definition</h2><dl class="facts">
        <div><dt>Publisher</dt><dd>{_text(module.get('publisher'))}</dd></div><div><dt>Jurisdiction</dt><dd>{_text(module.get('jurisdiction'))}</dd></div>
        <div><dt>Effective</dt><dd>{_text(module.get('effective_date'))}</dd></div><div><dt>Review date</dt><dd>{_text(module.get('review_date'))}</dd></div></dl>
        <h2 style="margin-top:24px">Integrity hash</h2><p class="hash">{_text(module.get('integrity_hash'))}</p><h2>Known limitations</h2><ul>{limitations}</ul></aside></div>""",
    )


def _review_section(title: str, items: Iterable[Any], empty: str) -> str:
    rendered = "".join(
        f"<li>{_text(item.get('statement') or item.get('reason') or item.get('rationale') or item)}</li>"
        if isinstance(item, dict) else f"<li>{_text(item)}</li>"
        for item in items
    )
    return f"<section style=\"margin-top:24px\"><h2>{escape(title)}</h2><ul>{rendered or f'<li class=\"meta\">{escape(empty)}</li>'}</ul></section>"


def knowledge_review_detail(
    opportunity: dict[str, Any], review: dict[str, Any]
) -> str:
    output = review.get("output", {})
    opportunity_id = str(opportunity["opportunity_id"])
    review_id = str(review["review_id"])
    findings = "".join(
        f"""<tr><td>{_text(item.get('question_id'))}</td><td><span class="badge">{_text(item.get('disposition'))}</span></td><td>{_text(item.get('rationale'))}</td><td>{_text(', '.join(item.get('evidence_ids', [])))}</td></tr>"""
        for item in output.get("findings", [])
    )
    trace = "".join(
        f"<tr><td>{_text(item.get('evidence_id'))}</td><td>{_text(item.get('revision'))}</td><td>{_text(item.get('evidence_status'))}</td><td>{_text(item.get('evidence_confidence'))}</td><td class=\"hash\">{_text(item.get('sha256'))}</td></tr>"
        for item in review.get("evidence_trace", [])
    ) or '<tr><td class="empty" colspan="5">No active evidence was consumed.</td></tr>'
    stale = bool(review.get("stale"))
    stale_html = _review_section("Staleness", review.get("stale_reasons", []), "Current") if stale else '<div class="notice"><strong>Current review.</strong> The persisted opportunity revision, active evidence trace, module version, and module hash still match.</div>'
    actions = ""
    if review.get("review_status") in {"Draft", "Ready", "Incomplete"} and not stale:
        actions += f'<form method="post" action="/opportunities/{quote(opportunity_id)}/knowledge-reviews/{quote(review_id)}/complete"><input type="hidden" name="revision" value="{_text(review.get("revision"), "1")}"><button type="submit">Complete review</button></form>'
    if review.get("review_status") != "Superseded":
        actions += f'<form method="post" action="/opportunities/{quote(opportunity_id)}/knowledge-reviews/{quote(review_id)}/supersede"><button type="submit">Run again and supersede</button></form>'
    return _layout(
        review_id,
        f"""<div class="eyebrow">{_text(review_id)} · Knowledge Review</div><h1>{_text(review.get('module_id'))}</h1><p class="lede">Persisted, replayable output for <a href="/opportunities/{quote(opportunity_id)}">{_text(opportunity.get('title'))}</a>.</p>
        <div class="toolbar"><a class="button secondary" href="/opportunities/{quote(opportunity_id)}">← Opportunity</a>{actions}<span class="badge{' archived' if stale else ''}">{'Stale' if stale else _text(review.get('review_status'))}</span></div>{stale_html}
        <section class="card"><dl class="facts"><div><dt>Confidence</dt><dd>{_text(review.get('confidence'))}</dd></div><div><dt>Revision</dt><dd>{_text(review.get('revision'))}</dd></div>
        <div><dt>Module version</dt><dd>{_text(review.get('module_version'))}</dd></div><div><dt>Opportunity revision</dt><dd>{_text(review.get('opportunity_revision'))}</dd></div>
        <div><dt>Created</dt><dd>{_text(review.get('created_at'))}</dd></div><div><dt>Reviewer source</dt><dd>{_text(review.get('reviewer_source'))}</dd></div></dl>
        <h2 style="margin-top:24px">Findings</h2><div class="table-wrap"><table><thead><tr><th>Question</th><th>Disposition</th><th>Rationale</th><th>Evidence</th></tr></thead><tbody>{findings}</tbody></table></div>
        {_review_section('Assumptions', output.get('assumptions', []), 'None recorded')}{_review_section('Unknowns', output.get('unknowns', []), 'None recorded')}{_review_section('Risks', output.get('risks', []), 'None recorded')}{_review_section('Missing evidence', output.get('missing_evidence', []), 'None recorded')}
        <h2 style="margin-top:24px">Evidence trace</h2><div class="table-wrap"><table><thead><tr><th>Evidence ID</th><th>Revision</th><th>Status</th><th>Confidence</th><th>SHA-256</th></tr></thead><tbody>{trace}</tbody></table></div>
        <h2 style="margin-top:24px">Replay hashes</h2><p class="hash">Module: {_text(review.get('module_integrity_hash'))}<br>Inputs: {_text(review.get('input_snapshot_hash'))}<br>Output: {_text(review.get('output_hash'))}</p>
        <div class="notice"><strong>Reference evidence notice:</strong> {_text(output.get('reference_evidence_notice'))}</div>
        <div class="notice"><strong>Bounded output:</strong> {_text(output.get('disclaimer'))}<br>{_text(' '.join(output.get('limitations', [])))}</div></section>""",
    )


def spatial_assessment_form(
    opportunity: dict[str, Any], readiness: dict[str, Any]
) -> str:
    opportunity_id = str(opportunity["opportunity_id"])
    review = readiness.get("knowledge_review") or {}
    warnings = "".join(f"<li>{_text(item)}</li>" for item in readiness.get("warnings", []))
    errors = "".join(f"<li>{_text(item)}</li>" for item in readiness.get("errors", []))
    readiness_panel = (
        '<div class="notice"><strong>Ready.</strong> The current persisted inputs satisfy the execution contract.</div>'
        if readiness.get("ready")
        else f'<div class="notice"><strong>Not ready.</strong><ul>{errors}</ul></div>'
    )
    run_button = (
        f'<button type="submit">Run S.P.A.T.I.A.L.</button><input type="hidden" name="knowledge_review_id" value="{_text(review.get("review_id"), "")}">'
        if readiness.get("ready")
        else '<button type="button" disabled>Run unavailable</button>'
    )
    return _layout(
        "Run S.P.A.T.I.A.L.",
        f"""<div class="eyebrow">{_text(opportunity_id)} · Assessment Service</div><h1>Run S.P.A.T.I.A.L.</h1>
        <p class="lede">Execute the installed engine against one immutable snapshot of the current opportunity revision, active evidence trace, and completed Knowledge Review.</p>
        {readiness_panel}
        <div class="grid"><section class="card"><h2>Execution inputs</h2><dl class="facts">
        <div><dt>Knowledge Review</dt><dd>{_text(review.get('review_id'))}</dd></div><div><dt>Review status</dt><dd>{_text(review.get('review_status'))}</dd></div>
        <div><dt>Module</dt><dd>{_text(review.get('module_id'))} v{_text(review.get('module_version'))}</dd></div><div><dt>Review confidence</dt><dd>{_text(review.get('confidence'))}</dd></div>
        <div><dt>Engine</dt><dd>S.P.A.T.I.A.L. v{_text(readiness.get('engine_version'))}</dd></div><div><dt>Adapter</dt><dd>v{_text(readiness.get('adapter_version'))}</dd></div>
        </dl><h2 style="margin-top:24px">Input hash</h2><p class="hash">{_text(readiness.get('input_hash'))}</p></section>
        <aside class="card"><h2>Readiness warnings</h2><ul>{warnings or '<li class="meta">No warnings recorded.</li>'}</ul></aside></div>
        <div class="notice">{_text(readiness.get('bounded_execution_notice'))}</div>
        <form method="post" action="/opportunities/{quote(opportunity_id)}/assessments"><div class="toolbar">{run_button}<a class="button secondary" href="/opportunities/{quote(opportunity_id)}">Cancel</a></div></form>""",
    )


def spatial_assessment_detail(
    opportunity: dict[str, Any], assessment: dict[str, Any], notice: str = ""
) -> str:
    opportunity_id = str(opportunity["opportunity_id"])
    assessment_id = str(assessment["assessment_id"])
    result = assessment.get("result", {})
    risk = result.get("risk_profile", {})
    gate_rows = "".join(
        f"<tr><td>{_text(key)}</td><td><span class=\"badge{' archived' if value.get('status') == 'fail' else ''}\">{_text(value.get('status'))}</span></td><td>{_text(value.get('rationale'))}</td><td>{_text(', '.join(value.get('evidence_refs', [])))}</td></tr>"
        for key, value in result.get("gates", {}).items()
    )
    trace_rows = "".join(
        f"<tr><td>{_text(item.get('evidence_id'))}</td><td>{_text(item.get('revision'))}</td><td>{_text(item.get('evidence_status'))}</td><td>{_text(item.get('evidence_confidence'))}</td><td class=\"hash\">{_text(item.get('sha256'))}</td></tr>"
        for item in result.get("evidence_trace", [])
    ) or '<tr><td class="empty" colspan="5">No evidence trace was stored.</td></tr>'
    engine_assumptions = [
        item.get("claim", "") if isinstance(item, dict) else item
        for item in result.get("assumptions", [])
    ]
    knowledge_assumptions = [
        item.get("statement", "") if isinstance(item, dict) else item
        for item in result.get("knowledge_assumptions", [])
    ]
    stale = bool(assessment.get("stale"))
    stale_panel = (
        _review_section(
            "Staleness", assessment.get("stale_reasons", []), "Current"
        )
        if stale
        else '<div class="notice"><strong>Current assessment.</strong> Opportunity revision, evidence trace, Knowledge Review, adapter, and engine still match.</div>'
    )
    notice_html = f'<div class="notice">{escape(notice)}</div>' if notice else ""
    return _layout(
        assessment_id,
        f"""<div class="eyebrow">{_text(assessment_id)} · S.P.A.T.I.A.L. Assessment</div><h1>{_text(result.get('recommendation'))}</h1>
        <p class="lede">Operational decision output for <a href="/opportunities/{quote(opportunity_id)}">{_text(opportunity.get('title'))}</a>.</p>
        <div class="toolbar"><a class="button secondary" href="/opportunities/{quote(opportunity_id)}">← Opportunity</a>
        <form method="post" action="/opportunities/{quote(opportunity_id)}/assessments/{quote(assessment_id)}/replay"><button type="submit">Replay stored snapshot</button></form>
        <span class="badge{' archived' if stale else ''}">{'Stale' if stale else 'Current'}</span></div>{notice_html}{stale_panel}
        <div class="grid"><section class="card"><h2>Decision</h2><dl class="facts">
        <div><dt>Recommendation</dt><dd>{_text(result.get('recommendation'))}</dd></div><div><dt>Score</dt><dd>{_text(result.get('score'))}/100</dd></div>
        <div><dt>Confidence</dt><dd>{_text(result.get('confidence'))}</dd></div><div><dt>Risk profile</dt><dd>{_text(risk.get('level'))}</dd></div>
        <div><dt>Knowledge Review</dt><dd><a href="/opportunities/{quote(opportunity_id)}/knowledge-reviews/{quote(str(assessment.get('knowledge_review_id', '')))}">{_text(assessment.get('knowledge_review_id'))}</a></dd></div>
        <div><dt>Executed</dt><dd>{_text(assessment.get('execution_timestamp'))}</dd></div></dl>
        <h2 style="margin-top:24px">Engine explanation</h2><p>{_text(result.get('explanation', {}).get('engine'))}</p></section>
        <aside class="card"><h2>Execution identity</h2><dl class="facts"><div><dt>Engine</dt><dd>v{_text(assessment.get('engine_version'))}</dd></div><div><dt>Adapter</dt><dd>v{_text(assessment.get('adapter_version'))}</dd></div>
        <div><dt>Revision</dt><dd>{_text(assessment.get('revision'))}</dd></div><div><dt>Assessment date</dt><dd>{_text(result.get('assessment_date'))}</dd></div></dl>
        <h2 style="margin-top:24px">Replay hash</h2><p class="hash">{_text(assessment.get('replay_hash'))}</p></aside></div>
        <section class="card" style="margin-top:22px"><h2>Gate results</h2><div class="table-wrap"><table><thead><tr><th>Gate</th><th>Status</th><th>Rationale</th><th>Evidence</th></tr></thead><tbody>{gate_rows}</tbody></table></div>
        {_review_section('Assumptions', engine_assumptions + knowledge_assumptions, 'None recorded')}
        {_review_section('Warnings', result.get('warnings', []), 'None recorded')}
        <h2 style="margin-top:24px">Evidence trace</h2><div class="table-wrap"><table><thead><tr><th>Evidence ID</th><th>Revision</th><th>Status</th><th>Confidence</th><th>SHA-256</th></tr></thead><tbody>{trace_rows}</tbody></table></div>
        <div class="notice" style="margin-top:24px"><strong>Bounded execution:</strong> {_text(result.get('explanation', {}).get('input_derivation', {}).get('bounded_input_notice'))}</div></section>""",
    )


def error_page(status: int, message: str) -> str:
    return _layout(
        f"Error {status}",
        f"""<div class="eyebrow">AnchorIntel could not complete the request</div>
        <h1>{status}</h1><p class="lede">{escape(message)}</p>
        <div class="toolbar"><a class="button" href="/opportunities">Return to opportunities</a></div>""",
    )
