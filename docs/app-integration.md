# App Integration

## Base URL

```dart
const quotationRepoBaseUrl =
    'https://raw.githubusercontent.com/OWNER/REPOSITORY/main/';
```

## Fetch manifest

```text
GET {baseUrl}manifest.json
```

Use `content_version` for cache invalidation.

## Fetch categories

```text
GET {baseUrl}catalog.json
```

Category example:

```json
{
  "id": "wisdom",
  "name": "Wisdom",
  "count": 34,
  "file": "data/categories/wisdom.json",
  "sha256": "..."
}
```

## Fetch a category

```text
GET {baseUrl}data/categories/wisdom.json
```

The response is directly importable as a JSON array.

## Import rules

- Use `uid` as the remote unique key.
- Keep local favorites and local usage history.
- Do not treat the remote integer `id` as the local DB primary key.
- Insert/update inside a database transaction.
- Cache the last successful `content_version`.
- Never delete local content only because a network request failed.

## Offline behavior

After a category is downloaded, keep it in local storage so it remains available
without internet access.
