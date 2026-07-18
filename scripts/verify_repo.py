#!/usr/bin/env python3
"""Verify the ONITSIR repo exists and contains the full tree."""
import json

OWNER, REPO = "Fame510", "ONITSIR"

repo, err = run_composio_tool("GITHUB_GET_A_REPOSITORY", {"owner": OWNER, "repo": REPO})
if err:
    print("REPO_ERR:", str(err)[:300]); raise SystemExit(1)

def dig(o, *keys):
    for k in keys:
        o = o.get(k) if isinstance(o, dict) else None
        if o is None: return None
    return o

data = repo.get("data", repo) if isinstance(repo, dict) else {}
# find html_url and default_branch anywhere
blob = json.dumps(repo)
import re
url = re.search(r'"html_url"\s*:\s*"([^"]+ONITSIR)"', blob)
branch = re.search(r'"default_branch"\s*:\s*"([^"]+)"', blob)
print("REPO_URL:", url.group(1) if url else "(not found)")
print("DEFAULT_BRANCH:", branch.group(1) if branch else "(unknown)")

# List the full tree recursively
tree, err2 = run_composio_tool("GITHUB_GET_A_TREE", {
    "owner": OWNER, "repo": REPO, "tree_sha": (branch.group(1) if branch else "main"),
    "recursive": "true",
})
if err2:
    print("TREE_ERR:", str(err2)[:300])
else:
    tb = json.dumps(tree)
    paths = re.findall(r'"path"\s*:\s*"([^"]+)"', tb)
    files = [p for p in paths]
    print(f"TREE_FILE_COUNT: {len(files)}")
    for p in sorted(set(files)):
        print("  ", p)
