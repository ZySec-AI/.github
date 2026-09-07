#!/usr/bin/env python3
"""Bring every repository in the organisation back to the label manifest.

Reports by default and writes only with --apply. That default is deliberate: this
script can delete labels across every repository, and deleting a label removes it
from every issue it was ever on, irreversibly. A scheduled job should tell you
about drift; a human should decide when to erase something.

Used by .github/workflows/label-reconcile.yml and label-drift-report.yml.
"""
import argparse, json, subprocess, sys, time
from collections import defaultdict

ORG = "ZySec-AI"


def sh(cmd, check=True, retries=5):
    for attempt in range(retries):
        out = subprocess.run(cmd, capture_output=True, text=True)
        if out.returncode == 0:
            return out
        err = out.stderr.lower()
        if "rate limit" in err or "abuse" in err or "secondary" in err:
            time.sleep(min(60 * (attempt + 1), 300))
            continue
        if check:
            raise RuntimeError(out.stderr.strip()[:250])
        return out
    raise RuntimeError("gave up after retries")


def load_manifest(path):
    labels, cur = [], None
    for line in open(path):
        line = line.rstrip()
        if line.startswith("- name:"):
            cur = {"name": line.split(":", 1)[1].strip().strip('"')}
            labels.append(cur)
        elif cur and line.strip().startswith("color:"):
            cur["color"] = line.split(":", 1)[1].strip().strip('"')
        elif cur and line.strip().startswith("description:"):
            cur["description"] = line.split(":", 1)[1].strip().strip('"')
    return labels


def repos():
    out = sh(["gh", "api", "graphql", "--paginate", "-f",
              'query=query($endCursor:String){organization(login:"%s")'
              "{repositories(first:100,after:$endCursor){pageInfo{hasNextPage endCursor}"
              "nodes{name isArchived}}}}" % ORG,
              "--jq", ".data.organization.repositories.nodes[]|select(.isArchived|not)|.name"])
    return sorted(set(out.stdout.split()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--repo")
    ap.add_argument("--min-labels", type=int, default=30,
                    help="refuse to run if the manifest has fewer than this")
    ap.add_argument("--max-deletes", type=int, default=150,
                    help="refuse to delete more than this in one run")
    args = ap.parse_args()

    manifest = load_manifest(args.manifest)

    # Deletion is automatic now, so a broken manifest is no longer a nuisance —
    # it is an org-wide data loss event. A truncated or unparseable labels.yml
    # would make every label in every repository look off-manifest, and the run
    # would cheerfully delete all of them. Refuse to proceed instead.
    if len(manifest) < args.min_labels:
        sys.exit(
            f"refusing to run: the manifest parsed to {len(manifest)} labels, "
            f"below the floor of {args.min_labels}. Either labels.yml is broken "
            f"or the floor needs lowering deliberately — both are decisions for "
            f"a person, not a nightly job."
        )
    if any(not l.get("color") for l in manifest):
        bad = [l["name"] for l in manifest if not l.get("color")][:5]
        sys.exit(f"refusing to run: manifest entries missing a colour: {bad}")

    want = {l["name"]: l for l in manifest}
    targets = [args.repo] if args.repo else repos()

    missing, extra, wrong = defaultdict(list), defaultdict(list), defaultdict(list)
    pending_deletes = []

    for repo in targets:
        have = {l["name"]: l for l in json.loads(
            sh(["gh", "api", f"/repos/{ORG}/{repo}/labels?per_page=100", "--paginate"]).stdout)}
        for name, spec in want.items():
            if name not in have:
                missing[repo].append(name)
                if args.apply:
                    sh(["gh", "api", f"/repos/{ORG}/{repo}/labels",
                        "-f", f"name={name}", "-f", f"color={spec['color']}",
                        "-f", f"description={spec.get('description','')}"], check=False)
            elif (have[name]["color"].lower() != spec["color"].lower()
                  or (have[name].get("description") or "") != spec.get("description", "")):
                wrong[repo].append(name)
                if args.apply:
                    sh(["gh", "api", "-X", "PATCH", f"/repos/{ORG}/{repo}/labels/{name}",
                        "-f", f"color={spec['color']}",
                        "-f", f"description={spec.get('description','')}"], check=False)
        for name in have:
            if name not in want:
                extra[repo].append(name)
                pending_deletes.append((repo, name))

    # Blast radius: a legitimate day's drift is a handful of labels. Hundreds
    # means something upstream went wrong — a bad merge, a bot loop, a manifest
    # someone edited in a hurry. Stop and make a person look.
    if args.apply and len(pending_deletes) > args.max_deletes:
        print(f"\n## Refused to delete\n")
        print(f"{len(pending_deletes)} labels are off-manifest, above the ceiling "
              f"of {args.max_deletes}. That is too many for one night's drift, so "
              f"nothing was deleted.\n")
        print("Check whether `labels.yml` changed unexpectedly. If this really is "
              "intended — a deliberate taxonomy change, say — re-run manually with "
              "a higher `--max-deletes`.\n")
        for repo, name in sorted(pending_deletes)[:40]:
            print(f"- `{repo}` — {name}")
        if len(pending_deletes) > 40:
            print(f"- …and {len(pending_deletes) - 40} more")
        return 2

    if args.apply:
        for repo, name in pending_deletes:
            sh(["gh", "api", "-X", "DELETE",
                f"/repos/{ORG}/{repo}/labels/{name}"], check=False)

    verb = "Applied" if args.apply else "Would apply"
    print(f"# Label reconcile — {len(targets)} repositories\n")
    print(f"Manifest: **{len(manifest)} labels** "
          f"([labels.yml](https://github.com/{ORG}/.github/blob/main/labels.yml))\n")
    print(f"| | Repos | Labels |\n|---|---|---|")
    for title, d in (("Missing (created)", missing), ("Off-manifest (deleted)", extra),
                     ("Wrong colour/description (corrected)", wrong)):
        print(f"| {title} | {len(d)} | {sum(len(v) for v in d.values())} |")

    if extra:
        print(f"\n## Off-manifest labels — {verb.lower()} removal\n")
        for repo, names in sorted(extra.items()):
            print(f"- **{repo}** — {', '.join(sorted(names))}")
        print("\n> If a label here keeps reappearing, the manifest is probably wrong "
              "rather than the person applying it. Open a pull request against "
              "`labels.yml` instead of deleting it again.")

    if not args.apply:
        print("\n_Report only — nothing was changed._")

    return 1 if extra else 0


if __name__ == "__main__":
    sys.exit(main())
