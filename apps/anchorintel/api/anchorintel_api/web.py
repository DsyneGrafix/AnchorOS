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
  <header><div class="bar"><a class="brand" href="/opportunities">Anchor<span>Intel</span></a><div class="tagline">Infrastructure Opportunity Intelligence</div></div></header>
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


def error_page(status: int, message: str) -> str:
    return _layout(
        f"Error {status}",
        f"""<div class="eyebrow">AnchorIntel could not complete the request</div>
        <h1>{status}</h1><p class="lede">{escape(message)}</p>
        <div class="toolbar"><a class="button" href="/opportunities">Return to opportunities</a></div>""",
    )
