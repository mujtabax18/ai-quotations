# Contributing

1. Add quotations to an existing file in `data/categories/`, when possible.
2. Follow `templates/quotation.json`.
3. Use a globally unique `uid`.
4. Set AI-generated content to `"source": "ai"`.
5. Do not invent author attribution.
6. Run:

```bash
python scripts/rebuild_catalog.py
python scripts/validate.py
```

7. Commit the edited category file and regenerated indexes.
