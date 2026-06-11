#!/usr/bin/env bash
# Copy standard thin wrappers from workflow-templates/ into .github/workflows/
# so the org .github meta-repo runs the same triggers as app repos.
# Logic lives only in _reusable-*.yml — never duplicate steps here.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STANDARD=(
  quality.yml security.yml release.yml hotfix-security.yml
  code-review.yml code-review-pr.yml issue-triage.yml issue-auto-fix.yml
  docs-to-wiki.yml branch-flow-check.yml pr-standards.yml stale.yml
  merge-comment.yml code-freeze.yml sprint-retro.yml check-license.yml
)

for f in "${STANDARD[@]}"; do
  cp "$ROOT/workflow-templates/$f" "$ROOT/.github/workflows/$f"
  echo "synced $f"
done

echo "Done. Org-only workflows (unchanged): workflow-sync, new-repo-bootstrap, ci-failure-monitor, sync-labels"
