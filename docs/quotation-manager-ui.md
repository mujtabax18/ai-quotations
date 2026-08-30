# AI Quotations Manager UI

The repository includes a native **Tkinter desktop application** for creating and
publishing AI-generated quotation packs without manually editing JSON files.

There is no Streamlit dependency, browser server, account prompt, or analytics prompt.

## What it does

The manager can:

- load the existing category catalog;
- build a strict prompt for ChatGPT or another AI system;
- create prompts for existing or new categories;
- support multiple languages, tones and length limits;
- copy prompts to the clipboard;
- paste AI JSON from the clipboard;
- accept plain JSON or fenced JSON output;
- remove duplicates already present anywhere in the repository;
- remove duplicate items inside the pasted batch;
- preview accepted quotations before writing;
- generate stable `uid` values and compatible numeric IDs;
- write the correct category JSON file;
- bump `manifest.json` content versions;
- rebuild `catalog.json` and `data/all.json`;
- run repository validation;
- roll back the save if rebuild or validation fails;
- show Git branch, origin and working-tree status;
- pull with `--ff-only`;
- commit quotation data and push the current branch to `origin`;
- display all repository categories and quotation counts.

The tool does **not** store a GitHub password or access token. Git operations use the
authentication already configured for the local `git` command.

## Requirements

- Python 3.10+
- Tk/Tkinter support
- Git, only if you want to use the built-in GitHub workflow
- a Git clone of the repository for pull/commit/push operations

Tkinter is included with standard Python installations on Windows and most macOS
installations. Some Linux distributions package Tk separately.

### Linux Tk packages

```bash
# Ubuntu / Debian
sudo apt install python3-tk

# Arch / CachyOS / Manjaro
sudo pacman -S tk

# Fedora
sudo dnf install python3-tkinter
```

## Quick setup

### Linux / macOS

```bash
git clone https://github.com/mujtabax18/ai-quotations.git
cd ai-quotations

./setup-ui.sh
source .venv/bin/activate
python run_manager.py
```

Manual setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
python run_manager.py
```

### Windows

```bat
git clone https://github.com/mujtabax18/ai-quotations.git
cd ai-quotations

setup-ui.bat
.venv\Scripts\activate
python run_manager.py
```

A normal desktop window opens. No browser is used.

## GitHub authentication

The Push action runs normal Git commands against the current clone:

```text
git add ...
git commit -m "..."
git push origin CURRENT_BRANCH
```

Configure Git authentication outside the app using your preferred method, such as an
SSH key, GitHub CLI, or your operating system's Git credential manager.

If someone does not have write permission to the repository, GitHub will reject their
push. They should use a fork or be added as a collaborator.

## Publishing workflow

1. Open **GitHub** in the manager and pull latest changes.
2. Open **Build Prompt** and choose or type a category.
3. Generate the prompt and copy it to your AI tool.
4. Paste the returned JSON into **Paste & Validate**.
5. Review new quotations and duplicate/invalid counts.
6. Open **Save**, choose the content-version bump, confirm publishing rights, and save.
7. Open **GitHub**, inspect status, enter a commit message, then validate/commit/push.

## AI output format

The UI deliberately asks the AI for only:

```json
[
  {
    "text": "Original quotation text",
    "author": "",
    "language": "English"
  }
]
```

Repository-specific fields (`uid`, integer `id`, timestamps, source, usage defaults,
style defaults and category) are added locally. This prevents an AI model from
inventing conflicting repository metadata.

## Duplicate handling

A quotation is considered a duplicate when its normalized text already exists in
`data/all.json`. Matching is case-insensitive and collapses repeated whitespace.

The manager also detects duplicate text within the pasted AI batch before saving.
