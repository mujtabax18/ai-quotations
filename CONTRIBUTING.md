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


## UI workflow

Contributors can use the Python quotation manager instead of editing JSON manually:

```bash
python -m venv .venv
# activate the environment
python -m pip install -r requirements-ui.txt
python run_manager.py
```

Use the manager to build the AI prompt, paste/validate the response, save it, and run
the built-in Git workflow. GitHub credentials are handled by the local Git
configuration, not by this repository tool.
