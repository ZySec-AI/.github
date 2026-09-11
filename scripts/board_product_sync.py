#!/usr/bin/env python3
"""Fill blank `Product` values on the Engineering Delivery board.

Reads the repository-to-product mapping from `board-products.yml` and resolves
Product option ids live from the board. Option ids are never written down: that
is what makes renaming a product an edit to the manifest and the board, with no
code change. Cyberpod was renamed to Autonous on 2026-09-11 and the previous
hardcoded map named a product that no longer existed, in seven places.

Only blank items are touched. A value somebody set by hand is left alone, and a
repository absent from the manifest is skipped rather than guessed: an item filed
under the wrong product is silently wrong, while a blank one is visibly missing.

Dry run by default; `--apply` writes. Output is GitHub-flavoured Markdown so it
renders in the job summary.
"""

from __future__ import annotations

import collections
import json
import pathlib
import subprocess
import sys
import time

ORG = "ZySec-AI"
MANIFEST = pathlib.Path(__file__).resolve().parent.parent / "board-products.yml"


def load_manifest() -> tuple[int, dict[str, str]]:
    """Parse the manifest without a YAML dependency: it is deliberately flat."""
    project, mapping = None, {}
    for line in MANIFEST.read_text().splitlines():
        line = line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if line.startswith("project:"):
            project = int(line.split(":", 1)[1])
        elif line.startswith("  ") and ":" in line:
            repo, product = line.split(":", 1)
            mapping[repo.strip()] = product.strip()
    if project is None or not mapping:
        raise SystemExit("board-products.yml is missing `project:` or has no repositories")
    return project, mapping


def gq(query: str, **variables):
    body = json.dumps({"query": query, "variables": variables})
    for attempt in range(5):
        proc = subprocess.run(
            ["gh", "api", "graphql", "--input", "-"],
            input=body, capture_output=True, text=True,
        )
        if proc.returncode == 0:
            parsed = json.loads(proc.stdout)
            if "errors" not in parsed:
                return parsed["data"]
            message = "; ".join(e.get("message", "") for e in parsed["errors"])
        else:
            message = proc.stderr[:300]
        if any(k in message.lower() for k in ("rate limit", "secondary", "abuse")):
            time.sleep(min(60 * (attempt + 1), 300))
            continue
        raise SystemExit(f"GraphQL failed: {message}")
    raise SystemExit("GraphQL failed after retries")


FIELDS = """query($org:String!,$n:Int!){organization(login:$org){projectV2(number:$n){
  id fields(first:60){nodes{... on ProjectV2SingleSelectField{id name options{id name}}}}}}}"""

ITEMS = """query($org:String!,$n:Int!,$cursor:String){organization(login:$org){projectV2(number:$n){
  items(first:100,after:$cursor){pageInfo{hasNextPage endCursor} nodes{ id
    fieldValues(first:30){nodes{... on ProjectV2ItemFieldSingleSelectValue{
      field{... on ProjectV2SingleSelectField{name}}}}}
    content{... on Issue{repository{name}} ... on PullRequest{repository{name}}}}}}}}"""

SET = """mutation($p:ID!,$i:ID!,$f:ID!,$o:String!){updateProjectV2ItemFieldValue(input:{
  projectId:$p,itemId:$i,fieldId:$f,value:{singleSelectOptionId:$o}}){projectV2Item{id}}}"""


def main() -> int:
    apply = "--apply" in sys.argv
    project_number, mapping = load_manifest()

    board = gq(FIELDS, org=ORG, n=project_number)["organization"]["projectV2"]
    field = next(
        (f for f in board["fields"]["nodes"] if f and f.get("name") == "Product"), None
    )
    if field is None:
        raise SystemExit(f"project {project_number} has no `Product` field")
    option = {o["name"]: o["id"] for o in field["options"]}

    # A product named in the manifest with no option on the board is a typo, not
    # a missing product. Failing loudly beats silently skipping every item for it.
    unknown = sorted({p for p in mapping.values() if p not in option})
    if unknown:
        raise SystemExit(
            f"manifest names products with no option on the board: {', '.join(unknown)}\n"
            f"board options are: {', '.join(sorted(option))}"
        )

    todo, unmapped = [], collections.Counter()
    cursor = None
    while True:
        conn = gq(ITEMS, org=ORG, n=project_number, cursor=cursor)[
            "organization"]["projectV2"]["items"]
        for item in conn["nodes"]:
            names = {
                v["field"]["name"] for v in item["fieldValues"]["nodes"]
                if v and (v.get("field") or {}).get("name")
            }
            if "Product" in names:
                continue
            repo = ((item.get("content") or {}).get("repository") or {}).get("name")
            if not repo:
                continue
            product = mapping.get(repo)
            if product is None:
                unmapped[repo] += 1
                continue
            todo.append((item["id"], repo, product))
        if not conn["pageInfo"]["hasNextPage"]:
            break
        cursor = conn["pageInfo"]["endCursor"]

    print("## Board Product sync\n")
    print(f"- mode: **{'apply' if apply else 'dry run'}**")
    print(f"- blank items with a known repository: **{len(todo)}**")
    if todo:
        print("\n| repository | product | items |\n|---|---|---:|")
        for (repo, product), n in collections.Counter(
            (r, p) for _, r, p in todo
        ).most_common():
            print(f"| `{repo}` | {product} | {n} |")

    # Named, never just counted. These are the items nobody can see in any
    # product figure, and a bare total is what let them stay invisible.
    if unmapped:
        print(f"\n- blank items in repositories **not in the manifest**: "
              f"**{sum(unmapped.values())}** — these stay blank on purpose\n")
        print("| repository | items |\n|---|---:|")
        for repo, n in unmapped.most_common(20):
            print(f"| `{repo}` | {n} |")

    if not apply:
        print("\n_Dry run. Pass `--apply` to write._")
        return 0

    for n, (item_id, _repo, product) in enumerate(todo, start=1):
        gq(SET, p=board["id"], i=item_id, f=field["id"], o=option[product])
        if n % 50 == 0:
            time.sleep(1)  # stay well clear of the secondary rate limit
    print(f"\n**Set `Product` on {len(todo)} items.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
