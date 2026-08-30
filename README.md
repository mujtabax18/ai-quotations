# AI Quotations Repository

A static GitHub-hosted quotation catalog for apps that need to discover categories
and download quotation packs on demand.

## Structure

```text
.
├── manifest.json
├── catalog.json
├── data/
│   ├── all.json
│   └── categories/
│       ├── anger-management.json
│       ├── personal-growth.json
│       ├── self-discipline.json
│       └── ...
├── schemas/
├── templates/
├── prompts/
├── scripts/
├── docs/
└── .github/workflows/
```

## App flow

Set one base URL:

```text
https://raw.githubusercontent.com/OWNER/REPOSITORY/main/
```

Then:

1. GET `manifest.json`.
2. If `content_version` changed, GET `catalog.json`.
3. Show `categories[].name`.
4. When a category is selected, append `categories[].file` to the base URL.
5. Download that JSON array.
6. Import the quotations into local storage.
7. Use `uid` as the stable remote identity.

Example:

```text
https://raw.githubusercontent.com/OWNER/REPOSITORY/main/catalog.json
https://raw.githubusercontent.com/OWNER/REPOSITORY/main/data/categories/wisdom.json
```

## Important database rule

The existing app export uses integer `id`. Do not use the repository integer `id`
as the local database primary key during sync.

Use `uid` to de-duplicate remote data and let the app/database assign its own local ID.

## Local-state fields

The current format contains:

- `is_favorite`
- `is_used`
- `usage_count`

They are kept in downloadable JSON for compatibility, but your app should preserve
its own local values when updating an already imported quotation.

## Adding AI-generated content

Use `templates/quotation.json`.

For generated content:

- set `source` to `ai`;
- use a unique `uid`;
- leave `author` empty unless attribution is verified;
- prefer an existing category;
- avoid duplicates and famous quotations copied verbatim.

After editing category files:

```bash
python scripts/rebuild_catalog.py
python scripts/validate.py
```

## Versioning

Use `manifest.json`:

- patch: corrections/small additions
- minor: new categories or content batches
- major: breaking schema changes

## Starter dataset

This repository starts with 178 quotations across 39 category labels from the supplied
application export.

## Licensing

Only publish text you have the right to redistribute. See `DATA_LICENSE.md`.
