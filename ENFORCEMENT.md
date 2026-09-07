# How the label taxonomy is enforced

The taxonomy is [`labels.yml`](labels.yml) — 42 labels, live across all 66
non-archived repositories.

## What actually enforces it

| Mechanism | Covers | When | Can delete? |
|---|---|---|---|
| **`sync-labels.yml`** | **all 66 repos** | daily 03:17 UTC, on manifest change, manual | **yes — automatically, including on the schedule** |
| **`label-drift-report.yml`** | all 66 repos | Mondays 09:00 UTC | no — opens an issue |
| **`enforce-standards.yml`** → `_reusable-enforce-standards.yml` | **all 66 repos** | the moment a label is *created* | yes, immediately |

`sync-labels.yml` is the workhorse. It iterates every non-archived repo through
the API from this one repository, so it does not depend on anything being
installed in the target repos.

## Deletion is automatic — and what stops it going wrong

The nightly run **deletes** every off-manifest label it finds. Deleting a label
strips it from every issue it was ever on and cannot be undone, so two guards sit
in front of it. Both abort the run and write nothing:

**The manifest floor.** If `labels.yml` parses to fewer than 30 labels, the run
refuses. This is the failure that matters: a truncated or unparseable manifest
makes *every* label in *every* repository look off-manifest, and without this
guard the job would delete all of them in one pass. A YAML file is one bad merge
away from that at any time.

**The blast radius ceiling.** If a single pass would delete more than 150 labels,
the run refuses and lists what it would have removed. A day's genuine drift is a
handful. Hundreds means something upstream broke — a bad merge, a bot loop, a
manifest edited in a hurry — and a person should look before anything is erased.

Either guard failing the job is deliberate: a silent skip would let the taxonomy
rot unnoticed, which is the exact failure that produced 141 labels in the first
place.

To preview without writing, run it manually and untick `apply`. To push through a
genuinely large deliberate change, raise `max_deletes` on a manual run.

**The daily reconcile is a backstop, not the front line.** The per-repo guard
deletes an off-manifest label within seconds of its creation, so by the time the
nightly run happens there should be almost nothing left to find.

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
