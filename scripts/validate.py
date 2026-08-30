#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATEGORY_DIR = ROOT / "data" / "categories"

required = {
    "uid", "id", "text", "author", "category", "source",
    "is_favorite", "is_used", "usage_count", "background_style",
    "text_align", "font_size", "show_author", "created_at", "updated_at",
}

seen_uid = set()
seen_text = set()
errors = []
count = 0

for path in sorted(CATEGORY_DIR.glob("*.json")):
    items = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(items, list):
        errors.append(f"{path}: top-level JSON must be an array")
        continue

    for i, item in enumerate(items):
        count += 1
        missing = required - set(item)
        if missing:
            errors.append(f"{path}[{i}]: missing {sorted(missing)}")
            continue

        uid = str(item["uid"]).strip()
        text = str(item["text"]).strip()

        if uid in seen_uid:
            errors.append(f"{path}[{i}]: duplicate uid {uid}")
        seen_uid.add(uid)

        normalized = " ".join(text.casefold().split())
        if normalized in seen_text:
            errors.append(f"{path}[{i}]: duplicate quotation text")
        seen_text.add(normalized)

        if item["source"] not in {"ai", "manual", "public-domain", "licensed"}:
            errors.append(f"{path}[{i}]: invalid source {item['source']!r}")

if errors:
    print("Validation FAILED")
    for error in errors:
        print(" -", error)
    raise SystemExit(1)

print(f"Validation OK: {count} quotations.")
