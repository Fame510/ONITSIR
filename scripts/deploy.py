#!/usr/bin/env python3
"""Deploy ONITSIR v0.2.0:
  1. push updated source + site to main
  2. create gh-pages branch with the site at root
  3. enable GitHub Pages (gh-pages, /)
  4. update the repo description (scrubbed of any remix language)
"""
import base64, json, os
from pathlib import Path

ROOT = Path("/tmp/ONITSIR")
OWNER, REPO = "Fame510", "ONITSIR"
LIMIT = 95_000  # bytes of args JSON per commit call (safe under ~128KB single-arg cap)

TEXT_SUFFIX = {".py", ".md", ".toml", ".txt", ".js", ".html", ".json", ".svg", ".cfg", ".ini", ""}
BIN_SUFFIX = {".png", ".jpg", ".jpeg", ".gif", ".ico"}
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", "build", "dist"}


def upsert_for(repo_path: str, local: Path) -> dict:
    data = local.read_bytes()
    if local.suffix in BIN_SUFFIX:
        return {"path": repo_path, "content": base64.b64encode(data).decode("ascii"), "encoding": "base64"}
    return {"path": repo_path, "content": data.decode("utf-8"), "encoding": "utf-8"}


def commit(branch, upserts, message, base_branch=None):
    """Pack upserts into size-bounded commits; return True on success."""
    batches, cur, size = [], [], 0
    for u in upserts:
        usz = len(json.dumps(u))
        if usz > LIMIT:
            print(f"  TOO_BIG single file {u['path']} = {usz}B -> own commit")
            if cur: batches.append(cur); cur, size = [], 0
            batches.append([u]); continue
        if cur and size + usz > LIMIT:
            batches.append(cur); cur, size = [], 0
        cur.append(u); size += usz
    if cur: batches.append(cur)

    first = True
    for i, b in enumerate(batches, 1):
        args = {"owner": OWNER, "repo": REPO, "branch": branch,
                "message": f"{message} ({i}/{len(batches)})", "upserts": b}
        if base_branch and first:
            args["base_branch"] = base_branch
        res, err = run_composio_tool("GITHUB_COMMIT_MULTIPLE_FILES", args)
        if err:
            print(f"  COMMIT FAIL [{branch} {i}]: {str(err)[:300]}")
            return False
        print(f"  committed [{branch} {i}/{len(batches)}]: {[u['path'] for u in b]}")
        first = False
    return True


def collect_main_text():
    ups = []
    for f in sorted(ROOT.rglob("*")):
        if not f.is_file(): continue
        if set(f.parts) & SKIP_DIRS: continue
        if f.suffix == ".pyc" or any(s.endswith(".egg-info") for s in f.parts): continue
        rel = f.relative_to(ROOT).as_posix()
        if f.suffix in BIN_SUFFIX:  # binaries (logo) already on main, unchanged — skip
            continue
        if rel == "data/roster.json":  # 106KB, unchanged on main — skip re-push
            continue
        ups.append(upsert_for(rel, f))
    return ups


def main():
    # 1. MAIN — updated source + docs + site source (text only; binaries unchanged)
    print("== push main ==")
    if not commit("main", collect_main_text(),
                  "feat: ONITSIR v0.2.0 — add Shackle Governor layer + in-browser app; scrub public origins"):
        return 1

    # 2. gh-pages — the site at ROOT
    print("== create gh-pages ==")
    site = [
        ("index.html", ROOT / "site/index.html"),
        ("app.js", ROOT / "site/app.js"),
        (".nojekyll", ROOT / "site/.nojekyll"),
        ("logo.png", ROOT / "assets/logo.png"),
        ("roster.json", ROOT / "data/roster.json"),
    ]
    ups = [upsert_for(rp, lp) for rp, lp in site]
    if not commit("gh-pages", ups, "deploy: ONITSIR in-browser app", base_branch="main"):
        return 1

    # 3. enable Pages (legacy build from gh-pages root)
    print("== enable pages ==")
    res, err = run_composio_tool("GITHUB_CREATE_OR_UPDATE_GITHUB_PAGES_SITE", {
        "owner": OWNER, "repo": REPO, "build_type": "legacy",
        "source_branch": "gh-pages", "source_path": "/",
    })
    print("  pages:", "OK" if not err else str(err)[:300])

    # 4. update repo description (scrubbed)
    print("== update repo description ==")
    res, err = run_composio_tool("GITHUB_UPDATE_A_REPOSITORY", {
        "owner": OWNER, "repo": REPO,
        "description": 'ONITSIR — "On It, Sir." The AI agency operating system: a 164-specialist roster, a fail-closed governance gate, a verify-gated workflow, and an autonomous phase machine, fused into one engine.',
        "homepage": "https://fame510.github.io/ONITSIR/",
    })
    print("  desc:", "OK" if not err else str(err)[:300])
    print("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
