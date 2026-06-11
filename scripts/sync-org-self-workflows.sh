#!/usr/bin/env bash
# Copy standard thin wrappers from workflow-templates/ into .github/workflows/
# so the org .github meta-repo runs the same triggers as app repos.
# Rewrites reusable refs to local ./ paths so PR branches work before merge to develop.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STANDARD=(
  quality.yml security.yml release.yml hotfix-security.yml
  code-review.yml code-review-pr.yml issue-triage.yml issue-auto-fix.yml
  docs-to-wiki.yml branch-flow-check.yml pr-standards.yml stale.yml
  merge-comment.yml code-freeze.yml sprint-retro.yml check-license.yml
)

for f in "${STANDARD[@]}"; do
  sed \
    -e 's|ZySec-AI/\.github/\.github/workflows/|./.github/workflows/|g' \
    -e 's|@develop||g' \
    "$ROOT/workflow-templates/$f" > "$ROOT/.github/workflows/$f"
  echo "synced $f"
done

echo "Done. Org-only workflows (unchanged): workflow-sync, new-repo-bootstrap, ci-failure-monitor, sync-labels"
