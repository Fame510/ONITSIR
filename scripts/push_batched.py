#!/usr/bin/env python3
"""Shrink the logo, then push the ONITSIR tree in size-bounded batches.

Single-arg exec limit (~128KB) means the base64 payload per commit call must stay
small. We (1) downscale the logo well under that, then (2) greedily pack files into
commits whose serialized args JSON stays under LIMIT bytes.
"""
import base64
import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path("/tmp/ONITSIR")
OWNER = "Fame510"
REPO = "ONITSIR"
LIMIT = 100_000  # bytes of args JSON per commit call (safe margin under ~128KB)

SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", "build", "dist"}
BIN_EXT = {".png", ".jpg", ".jpeg", ".gif", ".ico"}


def shrink_logo():
    p = ROOT / "assets" / "logo.png"
    img = Image.open(p).convert("RGB")
    img.thumbnail((480, 480))
    img.save(p, format="PNG", optimize=True)
    kb = p.stat().st_size / 1024
    print(f"LOGO_RESIZED: {img.size} {kb:.0f}KB")
    return kb


def should_skip(p: Path) -> bool:
    if set(p.parts) & SKIP_DIRS:
        return True
    if p.suffix == ".pyc" or any(s.endswith(".egg-info") for s in p.parts):
        return True
    return False


def make_upsert(f: Path) -> dict:
    rel = f.relative_to(ROOT).as_posix()
    data = f.read_bytes()
    if f.suffix in BIN_EXT:
        return {"path": rel, "content": base64.b64encode(data).decode("ascii"), "encoding": "base64"}
    return {"path": rel, "content": data.decode("utf-8"), "encoding": "utf-8"}


def commit(batch, n):
    args = {
        "owner": OWNER, "repo": REPO, "branch": "main",
        "message": f"feat: ONITSIR v0.1.0 content ({n})",
        "upserts": batch,
    }
    res, err = run_composio_tool("GITHUB_COMMIT_MULTIPLE_FILES", args)
    if err:
        print(f"COMMIT_{n}_ERROR:", str(err)[:400])
        return False
    print(f"COMMIT_{n}_OK: {len(batch)} files -> {[u['path'] for u in batch]}")
    return True


def main() -> int:
    shrink_logo()
    files = [f for f in sorted(ROOT.rglob("*")) if f.is_file() and not should_skip(f)]
    upserts = [make_upsert(f) for f in files]

    # Greedy pack by serialized size.
    batches, cur, cur_size = [], [], 0
    for u in upserts:
        usize = len(json.dumps(u))
        if usize > LIMIT:
            print(f"TOO_BIG_SINGLE: {u['path']} = {usize}B (skipping)")
            continue
        if cur and cur_size + usize > LIMIT:
            batches.append(cur)
            cur, cur_size = [], 0
        cur.append(u)
        cur_size += usize
    if cur:
        batches.append(cur)

    print(f"PLAN: {len(upserts)} files in {len(batches)} commits")
    ok = True
    for i, b in enumerate(batches, 1):
        if not commit(b, i):
            ok = False
            break
    print("ALL_OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
