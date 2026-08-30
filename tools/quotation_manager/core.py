from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


DEFAULT_BACKGROUND_STYLE = "sunrise"
DEFAULT_TEXT_ALIGN = "center"
DEFAULT_FONT_SIZE = 30.0


class QuotationManagerError(RuntimeError):
    """Raised for repository/content operations that should be shown to the user."""


@dataclass
class ParsedQuotation:
    text: str
    author: str = ""
    category: str = ""
    language: str = ""


@dataclass
class ImportPreview:
    category: str
    category_slug: str
    accepted: list[ParsedQuotation] = field(default_factory=list)
    duplicate_existing: list[str] = field(default_factory=list)
    duplicate_batch: list[str] = field(default_factory=list)
    invalid: list[str] = field(default_factory=list)

    @property
    def skipped_count(self) -> int:
        return (
            len(self.duplicate_existing)
            + len(self.duplicate_batch)
            + len(self.invalid)
        )


@dataclass
class SaveResult:
    category: str
    file: Path
    inserted: int
    skipped: int
    content_version: str
    created_category: bool


@dataclass
class GitResult:
    ok: bool
    command: str
    output: str
    returncode: int


def repo_root_from(start: Path | None = None) -> Path:
    current = (start or Path(__file__).resolve()).resolve()
    if current.is_file():
        current = current.parent

    for candidate in [current, *current.parents]:
        if (candidate / "manifest.json").exists() and (candidate / "data" / "categories").exists():
            return candidate
    raise QuotationManagerError("Could not locate the quotation repository root.")


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE)
    value = re.sub(r"[\s_]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "uncategorized"


def normalize_text(value: str) -> str:
    return " ".join(value.casefold().split())


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_catalog(root: Path) -> dict[str, Any]:
    path = root / "catalog.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise QuotationManagerError(f"Could not read catalog.json: {exc}") from exc

    if not isinstance(data, dict):
        raise QuotationManagerError("catalog.json must contain a JSON object.")
    return data


def load_manifest(root: Path) -> dict[str, Any]:
    path = root / "manifest.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise QuotationManagerError(f"Could not read manifest.json: {exc}") from exc

    if not isinstance(data, dict):
        raise QuotationManagerError("manifest.json must contain a JSON object.")
    return data


def list_categories(root: Path) -> list[dict[str, Any]]:
    catalog = load_catalog(root)
    categories = catalog.get("categories", [])
    if not isinstance(categories, list):
        return []
    return sorted(
        [c for c in categories if isinstance(c, dict)],
        key=lambda c: str(c.get("name", "")).casefold(),
    )


def load_all_quotations(root: Path) -> list[dict[str, Any]]:
    path = root / "data" / "all.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise QuotationManagerError(f"Could not read data/all.json: {exc}") from exc
    if not isinstance(data, list):
        raise QuotationManagerError("data/all.json must contain a JSON array.")
    return [item for item in data if isinstance(item, dict)]


def _strip_code_fence(raw: str) -> str:
    raw = raw.strip()
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", raw, flags=re.I | re.S)
    return match.group(1).strip() if match else raw


def parse_ai_response(raw: str) -> list[dict[str, Any]]:
    cleaned = _strip_code_fence(raw)
    if not cleaned:
        raise QuotationManagerError("Paste the AI-generated JSON first.")

    try:
        decoded = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        # Be forgiving if an AI wrapped JSON in prose.
        first_array = cleaned.find("[")
        last_array = cleaned.rfind("]")
        if first_array >= 0 and last_array > first_array:
            try:
                decoded = json.loads(cleaned[first_array:last_array + 1])
            except json.JSONDecodeError:
                raise QuotationManagerError(
                    f"Could not parse the pasted JSON near line {exc.lineno}, column {exc.colno}."
                ) from exc
        else:
            raise QuotationManagerError(
                f"Could not parse the pasted JSON near line {exc.lineno}, column {exc.colno}."
            ) from exc

    if isinstance(decoded, dict):
        for key in ("quotations", "quotes", "data", "items"):
            if isinstance(decoded.get(key), list):
                decoded = decoded[key]
                break

    if not isinstance(decoded, list):
        raise QuotationManagerError("AI output must be a JSON array of quotation objects.")

    return [item for item in decoded if isinstance(item, dict)]


def preview_import(root: Path, raw_json: str, category: str) -> ImportPreview:
    category = category.strip()
    if not category:
        raise QuotationManagerError("Choose or enter a category.")

    decoded = parse_ai_response(raw_json)
    existing = {
        normalize_text(str(item.get("text", "")))
        for item in load_all_quotations(root)
        if str(item.get("text", "")).strip()
    }

    preview = ImportPreview(category=category, category_slug=slugify(category))
    batch_seen: set[str] = set()

    for index, item in enumerate(decoded, start=1):
        text = str(item.get("text", "")).strip()
        if not text:
            preview.invalid.append(f"Item {index}: missing quotation text")
            continue

        normalized = normalize_text(text)
        if normalized in existing:
            preview.duplicate_existing.append(text)
            continue
        if normalized in batch_seen:
            preview.duplicate_batch.append(text)
            continue

        author = str(item.get("author", "")).strip()
        language = str(item.get("language", "")).strip()

        preview.accepted.append(
            ParsedQuotation(
                text=text,
                author=author,
                category=category,
                language=language,
            )
        )
        batch_seen.add(normalized)

    return preview


def next_version(current: str, bump: str) -> str:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", current.strip())
    if not match:
        raise QuotationManagerError(
            f"Unsupported content version {current!r}; expected semantic version such as 1.2.3."
        )
    major, minor, patch = map(int, match.groups())
    if bump == "none":
        return current
    if bump == "patch":
        return f"{major}.{minor}.{patch + 1}"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    if bump == "major":
        return f"{major + 1}.0.0"
    raise QuotationManagerError(f"Unknown version bump: {bump}")


def _generate_remote_identity() -> tuple[str, int]:
    # uid is the primary remote identity. A large timestamp-derived integer keeps
    # compatibility with the existing app schema without colliding with legacy IDs.
    token = uuid.uuid4().hex
    remote_uid = f"quote-ai-{token}"
    numeric_id = int(time.time_ns() // 1_000)  # microsecond-scale integer
    return remote_uid, numeric_id


def _build_repo_item(parsed: ParsedQuotation) -> dict[str, Any]:
    uid, numeric_id = _generate_remote_identity()
    now = iso_now()
    item: dict[str, Any] = {
        "uid": uid,
        "id": numeric_id,
        "text": parsed.text,
        "author": parsed.author,
        "category": parsed.category,
        "source": "ai",
        "is_favorite": 0,
        "is_used": 0,
        "usage_count": 0,
        "background_style": DEFAULT_BACKGROUND_STYLE,
        "text_align": DEFAULT_TEXT_ALIGN,
        "font_size": DEFAULT_FONT_SIZE,
        "show_author": 1,
        "created_at": now,
        "updated_at": now,
    }
    if parsed.language:
        # The current schema allows additional properties, so retaining language
        # is backward-compatible and useful for future filtering.
        item["language"] = parsed.language
    return item


def _category_file(root: Path, category: str) -> Path:
    return root / "data" / "categories" / f"{slugify(category)}.json"


def _load_category_file(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise QuotationManagerError(f"Could not read {path.name}: {exc}") from exc
    if not isinstance(data, list):
        raise QuotationManagerError(f"{path.name} must contain a JSON array.")
    return [item for item in data if isinstance(item, dict)]


def bump_manifest_version(root: Path, bump: str) -> str:
    manifest_path = root / "manifest.json"
    manifest = load_manifest(root)
    current = str(manifest.get("content_version", "1.0.0"))
    updated = next_version(current, bump)
    manifest["content_version"] = updated
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return updated


def run_python_script(root: Path, script: str) -> GitResult:
    python = shutil.which("python") or shutil.which("python3")
    if not python:
        raise QuotationManagerError("Python executable could not be found.")
    return run_command([python, str(root / "scripts" / script)], cwd=root)


def save_preview(
    root: Path,
    preview: ImportPreview,
    *,
    version_bump: str = "patch",
) -> SaveResult:
    if not preview.accepted:
        raise QuotationManagerError("There are no new quotations to save.")

    target = _category_file(root, preview.category)
    created_category = not target.exists()
    target.parent.mkdir(parents=True, exist_ok=True)

    current = _load_category_file(target)
    current_normalized = {
        normalize_text(str(item.get("text", "")))
        for item in current
        if str(item.get("text", "")).strip()
    }

    inserted_items: list[dict[str, Any]] = []
    for parsed in preview.accepted:
        normalized = normalize_text(parsed.text)
        if normalized in current_normalized:
            continue
        inserted_items.append(_build_repo_item(parsed))
        current_normalized.add(normalized)

    if not inserted_items:
        raise QuotationManagerError("All quotations became duplicates before saving.")

    # Snapshot every generated file we may touch so a failed rebuild/validation can
    # restore the repository to its exact pre-save state.
    tracked_paths = [
        target,
        root / "manifest.json",
        root / "catalog.json",
        root / "data" / "all.json",
    ]
    backups: dict[Path, bytes | None] = {
        path: path.read_bytes() if path.exists() else None
        for path in tracked_paths
    }

    try:
        current.extend(inserted_items)
        target.write_text(
            json.dumps(current, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        version = bump_manifest_version(root, version_bump)

        rebuild = run_python_script(root, "rebuild_catalog.py")
        if not rebuild.ok:
            raise QuotationManagerError(f"Catalog rebuild failed:\n{rebuild.output}")

        validation = run_python_script(root, "validate.py")
        if not validation.ok:
            raise QuotationManagerError(
                f"Validation failed after saving:\n{validation.output}"
            )
    except Exception:
        for path, backup in backups.items():
            if backup is None:
                if path.exists():
                    path.unlink()
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(backup)
        raise

    return SaveResult(
        category=preview.category,
        file=target,
        inserted=len(inserted_items),
        skipped=preview.skipped_count + (len(preview.accepted) - len(inserted_items)),
        content_version=version,
        created_category=created_category,
    )


def build_prompt(
    *,
    category: str,
    count: int,
    language: str,
    tone: str,
    max_words: int,
    themes: str = "",
    extra_instructions: str = "",
) -> str:
    category = category.strip()
    language = language.strip() or "English"
    tone = tone.strip() or "Thoughtful"
    themes = themes.strip()
    extra_instructions = extra_instructions.strip()

    if not category:
        raise QuotationManagerError("Category is required.")
    if count < 1 or count > 100:
        raise QuotationManagerError("Quotation count must be between 1 and 100.")
    if max_words < 3 or max_words > 100:
        raise QuotationManagerError("Maximum words must be between 3 and 100.")

    optional = []
    if themes:
        optional.append(f"- Themes or focus areas: {themes}")
    if extra_instructions:
        optional.append(f"- Additional instructions: {extra_instructions}")

    optional_block = "\n".join(optional)

    return f"""Generate {count} ORIGINAL quotations for a public quotation dataset.

Category: {category}
Language: {language}
Tone: {tone}
Maximum length: {max_words} words per quotation.

Rules:
- Return ONLY valid JSON. Do not include Markdown fences or explanatory text.
- Return one JSON array.
- Every item must contain exactly these content fields: "text", "author", "language".
- Use original wording; do not copy famous quotations or closely paraphrase them.
- Do not imitate a named living or historical author.
- Do not invent attribution to a real person.
- Set "author" to an empty string unless I explicitly provide verified attribution.
- Set "language" to "{language}".
- Keep every quotation clearly relevant to the "{category}" category.
- Avoid duplicate ideas, duplicate openings, and near-duplicate wording.
- Avoid unsafe, hateful, sexually explicit, or targeted degrading content.
{optional_block}

Required output shape:
[
  {{
    "text": "Original quotation text",
    "author": "",
    "language": "{language}"
  }}
]

Return exactly {count} items.
""".strip()


def git_available() -> bool:
    return shutil.which("git") is not None


def run_command(args: Iterable[str], *, cwd: Path) -> GitResult:
    args = [str(a) for a in args]
    command = " ".join(args)
    try:
        completed = subprocess.run(
            args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return GitResult(False, command, "Command not found.", 127)
    output = (completed.stdout + completed.stderr).strip()
    return GitResult(completed.returncode == 0, command, output, completed.returncode)


def git_is_repository(root: Path) -> bool:
    if not git_available():
        return False
    result = run_command(["git", "rev-parse", "--is-inside-work-tree"], cwd=root)
    return result.ok and result.output.strip().endswith("true")


def git_current_branch(root: Path) -> str:
    result = run_command(["git", "branch", "--show-current"], cwd=root)
    return result.output.strip() if result.ok else ""


def git_remote_url(root: Path, remote: str = "origin") -> str:
    result = run_command(["git", "remote", "get-url", remote], cwd=root)
    return result.output.strip() if result.ok else ""


def git_status(root: Path) -> GitResult:
    return run_command(["git", "status", "--short"], cwd=root)


def git_pull(root: Path, remote: str = "origin") -> GitResult:
    branch = git_current_branch(root)
    if not branch:
        return GitResult(False, "git pull", "Could not determine the current branch.", 1)
    return run_command(["git", "pull", "--ff-only", remote, branch], cwd=root)


def git_commit_and_push(
    root: Path,
    *,
    message: str,
    remote: str = "origin",
) -> list[GitResult]:
    if not git_is_repository(root):
        return [
            GitResult(
                False,
                "git",
                "This folder is not a Git working tree. Clone the repository with Git before using Push.",
                1,
            )
        ]

    message = message.strip()
    if not message:
        return [GitResult(False, "git commit", "Commit message is required.", 1)]

    branch = git_current_branch(root)
    if not branch:
        return [GitResult(False, "git branch", "Could not determine the current branch.", 1)]

    results: list[GitResult] = []

    validation = run_python_script(root, "validate.py")
    results.append(validation)
    if not validation.ok:
        return results

    add = run_command(
        [
            "git",
            "add",
            "manifest.json",
            "catalog.json",
            "data/all.json",
            "data/categories",
        ],
        cwd=root,
    )
    results.append(add)
    if not add.ok:
        return results

    diff = run_command(["git", "diff", "--cached", "--quiet"], cwd=root)
    if diff.returncode == 0:
        results.append(
            GitResult(False, "git commit", "There are no quotation changes to commit.", 1)
        )
        return results
    if diff.returncode not in (0, 1):
        results.append(diff)
        return results

    commit = run_command(["git", "commit", "-m", message], cwd=root)
    results.append(commit)
    if not commit.ok:
        return results

    push = run_command(["git", "push", remote, branch], cwd=root)
    results.append(push)
    return results
