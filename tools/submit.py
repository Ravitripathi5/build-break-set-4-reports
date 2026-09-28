#!/usr/bin/env python3
"""Create your submission zip:  python3 tools/submit.py --id p07

Includes: Dockerfile, app/, infra/*.tf, .github/, crack-files/ (your fixes), FINDINGS.md.
Excludes: Terraform state and caches, .env files, tfvars, zips.
Refuses to build the zip if a real-looking AWS key is found outside crack-files/.
"""
import argparse
import json
import os
import re
import sys
import zipfile

SKIP_DIRS = {".terraform", "__pycache__", ".git", "tools"}
SKIP_FILE = re.compile(r"(\.tfstate(\..*)?$|\.tfvars$|\.zip$|^\.env$|\.env\.local$|^out\.json$|\.lock\.hcl$|^\.DS_Store$)")
KEY_ID = re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b")
REQUIRED = ["Dockerfile", "FINDINGS.md", "infra/main.tf", ".github/workflows/deploy.yml"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    args = ap.parse_args()
    if not re.fullmatch(r"p\d{2}", args.id):
        sys.exit("--id must look like p07")
    root = os.getcwd()
    try:
        set_no = json.load(open(os.path.join(root, "set.json")))["set"]
    except (OSError, KeyError, json.JSONDecodeError):
        sys.exit("Run this from your set folder (the one with set.json).")

    files, leaks = [], []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if SKIP_FILE.search(name):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root)
            files.append(rel)
            if rel.startswith("crack-files" + os.sep):
                continue
            text = open(path, encoding="utf-8", errors="ignore").read()
            for m in KEY_ID.finditer(text):
                if "EXAMPLE" not in m.group(0):
                    leaks.append(f"{rel}: {m.group(0)[:8]}...")

    if leaks:
        print("STOP: possible AWS access keys found. Remove them and run again:")
        print("\n".join("  " + x for x in leaks))
        sys.exit(1)
    missing = [r for r in REQUIRED if not os.path.exists(os.path.join(root, r))]
    if missing:
        print("Warning - missing (you lose the related points):", ", ".join(missing))

    out = os.path.join(root, f"set-{set_no}-{args.id}-submission.zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in sorted(files):
            zf.write(os.path.join(root, rel), rel)
    print(f"Created {out} ({len(files)} files). Upload this zip. Do NOT destroy your AWS resources.")


if __name__ == "__main__":
    main()
