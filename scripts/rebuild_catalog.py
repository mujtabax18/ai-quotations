#!/usr/bin/env python3
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
CATEGORY_DIR = ROOT / "data" / "categories"

all_items = []
categories = []
seen_uid = set()

for path in sorted(CATEGORY_DIR.glob("*.json")):
    items = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(items, list):
        raise ValueError(f"{path} must contain a JSON array")

    category_names = {item.get("category") for item in items}
    category_names.discard(None)
    if len(category_names) > 1:
        raise ValueError(f"{path} mixes multiple categories")

    for item in items:
        uid = item.get("uid")
        if not uid:
            raise ValueError(f"Missing uid in {path}")
        if uid in seen_uid:
            raise ValueError(f"Duplicate uid: {uid}")
        seen_uid.add(uid)
        all_items.append(item)

    normalized = json.dumps(items, ensure_ascii=False, indent=2) + "\n"
    path.write_text(normalized, encoding="utf-8")

    categories.append({
        "id": path.stem,
        "name": next(iter(category_names), path.stem.replace("-", " ").title()),
        "count": len(items),
        "file": str(path.relative_to(ROOT)).replace("\\", "/"),
        "sha256": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
    })

all_items.sort(key=lambda x: (str(x.get("category", "")).casefold(), str(x.get("uid", ""))))
all_content = json.dumps(all_items, ensure_ascii=False, indent=2) + "\n"
(ROOT / "data" / "all.json").write_text(all_content, encoding="utf-8")

manifest_path = ROOT / "manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
version = manifest.get("content_version", "1.0.0")
now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

catalog = {
    "schema_version": 1,
    "content_version": version,
    "updated_at": now,
    "total_quotations": len(all_items),
    "total_categories": len(categories),
    "categories": categories,
}
(ROOT / "catalog.json").write_text(
    json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)

manifest.update({
    "schema_version": 1,
    "updated_at": now,
    "catalog": "catalog.json",
    "all_quotations": "data/all.json",
    "all_quotations_sha256": hashlib.sha256(all_content.encode("utf-8")).hexdigest(),
})
manifest_path.write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)

print(f"Built {len(all_items)} quotations across {len(categories)} categories.")
