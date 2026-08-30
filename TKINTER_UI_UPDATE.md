# Tkinter Quotation Manager Update

This update replaces the previous Streamlit interface with a native Python/Tkinter
desktop application.

## Changed

- Removed Streamlit completely
- Removed browser-based local server
- Removed Streamlit onboarding/email prompt
- Removed third-party Python UI dependencies
- Added native Tkinter desktop window
- Added Build Prompt tab
- Added Paste & Validate tab
- Added accepted quotation preview table
- Added existing/batch/invalid duplicate counters
- Added Save tab with semantic version controls
- Added publishing-rights confirmation
- Added GitHub tab with branch/origin/status
- Added safe `git pull --ff-only`
- Added validate + commit + push workflow
- Added Repository tab with category/count/file table
- Added clipboard copy/paste helpers
- Preserved rollback-safe save/rebuild/validation logic

## Run

```bash
./setup-ui.sh
source .venv/bin/activate
python run_manager.py
```

No `pip install streamlit` step is required.
