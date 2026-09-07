# How the label taxonomy is enforced

The taxonomy is [`labels.yml`](labels.yml) — 42 labels, live across all 66
non-archived repositories.

## What actually enforces it

| Mechanism | Covers | When | Can delete? |
|---|---|---|---|
| **`sync-labels.yml`** | **all 66 repos** | daily 03:17 UTC, on manifest change, manual | only on a manual run with `apply: true` |
| **`label-drift-report.yml`** | all 66 repos | Mondays 09:00 UTC | no — opens an issue |
| **`enforce-standards.yml`** → `_reusable-enforce-standards.yml` | **all 66 repos** | the moment a label is *created* | yes, immediately |

`sync-labels.yml` is the workhorse. It iterates every non-archived repo through
the API from this one repository, so it does not depend on anything being
installed in the target repos.

## What it deliberately does not do

**`sync-labels` reports by default and never deletes on a schedule.** Deleting a
label strips it from every issue it was ever on, irreversibly. A nightly job
should tell you about drift; a person should decide when to erase something. Run
it manually with `apply: true` to act on the report.

## Known gaps — read these before assuming you are covered

**This gap is now closed** (T-329). The wrapper was in 9 of 66 repos; it is now
in all of them, so an off-manifest label is deleted within seconds of being
created rather than surviving until the next nightly reconcile.

Worth remembering if this recurs: `workflow-sync.yml` will not distribute a new
wrapper. It only refreshes files that **already exist** in a repo. Adding a
workflow to repos that lack it is always a separate, deliberate rollout.

`threatmap` enforces pull requests through a **repository ruleset** rather than
classic branch protection — so the branch-protection API reports it as
unprotected while direct writes still fail with a 409. Anything scripted against
this org should expect that.

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
