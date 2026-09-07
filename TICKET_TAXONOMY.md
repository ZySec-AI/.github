# Ticket Taxonomy — ZySec AI

> [!IMPORTANT]
> **Parts of this document are out of date as of 2026-09-07.**
>
> The org moved from 141 ad-hoc labels to a 42-label enforced taxonomy
> ([`labels.yml`](labels.yml)). The `type:*`, `priority:*`, `status:*`,
> `severity:*` and `dimension:*` labels this document describes **no longer
> exist** — they were deleted from every repository.
>
> They were not replaced by other labels. They became native GitHub fields:
>
> | This document says | Now use |
> |---|---|
> | `type:bug`, `type:feature`, `type:task`, `type:epic` | **Issue Type** — Bug / Feature / Task / Epic |
> | `type:chore`, `type:docs`, `type:infra`, `type:test`, `type:spec`, `type:tech-debt` | **Issue Type: Task** |
> | `priority:p0`–`p3` | **Issue Priority** field (P0–P3) |
> | `severity:*` | **Issue Severity** field |
> | `status:*` | **Status** on the Engineering Delivery board |
> | `dimension:*` | `area:*` on the manifest |
>
> The workflow guidance below — templates, milestones, branch and ticket
> conventions — still holds. Only the label names are wrong. This document needs
> a proper pass; treat `labels.yml` as authoritative where the two disagree.

> **Self-contained rule:** Every issue must be independently actionable. A developer or coding agent should be able to pick up any issue without reading the parent thread first. Include all context the implementer needs inside the issue body.

---

## 1. Issue Types

Three templates cover all work. Each maps to one or more `type:*` labels.

| Template | `type:*` label | When to use |
|----------|---------------|-------------|
| **Work** | `type:feature`, `type:task`, `type:spec`, `type:chore`, `type:tech-debt`, `type:docs`, `type:infra`, `type:test` | Any new work that isn't a bug |
| **Bug** | `type:bug` | Something is broken, regressed, or behaves unexpectedly |
| **Epic** | `type:epic` | Cross-cutting initiative spanning multiple repos or milestones |

### Type details

| Label | Use for | Example |
|-------|---------|---------|
| `type:epic` | Parent tracking across repos | "Auth alignment — RS256 migration" |
| `type:feature` | New user-facing functionality | "Add OAuth 2.0 authorization_code flow" |
| `type:bug` | Defect or regression | "SSE stream disconnects after second agent" |
| `type:task` | General implementation work | "Implement ClientOps domain CRUD" |
| `type:spec` | Design spec, architecture, validation plan | "App manifest spec for Work Hub" |
| `type:chore` | Maintenance, tooling, dep updates | "Bump FastAPI to 0.135" |
| `type:tech-debt` | Refactor, cleanup, migration | "Migrate HS256 to RS256 across services" |
| `type:docs` | Documentation only | "Update API reference for chat endpoints" |
| `type:infra` | CI, deployment, Kubernetes | "Add HPA for cpod-backend" |
| `type:test` | Tests only, no production changes | "Add integration tests for memory module" |

---

## 2. Label Taxonomy

### Required labels per issue

Every issue must have:
- **One** `type:*` label
- **One** `status:*` label (default: `status:planned`)
- **One** `priority:*` label

Bugs additionally need:
- **One** `severity:*` label

### Type labels (pick one)

| Label | Color | Description |
|-------|-------|-------------|
| `type:epic` | `#5319E7` | Cross-cutting initiative |
| `type:feature` | `#A2EEEF` | New functionality |
| `type:bug` | `#D73A4A` | Defect or regression |
| `type:task` | `#1D76DB` | Implementation work |
| `type:spec` | `#5319E7` | Design spec or plan |
| `type:chore` | `#EDEDED` | Maintenance / tooling |
| `type:tech-debt` | `#FBCA04` | Refactor / cleanup |
| `type:docs` | `#0075CA` | Documentation |
| `type:infra` | `#5319E7` | CI / deployment |
| `type:test` | `#0052CC` | Tests only |

### Status labels (pick one)

| Label | Color | Meaning |
|-------|-------|---------|
| `status:planned` | `#C2E0C6` | Not started |
| `status:ready` | `#0E8A16` | Specs complete, ready to implement |
| `status:in-progress` | `#FBCA04` | Active implementation |
| `status:blocked` | `#E11D21` | Waiting on dependency or decision |
| `status:done` | `#0E8A16` | Completed and validated |
| `status:superseded` | `#BFDADC` | Replaced by another issue |

### Priority labels (pick one)

| Label | Color | Meaning |
|-------|-------|---------|
| `priority:p0-critical` | `#B60205` | Blocker — must ship now |
| `priority:p1-high` | `#D93F0B` | Important — current sprint |
| `priority:p2-normal` | `#FBCA04` | Normal priority |
| `priority:p3-low` | `#0E8A16` | Nice to have |

### Severity labels (for bugs and audit findings)

| Label | Color | Meaning |
|-------|-------|---------|
| `severity:critical` | `#B60205` | Fix immediately — production impact |
| `severity:high` | `#D93F0B` | Fix soon — significant impact |
| `severity:medium` | `#FBCA04` | Fix when possible — moderate impact |
| `severity:low` | `#C2E0C6` | Fix eventually — minor impact |

### Dimension labels (for review/audit findings)

| Label | Color | Meaning |
|-------|-------|---------|
| `dimension:security` | `#EE0701` | OWASP, CVE, secrets |
| `dimension:quality` | `#5319E7` | Dead code, complexity, conventions |
| `dimension:deps` | `#0366D6` | Outdated or vulnerable dependencies |
| `dimension:perf` | `#F9D0C4` | Performance |
| `dimension:ui` | `#E99695` | UI / accessibility |

### Automation labels (workflow-managed)

| Label | Color | Purpose |
|-------|-------|---------|
| `bot-reviewed` | `#6F42C1` | Triage bot classified |
| `bot-skip` | `#EDEDED` | Skip triage processing |
| `auto-fixable` | `#0E8A16` | Bot assessed as auto-fixable |
| `needs-info` | `#FBCA04` | Needs more context |
| `good-first-issue` | `#7057FF` | Good for newcomers |

### Simulation labels (from `/simulate` cycles)

| Label | Color | Purpose |
|-------|-------|---------|
| `sim` | `#E4E669` | Found by simulation |
| `carry` | `#FF6B35` | Bug surviving 2+ cycles |
| `highlight` | `#0E8A16` | Positive product signal |

### Area labels (per-repo)

Each repo adds its own `area:*` labels for domain-specific categorization. Follow these naming rules:

- Use `area:` prefix with colon separator
- Lowercase, hyphenated: `area:auth`, `area:tenants`, `area:edm`
- Keep under 20 area labels per repo — merge related concerns

**Common area labels across repos:**

| Repo | Example area labels |
|------|-------------------|
| core-sdk | `area:jwt`, `area:oauth`, `area:policy`, `area:audit`, `area:saml` |
| cpod-backend | `area:auth`, `area:skills`, `area:workflows`, `area:chat`, `area:agents`, `area:memory` |
| cpod-ui | `area:user-portal`, `area:tenant-portal`, `area:global-portal`, `area:design-system` |
| cpod-sdk | `area:typescript-sdk`, `area:python-sdk`, `area:contracts`, `area:edm` |
| coreiq | `area:proxy`, `area:scanning`, `area:governance`, `area:cost` |
| cpod-arai | `area:ingestion`, `area:retrieval`, `area:entities`, `area:graph` |
| app-store | `area:catalog`, `area:features`, `area:permissions`, `area:mcp`, `area:runtime` |
| deployments | `area:helm`, `area:nginx`, `area:monitoring`, `area:migration` |

---

## 3. Required Fields Per Issue Type

### Work (feature / task / spec / chore / tech-debt / docs / infra / test)

| Field | Required | Description |
|-------|----------|-------------|
| Work type | Yes | Dropdown: feature, task, spec, chore, tech-debt, docs, infra, test |
| Target repo | Yes | Which repo owns this work |
| Priority | Yes | p0 through p3 |
| Summary | Yes | What and why — one paragraph |
| Validation | Yes | Commands to run + acceptance criteria |
| Parent issue | If applicable | Link to epic or parent issue |
| Module | Recommended | Logical component name |
| Due date | If bounded | Target date (YYYY-MM-DD) |
| Owner | If assigned | GitHub handle |
| Code paths | Recommended | Files/dirs expected to change |
| Context | If applicable | SDK/EDM impact, permissions, shared refs |
| Dependencies | If applicable | Cross-repo blockers, prerequisite issues |
| Non-goals | Recommended | Explicit scope boundaries |

### Bug

| Field | Required | Description |
|-------|----------|-------------|
| Affected repo | Yes | Which repo has the bug |
| Severity | Yes | critical / high / medium / low |
| Priority | Yes | p0 through p3 |
| Summary | Yes | What is broken |
| Steps to reproduce | Yes | Exact steps to trigger |
| Expected behavior | Yes | What should happen |
| Actual behavior | Yes | What actually happens |
| Validation | Recommended | How to verify the fix |
| Parent issue | If applicable | Link to parent |
| Module | Recommended | Logical component |
| Suspected code paths | Recommended | Files likely involved |
| Environment | Recommended | OS, runtime, deployment mode |
| Dependencies | If applicable | Related cross-repo issues |

### Epic

| Field | Required | Description |
|-------|----------|-------------|
| Owner | Yes | GitHub handle |
| Priority | Yes | p0 through p3 |
| Summary | Yes | What the epic delivers and why |
| Scope | Yes | Repos and modules affected |
| Child issues | Yes | Checklist of all sub-issues |
| Target date | If bounded | Target completion |
| Dependency graph | Recommended | Sequencing of child issues |
| Success criteria | Recommended | What must be true at completion |
| Non-goals | Recommended | Explicit exclusions |

---

## 4. Issue Body Structure

### Self-contained rule

Every issue body must include enough context for a developer or agent to implement it without reading any other issue. Parent links are for traceability — they are NOT required reading.

If a parent issue defines a product contract, each child issue must **repeat the relevant parts** of that contract in its own body.

### Standard sections (all types)

```markdown
## Metadata

| Field | Value |
|-------|-------|
| Parent | #N or org/repo#N |
| Repo | repo-name |
| Module | module/path |
| Priority | p0-critical / p1-high / p2-normal / p3-low |
| Due date | YYYY-MM-DD or blank |
| Owner | @handle or blank |

## Summary

One paragraph: what and why.

## Code Paths

| Path | Purpose | Expected change |
|------|---------|-----------------|
| `app/auth/middleware.py` | JWT validation | Add RS256 support |

## Context

**Shared references** — design system, SDK docs, portal links

**SDK / EDM impact** (if applicable)
| Domain | Read/Write | Purpose |
|--------|-----------|---------|

**Permissions** (if applicable)
| Permission | Reason |
|------------|--------|

## Dependencies

- [ ] org/repo#N — description
- [ ] #N — description

## Validation

**Commands**
```bash
# exact commands to run
```

**Acceptance criteria**
- [ ] Criterion 1
- [ ] Criterion 2

## Non-Goals

- What this issue does NOT cover
```

---

## 5. Cross-Repo Dependencies

### Convention

Use GitHub sub-issues for parent/child relationships within the same repo. For cross-repo dependencies:

1. **In the issue body:** List under `## Dependencies` using `org/repo#N` format
2. **In comments:** Link with full URL when referencing from another repo
3. **On blocking:** Add `status:blocked` label and describe what's needed in the Dependencies section

### Example

```markdown
## Dependencies

- [ ] ZySec-AI/core-sdk#151 — RS256 signing support (blocks this issue)
- [ ] ZySec-AI/cpod-backend#200 — Auth middleware refactor (parallel, no block)
- [ ] #305 — Local prerequisite (must complete first)
```

### Blocked issue format

When an issue is blocked, the Dependencies section must explain:
- What is needed from the dependency
- Why this issue can't proceed without it
- Whether there's a workaround

---

## 6. Due Dates and Milestones

### Due date convention

- Use the `Due date` field in the metadata table
- Format: `YYYY-MM-DD`
- Only set due dates for `p0-critical` and `p1-high` issues
- For epics, set a target date for the full initiative

### Milestone alignment

- GitHub milestones are per-repo — use them for sprint/release tracking
- Epics may span milestones across repos — track in the epic body's child issue checklist
- When an issue has both a due date and a milestone, the due date takes precedence for urgency

---

## 7. Per-Repo Migration Guide

Each repo needs to align its existing labels to this taxonomy. Below is the mapping for each repo.

### core-sdk

| Old label | New label |
|-----------|-----------|
| `bug` | `type:bug` |
| `enhancement` | `type:feature` |
| `type:bug` | `type:bug` (keep) |
| `type:feature` | `type:feature` (keep) |
| `type:chore` | `type:chore` (keep) |
| `type:docs` | `type:docs` (keep) |
| `critical` | `priority:p0-critical` |
| `high` | `priority:p1-high` |
| `medium` | `priority:p2-normal` |
| `low` | `priority:p3-low` |
| `severity:high` | `severity:high` (keep) |
| `epic` | `type:epic` |
| `arch` | `type:tech-debt` or `type:spec` |

### cpod-backend

| Old label | New label |
|-----------|-----------|
| `type/bug` | `type:bug` |
| `type/feature` | `type:feature` |
| `type/chore` | `type:chore` |
| `type/docs` | `type:docs` |
| `type/infra` | `type:infra` |
| `type/security` | `dimension:security` |
| `priority/p0-critical` | `priority:p0-critical` |
| `priority/p1-high` | `priority:p1-high` |
| `priority/p2-normal` | `priority:p2-normal` |
| `priority/p3-low` | `priority:p3-low` |
| `status/blocked` | `status:blocked` |
| `status/in-progress` | `status:in-progress` |
| `status/ready` | `status:ready` |
| `status/needs-design` | `status:planned` (add `needs-info`) |
| `status/future` | `status:planned` |
| `epic` | `type:epic` |
| `severity/*` | `severity:*` (colon separator) |
| `dimension/*` | `dimension:*` (colon separator) |
| `area/*` | `area:*` (colon separator) |

### cpod-ui

| Old label | New label |
|-----------|-----------|
| `type:feature` | `type:feature` (keep) |
| `type:bug` | `type:bug` (keep) |
| `type:chore` | `type:chore` (keep) |
| `type:docs` | `type:docs` (keep) |
| `type:refactor` | `type:tech-debt` |
| `type:perf` | `type:task` + `dimension:perf` |
| `type:test` | `type:test` (keep) |
| `priority/p0-critical` | `priority:p0-critical` |
| `priority/p1-high` | `priority:p1-high` |
| `priority/p2-normal` | `priority:p2-normal` |
| `critical` / `high` / `medium` / `low` | `severity:*` or `priority:*` |
| `user-portal` | `area:user-portal` |

### cpod-sdk

| Old label | New label |
|-----------|-----------|
| `type:feature` | `type:feature` (keep) |
| `type:bug` | `type:bug` (keep) |
| `type:docs` | `type:docs` (keep) |
| `type:question` | (use GitHub Discussions instead) |
| `chore` | `type:chore` |
| `priority:p0` | `priority:p0-critical` |
| `priority:p1` | `priority:p1-high` |
| `priority:p2` | `priority:p2-normal` |
| `area:*` | `area:*` (keep) |
| `dimension:*` | `dimension:*` (keep) |
| `severity:*` | `severity:*` (keep) |

### coreiq

| Old label | New label |
|-----------|-----------|
| `type:feature` | `type:feature` (keep) |
| `type:chore` | `type:chore` (keep) |
| `critical` / `high` / `medium` / `low` | `priority:*` or `severity:*` |
| `arch` | `type:tech-debt` or `type:spec` |
| `feature` | `type:feature` |

### cpod-arai

| Old label | New label |
|-----------|-----------|
| `bug` | `type:bug` |
| `enhancement` | `type:feature` |
| `arch` | `type:tech-debt` or `type:spec` |
| `critical` / `high` / `medium` / `low` | `priority:*` or `severity:*` |
| `refactor` | `type:tech-debt` |
| `stale` | (close or update status) |

### app-store

Already aligned. Minor renames:
| Old label | New label |
|-----------|-----------|
| `type:sdk-dependency` | `type:task` + `status:blocked` (or keep as custom type) |
| `type:app` | `type:spec` (app spec issues) |
| `type:system` | `type:spec` (system spec issues) |
| `level:*` | (keep as custom labels — app-store specific) |
| `phase:*` | (keep — project-specific) |
| `app:*` | (keep — app-store specific) |

### deployments

| Old label | New label |
|-----------|-----------|
| `bug` | `type:bug` |
| `documentation` | `type:docs` |
| `enhancement` | `type:feature` |
| (all defaults) | Apply full taxonomy |

---

## 8. Quick Reference for Agents

When creating or triaging issues programmatically:

```yaml
# Minimum required labels
labels:
  - type:<one of: epic|feature|bug|task|spec|chore|tech-debt|docs|infra|test>
  - status:<one of: planned|ready|in-progress|blocked|done|superseded>
  - priority:<one of: p0-critical|p1-high|p2-normal|p3-low>

# For bugs, add severity
  - severity:<one of: critical|high|medium|low>

# For review/audit findings, add dimension
  - dimension:<one of: security|quality|deps|perf|ui>
```

**Metadata table (minimum):**

```markdown
| Field | Value |
|-------|-------|
| Repo | <repo-name> |
| Priority | p0-critical / p1-high / p2-normal / p3-low |
```

**Validation section (minimum):**

```markdown
## Validation

- [ ] Acceptance criterion 1
- [ ] Acceptance criterion 2
```

**Dependencies (cross-repo):**

```markdown
## Dependencies

- [ ] ZySec-AI/<repo>#<N> — <description>
```
