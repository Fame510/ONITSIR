#!/usr/bin/env python3
"""Create the ONITSIR repo on the authenticated GitHub account and push the tree."""
import base64
import json
import sys
from pathlib import Path

ROOT = Path("/tmp/ONITSIR")
OWNER = "Fame510"
REPO = "ONITSIR"

TEXT_EXT = {".py", ".md", ".txt", ".toml", ".json", ".cfg", ".ini", ".gitignore", ""}
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".egg-info", "build", "dist"}


def should_skip(p: Path) -> bool:
    parts = set(p.parts)
    if parts & SKIP_DIRS:
        return True
    if p.suffix in {".pyc"}:
        return True
    if any(seg.endswith(".egg-info") for seg in p.parts):
        return True
    return False


def collect_upserts():
    upserts = []
    for f in sorted(ROOT.rglob("*")):
        if not f.is_file() or should_skip(f):
            continue
        rel = f.relative_to(ROOT).as_posix()
        data = f.read_bytes()
        if f.suffix == ".png" or f.suffix in {".jpg", ".jpeg", ".gif", ".ico"}:
            upserts.append({
                "path": rel,
                "content": base64.b64encode(data).decode("ascii"),
                "encoding": "base64",
            })
        else:
            upserts.append({
                "path": rel,
                "content": data.decode("utf-8"),
                "encoding": "utf-8",
            })
    return upserts


def main() -> int:
    # 1. Create the repo (auto_init so 'main' exists to commit onto).
    create_args = {
        "name": REPO,
        "description": 'ONITSIR — "On It, Sir." An AI agency operating system: a routable roster of 164 specialists, a verify-gated workflow, and an autonomous phase machine. A remix of agency-agents + superpowers + gsd-pro.',
        "private": False,
        "auto_init": True,
        "license_template": "mit",
        "has_issues": True,
    }
    created, err = run_composio_tool(
        "GITHUB_CREATE_A_REPOSITORY_FOR_THE_AUTHENTICATED_USER", create_args
    )
    print("CREATE_RESULT:", json.dumps({"error": err, "ok": created is not None})[:300])
    if err:
        # If it already exists, continue to push (idempotent-ish).
        print("CREATE_ERR_DETAIL:", str(err)[:300])

    # 2. Push all files atomically.
    upserts = collect_upserts()
    print(f"UPSERT_COUNT: {len(upserts)}")
    print("FILES:", ", ".join(u["path"] for u in upserts))

    commit_args = {
        "owner": OWNER,
        "repo": REPO,
        "branch": "main",
        "message": "feat: ONITSIR v0.1.0 — roster + verify-gated workflow + phase machine (50 tests passing)",
        "upserts": upserts,
    }
    committed, err2 = run_composio_tool("GITHUB_COMMIT_MULTIPLE_FILES", commit_args)
    if err2:
        print("COMMIT_ERROR:", str(err2)[:600])
        return 1
    # surface useful bits of the response
    blob = json.dumps(committed)
    for key in ("html_url", "sha", "commit", "ref"):
        idx = blob.find(key)
        if idx != -1:
            print(f"COMMIT_{key}:", blob[idx:idx+160])
    print("COMMIT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
