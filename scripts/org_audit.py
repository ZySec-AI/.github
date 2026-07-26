#!/usr/bin/env python3
"""Org 360° Audit — stdlib only, no pip deps required."""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
TOKEN = os.environ.get("GH_TOKEN", "")
ORG = os.environ.get("ORG", "ZySec-AI")
OUTPUT = "org-audit-report.html"
DATE_30D = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
DATE_90D = datetime.now(timezone.utc) - timedelta(days=90)


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# GitHub API helpers
# ---------------------------------------------------------------------------
def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _get(url: str) -> tuple[Any, dict[str, str]]:
    """Return (parsed_json_or_None, response_headers). Handles 204, 403, 404."""
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw_headers = {k.lower(): v for k, v in resp.getheaders()}
            if resp.status == 204:
                return True, raw_headers
            body = resp.read()
            return json.loads(body) if body else None, raw_headers
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 404, 422, 451):
            return None, {}
        raise
    finally:
        time.sleep(0.1)


def _paginate(base_url: str) -> list[Any]:
    """Follow Link rel=next pagination, return merged list."""
    results: list[Any] = []
    url: str | None = base_url
    while url:
        data, hdrs = _get(url)
        if isinstance(data, list):
            results.extend(data)
        elif data is None:
            break
        link_header = hdrs.get("link", "")
        next_url = None
        for part in link_header.split(","):
            part = part.strip()
            m = re.match(r'<([^>]+)>;\s*rel="next"', part)
            if m:
                next_url = m.group(1)
                break
        url = next_url
    return results


def _link_last_page(url: str) -> int:
    """HEAD-style: fetch with per_page=1, read rel=last page number."""
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            link = {k.lower(): v for k, v in resp.getheaders()}.get("link", "")
    except urllib.error.HTTPError:
        return 0
    finally:
        time.sleep(0.1)
    m = re.search(r'<[^>]+[?&]page=(\d+)[^>]*>;\s*rel="last"', link)
    return int(m.group(1)) if m else 1


# ---------------------------------------------------------------------------
# Data collection
# ---------------------------------------------------------------------------
def collect_org() -> dict[str, Any]:
    log(f"[org] fetching /orgs/{ORG}")
    data, _ = _get(f"https://api.github.com/orgs/{ORG}")
    if not data:
        return {}
    plan = data.get("plan") or {}
    return {
        "plan_name": plan.get("name", "unknown"),
        "seats_used": plan.get("filled_seats", 0),
        "seats_total": plan.get("seats", 0),
        "private_repos": data.get("total_private_repos", 0),
        "public_repos": data.get("public_repos", 0),
        "two_factor_requirement_enabled": data.get("two_factor_requirement_enabled", False),
        "default_repository_permission": data.get("default_repository_permission", "read"),
        "members_can_create_public_repositories": data.get(
            "members_can_create_public_repositories", True
        ),
    }


def collect_repos() -> list[dict[str, Any]]:
    log(f"[repos] listing /orgs/{ORG}/repos")
    raw = _paginate(f"https://api.github.com/orgs/{ORG}/repos?per_page=100&type=all")
    repos = []
    commit_activity_cap = 0
    for r in raw:
        name = r["name"]
        log(f"  [repo] {name}")
        pushed_at_str = r.get("pushed_at") or ""
        inactive = False
        if pushed_at_str:
            try:
                pushed_dt = datetime.fromisoformat(pushed_at_str.replace("Z", "+00:00"))
                inactive = pushed_dt < DATE_90D.replace(tzinfo=timezone.utc)
            except ValueError:
                pass

        default_branch = r.get("default_branch", "main")

        # Branch protection
        bp_data, _ = _get(
            f"https://api.github.com/repos/{ORG}/{name}/branches/{default_branch}/protection"
        )
        branch_protected = bp_data is not None

        # Dependabot alerts
        dep_data, dep_hdrs = _get(
            f"https://api.github.com/repos/{ORG}/{name}/vulnerability-alerts"
        )
        dependabot_enabled = dep_data is True  # 204 returns True

        # Workflows
        wf_data, _ = _get(f"https://api.github.com/repos/{ORG}/{name}/actions/workflows")
        workflow_count = 0
        if isinstance(wf_data, dict):
            workflow_count = wf_data.get("total_count", 0)

        # CI runs last 30 days
        runs_success = runs_failure = runs_cancelled = 0
        if workflow_count > 0:
            runs_url = f"https://api.github.com/repos/{ORG}/{name}/actions/runs?per_page=100&created=%3E{DATE_30D}"
            runs_raw = _paginate(runs_url)
            for run in runs_raw:
                conclusion = (run.get("conclusion") or "").lower()
                if conclusion == "success":
                    runs_success += 1
                elif conclusion in ("failure", "timed_out"):
                    runs_failure += 1
                elif conclusion == "cancelled":
                    runs_cancelled += 1

        # Commit activity last 30 days (capped at 30 repos)
        commits_30d = 0
        if not r.get("archived") and commit_activity_cap < 30:
            commit_activity_cap += 1
            ca_data, _ = _get(
                f"https://api.github.com/repos/{ORG}/{name}/stats/commit_activity"
            )
            if isinstance(ca_data, list) and len(ca_data) >= 4:
                # last 4 weeks
                commits_30d = sum(w.get("total", 0) for w in ca_data[-4:])

        repos.append(
            {
                "name": name,
                "visibility": r.get("visibility", "public"),
                "archived": r.get("archived", False),
                "default_branch": default_branch,
                "pushed_at": pushed_at_str,
                "size": r.get("size", 0),
                "open_issues_count": r.get("open_issues_count", 0),
                "stargazers_count": r.get("stargazers_count", 0),
                "forks_count": r.get("forks_count", 0),
                "topics": r.get("topics", []),
                "inactive": inactive,
                "branch_protected": branch_protected,
                "dependabot_enabled": dependabot_enabled,
                "workflow_count": workflow_count,
                "runs_success": runs_success,
                "runs_failure": runs_failure,
                "runs_cancelled": runs_cancelled,
                "commits_30d": commits_30d,
            }
        )
    return repos


def collect_members(repos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    log(f"[members] listing /orgs/{ORG}/members")
    raw = _paginate(f"https://api.github.com/orgs/{ORG}/members?per_page=100")
    members = []
    repo_names = [r["name"] for r in repos if not r.get("archived")][:20]

    for m in raw:
        login = m["login"]
        log(f"  [member] {login}")

        # Role
        membership, _ = _get(f"https://api.github.com/orgs/{ORG}/memberships/{login}")
        role = "member"
        if isinstance(membership, dict):
            role = membership.get("role", "member")

        # Commits last 30 days (approximate via Link header trick)
        total_commits = 0
        for repo_name in repo_names:
            url = (
                f"https://api.github.com/repos/{ORG}/{repo_name}/commits"
                f"?author={login}&since={DATE_30D}&per_page=1"
            )
            pages = _link_last_page(url)
            total_commits += pages  # each page = 1 commit (per_page=1)

        members.append({"login": login, "role": role, "commits_30d": total_commits})

    return members


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
def score_repo(r: dict[str, Any]) -> int:
    score = 100
    if r.get("inactive"):
        score -= 30
    if not r.get("branch_protected"):
        score -= 20
    if not r.get("dependabot_enabled"):
        score -= 15
    if not r.get("topics"):
        score -= 10
    total_runs = r["runs_success"] + r["runs_failure"] + r["runs_cancelled"]
    if total_runs > 0:
        fail_rate = r["runs_failure"] / total_runs
        score -= int(fail_rate * 25)
    return max(0, min(100, score))


def compute_scores(
    org: dict[str, Any], repos: list[dict[str, Any]], members: list[dict[str, Any]]
) -> dict[str, Any]:
    total = len(repos)
    non_archived = [r for r in repos if not r.get("archived")]

    # Security
    two_fa = 20 if org.get("two_factor_requirement_enabled") else 0
    bp_pct = (
        sum(1 for r in non_archived if r["branch_protected"]) / len(non_archived) * 100
        if non_archived
        else 0
    )
    dep_pct = (
        sum(1 for r in non_archived if r["dependabot_enabled"]) / len(non_archived) * 100
        if non_archived
        else 0
    )
    security_score = int(two_fa + bp_pct / 100 * 40 + dep_pct / 100 * 40)

    # Repo Health
    inactive_ratio = sum(1 for r in repos if r.get("inactive")) / total if total else 0
    archived_ratio = sum(1 for r in repos if r.get("archived")) / total if total else 0
    no_topics = sum(1 for r in non_archived if not r.get("topics")) / len(non_archived) if non_archived else 0
    repo_health_score = int(max(0, 100 - inactive_ratio * 40 - archived_ratio * 20 - no_topics * 20))

    # CI/CD
    with_wf = sum(1 for r in non_archived if r["workflow_count"] > 0)
    wf_coverage = with_wf / len(non_archived) * 100 if non_archived else 0
    total_runs = sum(r["runs_success"] + r["runs_failure"] for r in non_archived)
    total_success = sum(r["runs_success"] for r in non_archived)
    pass_rate = total_success / total_runs * 100 if total_runs else 50
    cicd_score = int(wf_coverage * 0.5 + pass_rate * 0.5)

    # Contributions
    total_commits_30d = sum(m["commits_30d"] for m in members)
    active_contribs = sum(1 for m in members if m["commits_30d"] > 0)
    active_pct = active_contribs / len(members) * 100 if members else 0
    bus_factor_penalty = 0
    if total_commits_30d > 0 and members:
        top_commits = max(m["commits_30d"] for m in members)
        if top_commits / total_commits_30d > 0.6:
            bus_factor_penalty = 25
    contrib_score = int(max(0, active_pct - bus_factor_penalty))

    # Org Governance
    perm = org.get("default_repository_permission", "read")
    perm_score = {"none": 100, "read": 60, "write": 20, "admin": 0}.get(perm, 40)
    gov_score = int(perm_score * 0.8 + (20 if org.get("two_factor_requirement_enabled") else 0))

    # Engagement
    starred = [r for r in non_archived if r.get("stargazers_count", 0) > 0]
    star_pct = len(starred) / len(non_archived) * 100 if non_archived else 0
    avg_issues = sum(r["open_issues_count"] for r in non_archived) / len(non_archived) if non_archived else 0
    issue_score = max(0, 100 - avg_issues * 2)  # penalize high open issues
    engagement_score = int(star_pct * 0.5 + issue_score * 0.5)

    overall = int(
        security_score * 0.30
        + repo_health_score * 0.20
        + cicd_score * 0.20
        + contrib_score * 0.15
        + gov_score * 0.10
        + engagement_score * 0.05
    )

    return {
        "overall": overall,
        "security": security_score,
        "repo_health": repo_health_score,
        "cicd": cicd_score,
        "contributions": contrib_score,
        "governance": gov_score,
        "engagement": engagement_score,
        "meta": {
            "bp_pct": bp_pct,
            "dep_pct": dep_pct,
            "wf_coverage": wf_coverage,
            "pass_rate": pass_rate,
            "active_pct": active_pct,
            "bus_factor_warning": bus_factor_penalty > 0,
            "total_commits_30d": total_commits_30d,
            "inactive_count": sum(1 for r in repos if r.get("inactive")),
            "archived_count": sum(1 for r in repos if r.get("archived")),
        },
    }


def generate_findings(
    org: dict[str, Any],
    repos: list[dict[str, Any]],
    members: list[dict[str, Any]],
    scores: dict[str, Any],
) -> list[dict[str, str]]:
    findings = []
    meta = scores["meta"]

    if not org.get("two_factor_requirement_enabled"):
        findings.append(
            {
                "severity": "Critical",
                "text": "2FA is NOT enforced org-wide — any member account without 2FA is a credential theft risk.",
                "rec": "Enable 2FA requirement under Org Settings → Authentication security.",
            }
        )
    if meta["bp_pct"] < 50:
        findings.append(
            {
                "severity": "High",
                "text": f"Only {meta['bp_pct']:.0f}% of repos have branch protection on the default branch.",
                "rec": "Enable branch protection with required reviews and status checks for all active repos.",
            }
        )
    if meta["dep_pct"] < 50:
        findings.append(
            {
                "severity": "High",
                "text": f"Dependabot alerts enabled on only {meta['dep_pct']:.0f}% of repos.",
                "rec": "Enable Dependabot vulnerability alerts across the org via Security settings.",
            }
        )
    if meta["inactive_count"] > 0:
        findings.append(
            {
                "severity": "Medium",
                "text": f"{meta['inactive_count']} repos have not been pushed to in 90+ days.",
                "rec": "Archive stale repos to reduce maintenance surface and confusion.",
            }
        )
    if meta["wf_coverage"] < 60:
        findings.append(
            {
                "severity": "Medium",
                "text": f"CI/CD workflow coverage is {meta['wf_coverage']:.0f}% — many repos ship without automated checks.",
                "rec": "Add a basic CI workflow (lint + test) to all active repos.",
            }
        )
    if meta["bus_factor_warning"]:
        findings.append(
            {
                "severity": "High",
                "text": "Bus factor risk: one contributor accounts for >60% of commits in the last 30 days.",
                "rec": "Distribute ownership and add at least one more maintainer to critical repos.",
            }
        )
    if org.get("default_repository_permission") in ("write", "admin"):
        findings.append(
            {
                "severity": "High",
                "text": f"Default repository permission is '{org.get('default_repository_permission')}' — all members can write to all repos.",
                "rec": "Set default_repository_permission to 'read' or 'none' and use teams for granular access.",
            }
        )
    if meta["pass_rate"] < 70:
        findings.append(
            {
                "severity": "Medium",
                "text": f"30-day CI pass rate is {meta['pass_rate']:.0f}% — build stability is low.",
                "rec": "Investigate flaky tests and failing workflows; add retry logic where appropriate.",
            }
        )
    if meta["active_pct"] < 30:
        findings.append(
            {
                "severity": "Low",
                "text": f"Only {meta['active_pct']:.0f}% of members made commits in the last 30 days.",
                "rec": "Review membership list and offboard inactive contributors to reduce attack surface.",
            }
        )
    return findings


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------
CSS = """
:root {
  --bg: oklch(15% 0.02 240);
  --surface: oklch(20% 0.02 240);
  --surface2: oklch(25% 0.02 240);
  --accent: oklch(70% 0.15 200);
  --green: oklch(65% 0.18 145);
  --amber: oklch(75% 0.18 85);
  --red: oklch(60% 0.2 25);
  --text: oklch(90% 0.01 240);
  --muted: oklch(60% 0.02 240);
  --border: oklch(30% 0.02 240);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); color: var(--text); font-family: system-ui, sans-serif; font-size: 14px; line-height: 1.5; }
a { color: var(--accent); }
h1, h2, h3 { font-weight: 600; }
header { background: var(--surface); border-bottom: 1px solid var(--border); padding: 2rem; display: flex; align-items: center; gap: 2rem; flex-wrap: wrap; }
.ring-wrap { position: relative; width: 120px; height: 120px; flex-shrink: 0; }
.ring-wrap svg { transform: rotate(-90deg); }
.ring-label { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; font-size: 1.6rem; font-weight: 700; }
.ring-label small { font-size: 0.65rem; color: var(--muted); font-weight: 400; margin-top: 2px; }
.header-text h1 { font-size: 1.5rem; }
.header-text p { color: var(--muted); font-size: 0.85rem; margin-top: 0.25rem; }
main { max-width: 1400px; margin: 0 auto; padding: 1.5rem; }
section { margin-bottom: 2rem; }
section > h2 { font-size: 1rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 1rem; }
.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem; }
.card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1.25rem; }
.card-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.75rem; }
.card-title { font-weight: 600; }
.badge { display: inline-block; padding: 0.2em 0.6em; border-radius: 4px; font-size: 0.8rem; font-weight: 600; }
.badge-green { background: color-mix(in oklch, var(--green) 20%, transparent); color: var(--green); }
.badge-amber { background: color-mix(in oklch, var(--amber) 20%, transparent); color: var(--amber); }
.badge-red { background: color-mix(in oklch, var(--red) 20%, transparent); color: var(--red); }
.card ul { list-style: none; margin: 0.5rem 0; }
.card ul li { color: var(--muted); font-size: 0.85rem; padding: 0.15rem 0; }
.card ul li::before { content: "• "; }
.rec { background: var(--surface2); border-radius: 4px; padding: 0.5rem 0.75rem; font-size: 0.82rem; margin-top: 0.75rem; color: var(--text); border-left: 3px solid var(--accent); }
table { width: 100%; border-collapse: collapse; font-size: 0.83rem; }
th { background: var(--surface2); color: var(--muted); font-weight: 600; text-align: left; padding: 0.6rem 0.75rem; cursor: pointer; user-select: none; white-space: nowrap; }
th:hover { color: var(--text); }
td { padding: 0.55rem 0.75rem; border-top: 1px solid var(--border); }
tr.row-red td { background: color-mix(in oklch, var(--red) 8%, transparent); }
tr.row-amber td { background: color-mix(in oklch, var(--amber) 6%, transparent); }
tr.row-green td { background: color-mix(in oklch, var(--green) 5%, transparent); }
.table-wrap { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; overflow-x: auto; }
.findings-list { list-style: none; }
.findings-list li { background: var(--surface); border: 1px solid var(--border); border-radius: 6px; padding: 0.75rem 1rem; margin-bottom: 0.5rem; display: flex; gap: 0.75rem; align-items: flex-start; }
.sev { font-weight: 600; font-size: 0.75rem; padding: 0.15em 0.5em; border-radius: 3px; white-space: nowrap; margin-top: 2px; }
.sev-Critical { background: color-mix(in oklch, var(--red) 25%, transparent); color: var(--red); }
.sev-High { background: color-mix(in oklch, var(--amber) 20%, transparent); color: var(--amber); }
.sev-Medium { background: color-mix(in oklch, var(--accent) 20%, transparent); color: var(--accent); }
.sev-Low { background: color-mix(in oklch, var(--muted) 20%, transparent); color: var(--muted); }
.finding-body p { color: var(--text); }
.finding-body small { color: var(--muted); font-style: italic; }
footer { text-align: center; padding: 2rem; color: var(--muted); font-size: 0.8rem; border-top: 1px solid var(--border); }
.bool-yes { color: var(--green); }
.bool-no { color: var(--red); }
"""

JS = """
function sortTable(tableId, col) {
  const tbl = document.getElementById(tableId);
  const tbody = tbl.querySelector('tbody');
  const rows = Array.from(tbody.querySelectorAll('tr'));
  const th = tbl.querySelectorAll('th')[col];
  const asc = th.dataset.sort !== 'asc';
  tbl.querySelectorAll('th').forEach(h => delete h.dataset.sort);
  th.dataset.sort = asc ? 'asc' : 'desc';
  rows.sort((a, b) => {
    const va = a.cells[col]?.dataset.val ?? a.cells[col]?.textContent ?? '';
    const vb = b.cells[col]?.dataset.val ?? b.cells[col]?.textContent ?? '';
    const na = parseFloat(va), nb = parseFloat(vb);
    if (!isNaN(na) && !isNaN(nb)) return asc ? na - nb : nb - na;
    return asc ? va.localeCompare(vb) : vb.localeCompare(va);
  });
  rows.forEach(r => tbody.appendChild(r));
}
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('table[id]').forEach(tbl => {
    tbl.querySelectorAll('th').forEach((th, i) => {
      th.addEventListener('click', () => sortTable(tbl.id, i));
    });
  });
});
"""


def _score_color(s: int) -> str:
    if s >= 80:
        return "green"
    if s >= 50:
        return "amber"
    return "red"


def _score_emoji(s: int) -> str:
    if s >= 80:
        return "🟢"
    if s >= 50:
        return "🟡"
    return "🔴"


def _bool_cell(v: bool) -> str:
    if v:
        return '<span class="bool-yes">✓</span>'
    return '<span class="bool-no">✗</span>'


def _ring_svg(score: int) -> str:
    r = 52
    circ = 2 * 3.14159 * r
    fill = circ * score / 100
    color = {"green": "var(--green)", "amber": "var(--amber)", "red": "var(--red)"}[
        _score_color(score)
    ]
    return f"""
<div class="ring-wrap">
  <svg width="120" height="120" viewBox="0 0 120 120">
    <circle cx="60" cy="60" r="{r}" fill="none" stroke="var(--border)" stroke-width="10"/>
    <circle cx="60" cy="60" r="{r}" fill="none" stroke="{color}" stroke-width="10"
      stroke-dasharray="{fill:.1f} {circ:.1f}" stroke-linecap="round"/>
  </svg>
  <div class="ring-label">{score}<small>/ 100</small></div>
</div>"""


def _section_card(
    title: str, score: int, bullets: list[str], rec: str
) -> str:
    c = _score_color(score)
    emoji = _score_emoji(score)
    bullets_html = "".join(f"<li>{b}</li>" for b in bullets)
    return f"""
<div class="card">
  <div class="card-header">
    <span class="card-title">{emoji} {title}</span>
    <span class="badge badge-{c}">{score}</span>
  </div>
  <ul>{bullets_html}</ul>
  <div class="rec">{rec}</div>
</div>"""


def _repo_row(r: dict[str, Any]) -> str:
    s = score_repo(r)
    row_class = "row-green" if s > 70 else ("row-amber" if s >= 40 else "row-red")
    pushed = r["pushed_at"][:10] if r["pushed_at"] else "—"
    topics = ", ".join(r["topics"]) if r["topics"] else "—"
    name_cell = f'<a href="https://github.com/{ORG}/{r["name"]}" target="_blank">{r["name"]}</a>'
    return (
        f'<tr class="{row_class}">'
        f"<td>{name_cell}</td>"
        f'<td>{r["visibility"]}</td>'
        f'<td data-val="{int(r["branch_protected"])}">{_bool_cell(r["branch_protected"])}</td>'
        f'<td data-val="{int(r["dependabot_enabled"])}">{_bool_cell(r["dependabot_enabled"])}</td>'
        f'<td data-val="{r["workflow_count"]}">{r["workflow_count"]}</td>'
        f'<td data-val="{r["pushed_at"]}">{pushed}{"⚠" if r["inactive"] else ""}</td>'
        f'<td data-val="{r["commits_30d"]}">{r["commits_30d"]}</td>'
        f'<td data-val="{r["open_issues_count"]}">{r["open_issues_count"]}</td>'
        f'<td data-val="{s}"><span class="badge badge-{_score_color(s)}">{s}</span></td>'
        "</tr>"
    )


def _member_row(m: dict[str, Any], total_commits: int) -> str:
    pct = (m["commits_30d"] / total_commits * 100) if total_commits else 0
    bus = " 🚨" if pct > 60 else ""
    return (
        f"<tr>"
        f'<td><a href="https://github.com/{m["login"]}" target="_blank">{m["login"]}</a></td>'
        f'<td>{m["role"]}</td>'
        f'<td data-val="{m["commits_30d"]}">{m["commits_30d"]}</td>'
        f'<td data-val="{pct:.1f}">{pct:.1f}%{bus}</td>'
        "</tr>"
    )


def build_html(
    org: dict[str, Any],
    repos: list[dict[str, Any]],
    members: list[dict[str, Any]],
    scores: dict[str, Any],
    findings: list[dict[str, str]],
) -> str:
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    meta = scores["meta"]
    total_commits = meta["total_commits_30d"]

    # Section cards
    sec_security = _section_card(
        "Security",
        scores["security"],
        [
            f"2FA enforcement: {'✓ enabled' if org.get('two_factor_requirement_enabled') else '✗ disabled'}",
            f"Branch protection: {meta['bp_pct']:.0f}% of repos",
            f"Dependabot alerts: {meta['dep_pct']:.0f}% of repos",
        ],
        "Enable 2FA org-wide, add branch protection rules, and turn on Dependabot for all repos.",
    )
    non_archived_count = sum(1 for r in repos if not r.get("archived"))
    sec_repo = _section_card(
        "Repo Health",
        scores["repo_health"],
        [
            f"Total repos: {len(repos)} ({non_archived_count} active, {meta['archived_count']} archived)",
            f"Inactive (>90d no push): {meta['inactive_count']}",
            f"Repos missing topics: {sum(1 for r in repos if not r.get('archived') and not r.get('topics'))}",
        ],
        "Archive stale repos, add topics to all active repos, and review the inactive list quarterly.",
    )
    sec_cicd = _section_card(
        "CI/CD",
        scores["cicd"],
        [
            f"Workflow coverage: {meta['wf_coverage']:.0f}% of active repos",
            f"30-day CI pass rate: {meta['pass_rate']:.0f}%",
            f"Total runs (30d): {sum(r['runs_success'] + r['runs_failure'] + r['runs_cancelled'] for r in repos)}",
        ],
        "Add CI workflows to all active repos and investigate chronic failures to improve pass rate.",
    )
    sec_contrib = _section_card(
        "Contributions",
        scores["contributions"],
        [
            f"Active contributors (30d): {meta['active_pct']:.0f}% of members",
            f"Total commits (30d, sampled): {total_commits}",
            f"Bus factor risk: {'YES 🚨' if meta['bus_factor_warning'] else 'No'}",
        ],
        "Distribute commit ownership and onboard co-maintainers to critical repos.",
    )
    sec_gov = _section_card(
        "Org Governance",
        scores["governance"],
        [
            f"Default repo permission: {org.get('default_repository_permission', 'unknown')}",
            f"Members can create public repos: {org.get('members_can_create_public_repositories', True)}",
            f"Plan: {org.get('plan_name', '—')} ({org.get('seats_used', 0)}/{org.get('seats_total', 0)} seats)",
        ],
        "Set default permission to 'none', use teams, and restrict public repo creation to admins.",
    )
    sec_engage = _section_card(
        "Engagement",
        scores["engagement"],
        [
            f"Repos with stars: {sum(1 for r in repos if r.get('stargazers_count', 0) > 0)}",
            f"Public repos: {org.get('public_repos', 0)}",
            f"Avg open issues per repo: {sum(r['open_issues_count'] for r in repos) / len(repos) if repos else 0:.1f}",
        ],
        "Improve docs and add topics/descriptions to boost discoverability and star count.",
    )

    repo_rows = "".join(_repo_row(r) for r in repos)
    member_rows = "".join(_member_row(m, total_commits) for m in members)

    findings_html = ""
    for f in findings:
        findings_html += f"""
<li>
  <span class="sev sev-{f['severity']}">{f['severity']}</span>
  <div class="finding-body">
    <p>{f['text']}</p>
    <small>Rec: {f['rec']}</small>
  </div>
</li>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{ORG} — Org 360° Audit</title>
<style>{CSS}</style>
</head>
<body>
<header>
  {_ring_svg(scores['overall'])}
  <div class="header-text">
    <h1>{ORG} — Org 360° Audit</h1>
    <p>Generated {now_str} &nbsp;·&nbsp; {len(repos)} repos &nbsp;·&nbsp; {len(members)} members</p>
    <p style="margin-top:0.5rem;font-size:0.8rem;color:var(--muted)">Overall score: <strong style="color:var(--text)">{scores['overall']} / 100</strong></p>
  </div>
</header>
<main>
  <section>
    <h2>Section Scores</h2>
    <div class="cards">
      {sec_security}
      {sec_repo}
      {sec_cicd}
      {sec_contrib}
      {sec_gov}
      {sec_engage}
    </div>
  </section>

  <section>
    <h2>Repositories ({len(repos)})</h2>
    <div class="table-wrap">
      <table id="repo-table">
        <thead>
          <tr>
            <th>Name</th><th>Visibility</th><th>Branch Protected</th>
            <th>Dependabot</th><th>Workflows</th><th>Last Push</th>
            <th>30d Commits</th><th>Open Issues</th><th>Score</th>
          </tr>
        </thead>
        <tbody>{repo_rows}</tbody>
      </table>
    </div>
  </section>

  <section>
    <h2>Members ({len(members)})</h2>
    {"<p style='color:var(--amber);margin-bottom:0.75rem'>⚠ Bus factor risk: one contributor accounts for &gt;60% of recent commits.</p>" if meta['bus_factor_warning'] else ""}
    <div class="table-wrap">
      <table id="member-table">
        <thead>
          <tr><th>Login</th><th>Role</th><th>30d Commits</th><th>Contribution %</th></tr>
        </thead>
        <tbody>{member_rows}</tbody>
      </table>
    </div>
  </section>

  <section>
    <h2>Findings &amp; Recommendations ({len(findings)})</h2>
    <ul class="findings-list">{findings_html}</ul>
  </section>
</main>
<footer>
  Generated {now_str} &nbsp;·&nbsp; Run weekly via GitHub Actions &nbsp;·&nbsp; Org 360° Audit
</footer>
<script>{JS}</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    if not TOKEN:
        log("ERROR: GH_TOKEN env var is required.")
        sys.exit(1)

    log(f"=== Org 360° Audit: {ORG} ===")

    org = collect_org()
    log(f"[org] plan={org.get('plan_name')} repos={org.get('public_repos')}+{org.get('private_repos')}")

    repos = collect_repos()
    log(f"[repos] collected {len(repos)} repos")

    members = collect_members(repos)
    log(f"[members] collected {len(members)} members")

    scores = compute_scores(org, repos, members)
    log(f"[scores] overall={scores['overall']}")

    findings = generate_findings(org, repos, members, scores)
    log(f"[findings] {len(findings)} findings")

    html = build_html(org, repos, members, scores, findings)
    with open(OUTPUT, "w", encoding="utf-8") as fh:
        fh.write(html)

    size_kb = len(html.encode("utf-8")) / 1024
    log(f"[done] {OUTPUT} written ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
