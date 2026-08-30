# Python Quotation Manager Update

This release adds a local Python UI for managing AI-generated quotation packs.

## Added

- Streamlit-based quotation manager
- Python virtual-environment setup scripts for Linux/macOS and Windows
- Existing-category selection
- New-category creation
- AI prompt builder
- Language, tone, count and length controls
- Strict JSON output format for AI prompts
- Pasted AI response parsing
- Support for plain JSON and fenced JSON
- Global duplicate detection against `data/all.json`
- Duplicate detection inside each generated batch
- Preview before saving
- Automatic repository-compatible `uid` and numeric ID generation
- Automatic timestamps and quotation defaults
- Automatic category JSON creation/update
- Semantic content version bumping
- Automatic catalog rebuild
- Automatic repository validation
- Transaction-style rollback if rebuild or validation fails
- Git status display
- Safe `git pull --ff-only`
- Commit and push using existing local Git authentication
- Core unit tests and GitHub Actions validation

## Security

The manager does not ask for or store GitHub passwords or personal access tokens.
Push operations use the authentication already configured for the local Git client.

## Run

```bash
python -m venv .venv
# activate .venv
python -m pip install -r requirements-ui.txt
python run_manager.py
```

See `docs/quotation-manager-ui.md` for the full workflow.
