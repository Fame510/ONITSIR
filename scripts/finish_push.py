#!/usr/bin/env python3
"""Finish the push: roster.json (alone) + a quantized, smaller logo."""
import base64
import json
from pathlib import Path

from PIL import Image

ROOT = Path("/tmp/ONITSIR")
OWNER, REPO = "Fame510", "ONITSIR"


def push_one(path_rel, content, encoding, msg):
    args = {
        "owner": OWNER, "repo": REPO, "branch": "main", "message": msg,
        "upserts": [{"path": path_rel, "content": content, "encoding": encoding}],
    }
    argsize = len(json.dumps(args))
    print(f"PUSH {path_rel}: args={argsize}B")
    res, err = run_composio_tool("GITHUB_COMMIT_MULTIPLE_FILES", args)
    if err:
        print(f"  ERROR: {str(err)[:300]}")
        return False
    print("  OK")
    return True


def main():
    # 1) roster.json alone
    roster = (ROOT / "data" / "roster.json").read_text()
    push_one("data/roster.json", roster, "utf-8", "chore: add specialist roster data (164)")

    # 2) quantized logo, target < 85KB
    p = ROOT / "assets" / "logo.png"
    img = Image.open(p).convert("RGB")
    img.thumbnail((256, 256))
    q = img.quantize(colors=128, method=Image.MEDIANCUT)
    out = ROOT / "assets" / "logo.png"
    q.save(out, format="PNG", optimize=True)
    kb = out.stat().st_size / 1024
    print(f"LOGO: {img.size} quantized -> {kb:.0f}KB")
    b64 = base64.b64encode(out.read_bytes()).decode("ascii")
    print(f"LOGO b64 len: {len(b64)}")
    push_one("assets/logo.png", b64, "base64", "assets: add ONITSIR logo")


if __name__ == "__main__":
    main()
