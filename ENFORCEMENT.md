# How the label taxonomy is enforced

The taxonomy is [`labels.yml`](labels.yml) — 42 labels, live across all 66
non-archived repositories.

## What actually enforces it

| Mechanism | Covers | When | Can delete? |
|---|---|---|---|
| **`sync-labels.yml`** | **all 66 repos** | daily 03:17 UTC, on manifest change, manual | only on a manual run with `apply: true` |
| **`label-drift-report.yml`** | all 66 repos | Mondays 09:00 UTC | no — opens an issue |
| **`enforce-standards.yml`** → `_reusable-enforce-standards.yml` | **9 repos** (see below) | the moment a label is *created* | yes, immediately |

`sync-labels.yml` is the workhorse. It iterates every non-archived repo through
the API from this one repository, so it does not depend on anything being
installed in the target repos.

## What it deliberately does not do

**`sync-labels` reports by default and never deletes on a schedule.** Deleting a
label strips it from every issue it was ever on, irreversibly. A nightly job
should tell you about drift; a person should decide when to erase something. Run
it manually with `apply: true` to act on the report.

## Known gaps — read these before assuming you are covered

**Only 9 of 66 repos have `enforce-standards.yml`**, so the fast
delete-on-creation guard covers only those: `agentsight` and eight others that
already had the wrapper. Everywhere else, an off-manifest label survives until
the next `sync-labels` run reports it and someone applies the fix.

`workflow-sync.yml` will not close this gap on its own — it only refreshes
wrapper files that **already exist** in a repo, and does not add new ones.
Adding the wrapper to the remaining 57 repos is a separate, deliberate task.

**GitHub cannot prevent label creation.** Repository rulesets cover branches,
tags and pushes — not labels. Anyone with `triage` or above can create one.
Everything here is detect-and-remove. The only genuine preventive control is
repository permissions: the org default is already `none`, so auditing who holds
`maintain`/`admin` is what actually reduces drift at source.

**`main` is stale.** `develop` is the default branch and is 135 commits ahead of
`main`. Reusable workflows are referenced `@develop` — `enforce-standards.yml`
was the one exception, pinned `@main`, which meant changes to its reusable
workflow never reached callers. That pin is fixed here.

## Changing the taxonomy

Open a pull request against `labels.yml`. Merging it triggers `sync-labels` in
report mode, so you see what would change before anything does.

If a label keeps being re-created, treat it as evidence the manifest is missing
something rather than as a person misbehaving. That is what the drift report is
for.
