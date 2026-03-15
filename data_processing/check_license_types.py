"""
check_license_types.py

Scan all directory_info.json files and report the type/structure of the license field.

Usage:
  python check_license_types.py
"""

import json
from pathlib import Path
from collections import defaultdict

DATA_ROOT = Path(__file__).parent.parent / "data" / "output"


def describe_license(license_val) -> str:
    if license_val is None:
        return "null"
    if isinstance(license_val, str):
        return f"str: {license_val!r}"
    if isinstance(license_val, dict):
        detected = license_val.get("detected_type")
        if detected is None:
            return f"dict(no detected_type), keys={list(license_val.keys())}"
        if isinstance(detected, str):
            return f"dict->str: {detected!r}"
        if isinstance(detected, dict):
            return f"dict->dict: keys={list(detected.keys())}"
        if isinstance(detected, list):
            items = []
            for item in detected:
                if isinstance(item, dict):
                    items.append(f"dict(keys={list(item.keys())})")
                else:
                    items.append(repr(item))
            return f"dict->list[{', '.join(items)}]"
        return f"dict->unknown({type(detected).__name__})"
    if isinstance(license_val, list):
        return f"list(len={len(license_val)})"
    return f"unknown({type(license_val).__name__})"


def main():
    json_files = sorted(DATA_ROOT.glob("*/*/directory_info.json"))
    print(f"Found {len(json_files)} repos\n")

    type_groups = defaultdict(list)

    for json_path in json_files:
        org = json_path.parts[-3]
        repo = json_path.parts[-2]
        repo_id = f"{org}/{repo}"

        try:
            with open(json_path, encoding="utf-8") as f:
                raw = json.load(f)
        except Exception as e:
            print(f"[ERROR] {repo_id}: {e}")
            continue

        desc = describe_license(raw.get("license"))
        type_groups[desc].append(repo_id)

    print("=== License type groups ===\n")
    for desc, repos in sorted(type_groups.items(), key=lambda x: -len(x[1])):
        print(f"[{len(repos)} repos] {desc}")
        for r in repos[:3]:
            print(f"    {r}")
        if len(repos) > 3:
            print(f"    ... and {len(repos) - 3} more")
        print()


if __name__ == "__main__":
    main()
