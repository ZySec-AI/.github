# Org Maintainer Guide — ZySec-AI

This document is for **org owners and admins** managing the ZySec-AI GitHub organisation. End users / contributors don't need this.

---

## Architecture

ZySec-AI uses a fully **team-based, ruleset-enforced** access model. No direct user grants on repos. All policy lives at the org level.

### Org-level rulesets

| Name | Target | Purpose |
|---|---|---|
| `secure-merge` | default branch | PR + 1 reviewer required |
| `org-no-main-branch` | `main`, `master` | Blocks creation org-wide |
| `org-develop-protected` | `develop` | No delete / force-push / non-linear |
| `org-release-only-from-develop` | `release/**` | Versioned name, signed commits, PR with linear history |
| `org-stage-protected` | `stage` | Optional staging branch, PR-only |
| `org-version-tags-locked` | `v*` tags | Semver pattern, no delete/update |
| `org-branch-naming-convention` | feature branches | Conventional Commits prefix |
| `enforce-lowercase-names` | repo names | All-lowercase enforced |

All rulesets bypass: `RepositoryRole=5` (Repository Admin).

### Branch model

```
feature/* → develop → stage → release → tag (v*)
                ↑
            hotfix/* → release  (urgent path)
```

### Standard teams

| Team | Org role | Per-repo permission | Purpose |
|---|---|---|---|
| `admins` | — | `admin` × all repos | Full control |
| `maintenance-team` | — | `maintain` × all repos | Tooling, deps, CI fixes |
| `security-team` | **Security Manager** | `triage` × all repos | Vulnerability triage, advisories |
| `backend-core` | — | per-repo | Backend domain |
| `fullstack-team` | — | per-repo | Fullstack domain |
| `data-engineering` | — | per-repo | Data domain |
| `operations` | — | per-repo | Ops domain |
| `other-users` | — | per-repo | Tracking individuals not yet domain-assigned |

### Org-wide settings

- `members_can_create_repositories: false` — only admins create repos
- `default_repository_branch: develop`
- `default_repository_permission: none`
- `members_can_create_pages: false`
- `members_can_fork_private_repositories: false`

---

## New repo bootstrap workflow

Every new repo created in ZySec-AI is bootstrapped by `.github/workflows/new-repo-bootstrap.yml`. It:

1. Grants `admins` team `admin`
2. Grants `maintenance-team` team `maintain`
3. Grants `security-team` team `triage`
4. Sets repo settings (squash-only, delete-on-merge, no wiki, web sign-off)
5. Ensures default branch is `develop`

### ⚠️ Required: `ORG_BOOTSTRAP_TOKEN` secret

The bootstrap workflow needs an org secret to call the GitHub API.

#### How to create the token

1. Go to https://github.com/settings/personal-access-tokens/new (use a service account if you have one — `zysec-bot` recommended)
2. **Token name:** `ZySec-AI Org Bootstrap`
3. **Expiration:** 1 year (set a calendar reminder to rotate)
4. **Resource owner:** `ZySec-AI`
5. **Repository access:** All repositories (or just `.github` if you prefer minimum scope)
6. **Repository permissions:**
   - Administration: **Read and write**
   - Metadata: **Read-only** (auto)
7. **Organization permissions:**
   - Administration: **Read and write**
   - Members: **Read and write**
8. Click **Generate token**, copy the value

#### How to install the secret

1. Go to https://github.com/organizations/ZySec-AI/settings/secrets/actions
2. Click **New organization secret**
3. **Name:** `ORG_BOOTSTRAP_TOKEN`
4. **Secret:** paste the token from above
5. **Repository access:** **Selected repositories** → choose only `.github`
6. **Add secret**

#### Verifying it works

Create a tiny test repo:

```bash
gh repo create ZySec-AI/bootstrap-test --private --add-readme --confirm
```

Within ~30 seconds, the workflow runs. Check:

```bash
gh run list --repo ZySec-AI/.github --workflow new-repo-bootstrap.yml --limit 1
gh api /repos/ZySec-AI/bootstrap-test/teams --jq '.[] | "\(.slug): \(.permission)"'
```

You should see `admins:admin`, `maintenance-team:maintain`, `security-team:triage`. Then delete the test repo.

#### Token rotation

Set a calendar reminder for ~11 months out:
- Generate a new fine-grained PAT with the same scopes
- Update the `ORG_BOOTSTRAP_TOKEN` org secret
- Revoke the old PAT

---

## Common operations

### Add a user to a team

```bash
gh api -X PUT /orgs/ZySec-AI/teams/<team-slug>/memberships/<username> -f role=member
gh api -X PUT /orgs/ZySec-AI/teams/<team-slug>/memberships/<username> -f role=maintainer  # team lead
```

### Move a user from `other-users` to a domain team

```bash
gh api -X DELETE /orgs/ZySec-AI/teams/other-users/memberships/<username>
gh api -X PUT /orgs/ZySec-AI/teams/<domain-team>/memberships/<username> -f role=member
```

### Audit direct user grants (should always be empty)

```bash
for repo in $(gh repo list ZySec-AI --limit 200 --json name --jq '.[].name'); do
  gh api "/repos/ZySec-AI/$repo/collaborators?affiliation=direct" --jq ".[] | \"$repo: \(.login) (\(.role_name))\""
done
```

### List all org rulesets

```bash
gh api /orgs/ZySec-AI/rulesets --jq '.[] | "\(.id) | \(.name) | \(.enforcement)"'
```

### Edit a ruleset

```bash
gh api /orgs/ZySec-AI/rulesets/<id> > /tmp/rs.json
# edit /tmp/rs.json
gh api -X PUT /orgs/ZySec-AI/rulesets/<id> --input /tmp/rs.json
```

---

## Branch flow validator

The reusable workflow template `workflow-templates/branch-flow-check.yml` is available in every repo's "Add workflow" picker. It validates:

- Branch name matches Conventional Commits pattern (`feat/x`, `fix/y`, `hotfix/z`, etc.)
- Merge flow follows `<type>/* → develop → stage → release` (with `hotfix/*` → release shortcut)

Add it to any repo via the GitHub UI (Actions → New workflow → search "branch flow") or copy the file directly.

---

## Limitations on Team plan

The following require GitHub Enterprise Cloud and are **not enforceable today**:

- Block members from deleting repos (`members_can_delete_repositories`)
- Block members from changing repo visibility (private → public) (`members_can_change_repo_visibility`)
- Block outside collaborator invites (`members_can_invite_outside_collaborators`)
- Custom org roles

Mitigation: members **cannot create repos** at all now, so the visibility-flip path is closed. Deletion risk remains only for users with admin permission on individual repos — a small set (admins team).

---

## Last updated

2026-04-28 — initial governance baseline (vibekit/hypermind cycle).
