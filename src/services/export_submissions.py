"""
Service for exporting submission metadata to markdown format.
"""

import re
from typing import List, Iterable
from datetime import datetime

import pandas as pd

from config.enums.states import SubmissionStatesEnums


# ---------- formatting helpers ----------

def _ts(v) -> str:
    """Format a timestamp (ms or s since epoch)."""
    if v is None:
        return ""
    if hasattr(v, "to_native"):
        v = v.to_native()
    if isinstance(v, (int, float)):
        if v > 1e11:  # neo4j timestamp() is in milliseconds
            v = v / 1000
        v = datetime.fromtimestamp(v)
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M")
    return str(v)


def _state_name(state_tag) -> str:
    if state_tag is None:
        return ""
    try:
        return SubmissionStatesEnums(int(state_tag)).name.replace("_", " ").title()
    except (ValueError, TypeError):
        return str(state_tag)


def _cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and pd.isna(v):
        return ""
    if isinstance(v, (list, tuple, set)):
        return ", ".join(_cell(x) for x in v if x not in (None, ""))
    return str(v).replace("|", "\\|").replace("\n", " ").strip()


def _table(headers: List[str], rows: Iterable) -> str:
    rows = list(rows)
    if not rows:
        return ""
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += ["| " + " | ".join(_cell(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def _section(title: str, body: str) -> str:
    return f"## {title}\n\n{body}\n" if body else f"## {title}\n"


def _demote_headings(text: str, min_level: int) -> str:
    """Shift markdown headings so the highest one in `text` becomes `min_level`."""
    lines = text.splitlines()
    levels = [len(m.group(1)) for line in lines if (m := re.match(r"^(#{1,6})\s", line))]
    if not levels:
        return text
    shift = max(0, min_level - min(levels))
    return "\n".join(
        re.sub(r"^(#{1,6})(\s)", lambda m: "#" * min(6, len(m.group(1)) + shift) + m.group(2), line)
        for line in lines
    )


def _column_label(col: str) -> str:
    # "att_compound" -> "Compound"
    return str(col).removeprefix("att_").replace("_", " ").capitalize()


def _attribute_text(db, attribute_tag: str) -> str:
    if attribute_tag == "sample_tag":
        return "Sample"
    if attribute_tag in ("replicate", "genotype"):
        return attribute_tag.capitalize()
    if db.attributes.exists(tag=attribute_tag):
        return db.attributes.attribute(tag=attribute_tag).text
    return _column_label(attribute_tag)


def _attribute_priority(db, attribute_tag: str) -> int:
    try:
        return db.attributes.get_priority(tag=attribute_tag) or 0
    except ValueError:
        return 0


def _user_name(db, user_tag: str) -> str:
    if not user_tag or not db.users.exists(tag=user_tag):
        return ""
    u = db.users.get_user_by_tag(tag=user_tag)
    return f"{u.firstname or ''} {u.lastname or ''}".strip()


# ---------- sections ----------

def format_overview(submission_tag: str, db) -> str:
    lines = [
        f"- **State:** {_state_name(db.submissions.get_state(tag=submission_tag))}",
        f"- **Created:** {_ts(db.submissions.get_created_at(tag=submission_tag))}",
    ]
    return "\n".join(lines) + "\n"


def format_researchers(submission_tag: str, db) -> str:
    creator_tag = db.submissions.get_creator(tag=submission_tag)
    user_tags = db.submissions.get_users(tag=submission_tag)
    rows = []
    for user_tag in user_tags:
        if not db.users.exists(tag=user_tag):
            continue
        u = db.users.get_user_by_tag(tag=user_tag)
        role = "Creator" if user_tag == creator_tag else "Collaborator"
        rows.append([f"{u.firstname or ''} {u.lastname or ''}".strip(), u.email, role])
    rows.sort(key=lambda r: r[2] != "Creator")
    return _section("Researchers", _table(["Name", "Email", "Role"], rows))


def format_research_aim(submission_tag: str, db) -> str:
    aim = (db.submissions.get_research_aim(tag=submission_tag) or "").strip()
    return _section("Research Aim", _demote_headings(aim, min_level=3))


def format_metatexts(submission_tag: str, db) -> str:
    """All metatexts except the research aim, each as its own section."""
    metatexts = []
    for metatext_tag in db.metatexts.find(submission_tag=submission_tag):
        try:
            metatexts.append(db.metatexts.get(tag=metatext_tag))
        except KeyError:
            continue
    metatexts.sort(key=lambda m: m.get("created_at") or 0)

    blocks = []
    for mt in metatexts:
        title = (mt.get("title") or "").strip()
        text = (mt.get("text") or "").strip()
        if not text or ("research" in title.lower() and "aim" in title.lower()):
            continue
        blocks.append(_section(title, _demote_headings(text, min_level=3)))
    return "\n".join(blocks)


def format_condition_applications(submission_tag: str, db) -> str:
    grouped = db.submissions.get_conditions_applications(tag=submission_tag, group_by_attribute=True)
    grouped = sorted(grouped, key=lambda g: -_attribute_priority(db, g.attribute_tag))
    rows = [
        [_attribute_text(db, g.attribute_tag),
         [db.condition_applications.get_text(tag=ca_tag) for ca_tag in g.condition_application_tags]]
        for g in grouped
    ]
    rows = [r for r in rows if any(r[1])]
    return _section("Condition Applications", _table(["Attribute", "Value"], rows))


def format_samples(submission_tag: str, db) -> str:
    # same source as the Samples tab download
    df = db.samples.get_samples_export_data(submission_tag=submission_tag, join=", ")
    if df is None or df.empty:
        return _section("Samples", "")
    headers = [_attribute_text(db, col) for col in df.columns]
    return _section("Samples", _table(headers, df.itertuples(index=False, name=None)))


def format_protocols(submission_tag: str, db, include_text: bool = True) -> str:
    protocol_tags = db.protocols.find(submission_tags=[submission_tag])
    blocks = []
    for protocol_tag in protocol_tags:
        p = db.protocols.get(tag=protocol_tag)
        lines = [f"### {p.title or ''}", ""]
        lines += [f"- **{label}:** {value}" for label, value in
                  [("DOI", p.doi), ("PubMed ID", p.pubmed_id), ("URL", p.url)] if value]
        if include_text and p.text:
            lines += ["", _demote_headings(p.text, min_level=4)]
        blocks.append("\n".join(lines))
    return _section("Protocols", "\n\n".join(blocks))


def format_runlists(submission_tag: str, db) -> str:
    runlists = db.submissions.list_runlists(submission_tag=submission_tag)
    rows = [
        [_ts(rl.created_at),
         db.attributes.get_trait_text(tag=rl.instrument_tag) if rl.instrument_tag else "",
         rl.n_runs, rl.n_plates, rl.fractionated, rl.n_fractions, rl.scrambled,
         _user_name(db, rl.user_tag)]
        for rl in runlists
    ]
    return _section("Run Lists", _table(
        ["Created", "Instrument", "Runs", "Plates", "Fractionated",
         "Fractions", "Scrambled", "Created by"], rows))


def format_state_history(submission_tag: str, db) -> str:
    history = db.submissions.get_state_history(tag=submission_tag)
    rows = [
        [_ts(h.get("created_at")), _state_name(h.get("state_tag")),
         f"{h.get('user_firstname') or ''} {h.get('user_lastname') or ''}".strip()]
        for h in history
    ]
    return _section("State History", _table(["Date", "State", "User"], rows))



# ---------- main ----------

def export_submission_to_markdown(
    submission_tag: str,
    db,
    include_condition_applications: bool = True,
    include_protocols: bool = True,
    include_runlist: bool = True,
    include_samples: bool = True,
    include_metatext: bool = True,
    include_timeline: bool = True,
    include_protocol_text: bool = True  
) -> str:
    """
    Export submission metadata to markdown format.

    Parameters
    ----------
    submission_tag : str
        The tag of the submission to export
    db : DatabaseABC
        The database connection
    include_condition_applications : bool, optional
        Whether to include condition applications, by default True
    include_protocols : bool, optional
        Whether to include protocols, by default True
    include_runlist : bool, optional
        Whether to include run lists, by default True
    include_samples : bool, optional
        Whether to include samples, by default True
    include_metatext : bool, optional
        Whether to include the research aim and other metatexts, by default True
    include_timeline : bool, optional
        Whether to include the timeline of events, by default True
    include_protocol_text : bool, optional
        Whether to include the full text of protocols, by default True

    Returns
    -------
    str
        The markdown content
    """
    parts = [
        f"# {db.submissions.get_title(tag=submission_tag) or ''}\n",
        format_overview(submission_tag, db),
        "> Be aware that meta data might be added during the project's life cycle.\n",
        format_researchers(submission_tag, db),
    ]

    if include_metatext:
        parts.append(format_research_aim(submission_tag, db))
        metatexts = format_metatexts(submission_tag, db)
        if metatexts:
            parts.append(metatexts)
    if include_condition_applications:
        parts.append(format_condition_applications(submission_tag, db))
    if include_samples:
        parts.append(format_samples(submission_tag, db))
    if include_protocols:
        parts.append(format_protocols(submission_tag, db, include_text=include_protocol_text))
    if include_runlist:
        parts.append(format_runlists(submission_tag, db))
    if include_timeline:
        parts.append(format_state_history(submission_tag, db))

    parts.append(f"---\n_Exported from MitoCube on {_ts(datetime.now())}_\n")
    
    return "\n".join(parts)