from __future__ import annotations

import json
import platform
import subprocess
import sys
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from tools.quotation_manager.core import (
    ImportPreview,
    QuotationManagerError,
    SaveResult,
    build_prompt,
    git_available,
    git_commit_and_push,
    git_current_branch,
    git_is_repository,
    git_pull,
    git_remote_url,
    git_status,
    list_categories,
    load_catalog,
    load_manifest,
    preview_import,
    repo_root_from,
    save_preview,
)


ROOT = repo_root_from(Path(__file__))
REPOSITORY_URL = "https://github.com/mujtabax18/ai-quotations"


class QuotationManagerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("AI Quotations Manager")
        self.geometry("1120x760")
        self.minsize(940, 640)

        self.preview: ImportPreview | None = None
        self.last_save: SaveResult | None = None
        self.categories: list[dict] = []
        self.category_names: list[str] = []

        self._configure_style()
        self._build_ui()
        self.refresh_repository_data()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------
    def _configure_style(self) -> None:
        style = ttk.Style(self)
        try:
            if platform.system() == "Windows":
                style.theme_use("vista")
            elif "clam" in style.theme_names():
                style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("Title.TLabel", font=("TkDefaultFont", 18, "bold"))
        style.configure("Heading.TLabel", font=("TkDefaultFont", 12, "bold"))
        style.configure("MetricValue.TLabel", font=("TkDefaultFont", 16, "bold"))
        style.configure("Muted.TLabel", foreground="#666666")
        style.configure("Primary.TButton", padding=(14, 8))
        style.configure("Card.TFrame", relief="solid", borderwidth=1)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=14)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x")

        title_block = ttk.Frame(header)
        title_block.pack(side="left", fill="x", expand=True)
        ttk.Label(title_block, text="AI Quotations Manager", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            title_block,
            text=(
                "Generate prompts, validate AI JSON, save quotation packs, rebuild the catalog, "
                "and push using your existing Git authentication."
            ),
            style="Muted.TLabel",
            wraplength=780,
        ).pack(anchor="w", pady=(2, 0))

        ttk.Button(header, text="Open GitHub", command=self._open_repository).pack(side="right", padx=(10, 0))

        metrics = ttk.Frame(outer)
        metrics.pack(fill="x", pady=(14, 10))
        self.metric_quotes = self._metric(metrics, "Quotations")
        self.metric_categories = self._metric(metrics, "Categories")
        self.metric_version = self._metric(metrics, "Content version")
        self.metric_updated = self._metric(metrics, "Updated")

        self.notebook = ttk.Notebook(outer)
        self.notebook.pack(fill="both", expand=True)

        self.prompt_tab = ttk.Frame(self.notebook, padding=14)
        self.validate_tab = ttk.Frame(self.notebook, padding=14)
        self.save_tab = ttk.Frame(self.notebook, padding=14)
        self.git_tab = ttk.Frame(self.notebook, padding=14)
        self.repository_tab = ttk.Frame(self.notebook, padding=14)

        self.notebook.add(self.prompt_tab, text="1 · Build Prompt")
        self.notebook.add(self.validate_tab, text="2 · Paste & Validate")
        self.notebook.add(self.save_tab, text="3 · Save")
        self.notebook.add(self.git_tab, text="4 · GitHub")
        self.notebook.add(self.repository_tab, text="Repository")

        self._build_prompt_tab()
        self._build_validate_tab()
        self._build_save_tab()
        self._build_git_tab()
        self._build_repository_tab()

        self.status_var = tk.StringVar(value="Ready")
        ttk.Separator(outer).pack(fill="x", pady=(8, 4))
        ttk.Label(outer, textvariable=self.status_var, style="Muted.TLabel").pack(anchor="w")

    def _metric(self, parent: ttk.Frame, title: str) -> tk.StringVar:
        frame = ttk.Frame(parent, padding=10, style="Card.TFrame")
        frame.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Label(frame, text=title, style="Muted.TLabel").pack(anchor="w")
        value = tk.StringVar(value="—")
        ttk.Label(frame, textvariable=value, style="MetricValue.TLabel").pack(anchor="w", pady=(2, 0))
        return value

    def _build_prompt_tab(self) -> None:
        ttk.Label(self.prompt_tab, text="Build an AI quotation prompt", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(
            self.prompt_tab,
            text=(
                "Choose an existing category or type a new category. The AI is only asked for content fields; "
                "IDs, timestamps, repository fields, and defaults are added locally when saving."
            ),
            style="Muted.TLabel",
            wraplength=950,
        ).pack(anchor="w", pady=(4, 12))

        form = ttk.Frame(self.prompt_tab)
        form.pack(fill="x")
        for col in range(4):
            form.columnconfigure(col, weight=1)

        self.prompt_category_var = tk.StringVar()
        self.prompt_count_var = tk.IntVar(value=10)
        self.prompt_language_var = tk.StringVar(value="English")
        self.prompt_tone_var = tk.StringVar(value="Thoughtful")
        self.prompt_max_words_var = tk.IntVar(value=24)
        self.prompt_themes_var = tk.StringVar()

        ttk.Label(form, text="Category").grid(row=0, column=0, sticky="w")
        ttk.Label(form, text="Count").grid(row=0, column=1, sticky="w", padx=(10, 0))
        ttk.Label(form, text="Language").grid(row=0, column=2, sticky="w", padx=(10, 0))
        ttk.Label(form, text="Tone").grid(row=0, column=3, sticky="w", padx=(10, 0))

        self.prompt_category_combo = ttk.Combobox(
            form,
            textvariable=self.prompt_category_var,
            state="normal",
        )
        self.prompt_category_combo.grid(row=1, column=0, sticky="ew", pady=(3, 10))

        ttk.Spinbox(
            form,
            from_=1,
            to=100,
            textvariable=self.prompt_count_var,
        ).grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=(3, 10))

        ttk.Combobox(
            form,
            textvariable=self.prompt_language_var,
            values=["English", "Urdu", "Roman Urdu", "Arabic", "Spanish", "French", "German"],
            state="normal",
        ).grid(row=1, column=2, sticky="ew", padx=(10, 0), pady=(3, 10))

        ttk.Combobox(
            form,
            textvariable=self.prompt_tone_var,
            values=["Thoughtful", "Uplifting", "Powerful", "Calm", "Direct", "Reflective", "Warm"],
            state="normal",
        ).grid(row=1, column=3, sticky="ew", padx=(10, 0), pady=(3, 10))

        ttk.Label(form, text="Maximum words").grid(row=2, column=0, sticky="w")
        ttk.Label(form, text="Themes / focus areas").grid(row=2, column=1, columnspan=3, sticky="w", padx=(10, 0))

        ttk.Spinbox(
            form,
            from_=3,
            to=100,
            textvariable=self.prompt_max_words_var,
        ).grid(row=3, column=0, sticky="ew", pady=(3, 10))
        ttk.Entry(form, textvariable=self.prompt_themes_var).grid(
            row=3,
            column=1,
            columnspan=3,
            sticky="ew",
            padx=(10, 0),
            pady=(3, 10),
        )

        ttk.Label(self.prompt_tab, text="Extra instructions").pack(anchor="w")
        self.prompt_extra_text = ScrolledText(self.prompt_tab, height=4, wrap="word")
        self.prompt_extra_text.pack(fill="x", pady=(3, 10))

        buttons = ttk.Frame(self.prompt_tab)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Generate Prompt", style="Primary.TButton", command=self.generate_prompt).pack(side="left")
        ttk.Button(buttons, text="Copy Prompt", command=self.copy_prompt).pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="Use Category in Validate Tab", command=self._send_category_to_validate).pack(side="left", padx=(8, 0))

        ttk.Label(self.prompt_tab, text="Prompt", style="Heading.TLabel").pack(anchor="w", pady=(14, 4))
        self.prompt_output = ScrolledText(self.prompt_tab, height=15, wrap="word")
        self.prompt_output.pack(fill="both", expand=True)

    def _build_validate_tab(self) -> None:
        ttk.Label(self.validate_tab, text="Paste and validate AI output", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(
            self.validate_tab,
            text="Paste the JSON returned by the AI. Markdown JSON fences are accepted too.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(4, 10))

        category_row = ttk.Frame(self.validate_tab)
        category_row.pack(fill="x")
        ttk.Label(category_row, text="Category to save into").pack(side="left")
        self.validation_category_var = tk.StringVar()
        self.validation_category_combo = ttk.Combobox(
            category_row,
            textvariable=self.validation_category_var,
            state="normal",
            width=38,
        )
        self.validation_category_combo.pack(side="left", padx=(10, 0))
        ttk.Button(category_row, text="Paste Clipboard", command=self.paste_json_from_clipboard).pack(side="right")

        self.raw_json_text = ScrolledText(self.validate_tab, height=16, wrap="none")
        self.raw_json_text.pack(fill="both", expand=True, pady=(10, 8))

        button_row = ttk.Frame(self.validate_tab)
        button_row.pack(fill="x")
        ttk.Button(button_row, text="Validate & Preview", style="Primary.TButton", command=self.validate_json).pack(side="left")
        ttk.Button(button_row, text="Clear", command=self.clear_validation).pack(side="left", padx=(8, 0))

        stats = ttk.Frame(self.validate_tab)
        stats.pack(fill="x", pady=(10, 8))
        self.preview_new_var = tk.StringVar(value="New: 0")
        self.preview_existing_var = tk.StringVar(value="Existing duplicates: 0")
        self.preview_batch_var = tk.StringVar(value="Batch duplicates: 0")
        self.preview_invalid_var = tk.StringVar(value="Invalid: 0")
        for var in (
            self.preview_new_var,
            self.preview_existing_var,
            self.preview_batch_var,
            self.preview_invalid_var,
        ):
            ttk.Label(stats, textvariable=var).pack(side="left", padx=(0, 18))

        columns = ("text", "author", "language")
        self.preview_tree = ttk.Treeview(self.validate_tab, columns=columns, show="headings", height=8)
        self.preview_tree.heading("text", text="Quotation")
        self.preview_tree.heading("author", text="Author")
        self.preview_tree.heading("language", text="Language")
        self.preview_tree.column("text", width=650, anchor="w")
        self.preview_tree.column("author", width=150, anchor="w")
        self.preview_tree.column("language", width=110, anchor="w")
        self.preview_tree.pack(fill="both", expand=True)

    def _build_save_tab(self) -> None:
        ttk.Label(self.save_tab, text="Save validated quotations", style="Heading.TLabel").pack(anchor="w")
        self.save_info_var = tk.StringVar(value="Validate AI output first.")
        ttk.Label(self.save_tab, textvariable=self.save_info_var, wraplength=900).pack(anchor="w", pady=(6, 16))

        options = ttk.Frame(self.save_tab)
        options.pack(fill="x")

        ttk.Label(options, text="Content version bump").grid(row=0, column=0, sticky="w")
        self.version_bump_var = tk.StringVar(value="patch")
        ttk.Combobox(
            options,
            textvariable=self.version_bump_var,
            values=["patch", "minor", "major", "none"],
            state="readonly",
            width=18,
        ).grid(row=1, column=0, sticky="w", pady=(4, 12))

        self.publish_confirm_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options,
            text="I reviewed these quotations and have the right to publish them.",
            variable=self.publish_confirm_var,
        ).grid(row=2, column=0, sticky="w", pady=(2, 12))

        ttk.Button(options, text="Save to Repository", style="Primary.TButton", command=self.save_validated).grid(row=3, column=0, sticky="w")

        ttk.Separator(self.save_tab).pack(fill="x", pady=20)
        ttk.Label(self.save_tab, text="Last save", style="Heading.TLabel").pack(anchor="w")
        self.last_save_var = tk.StringVar(value="No quotations saved in this session yet.")
        ttk.Label(self.save_tab, textvariable=self.last_save_var, wraplength=900).pack(anchor="w", pady=(5, 0))

    def _build_git_tab(self) -> None:
        ttk.Label(self.git_tab, text="Commit and push to GitHub", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(
            self.git_tab,
            text=(
                "No GitHub password or token is stored here. Git uses the authentication already configured "
                "on this computer, such as SSH, Git Credential Manager, or GitHub CLI credentials."
            ),
            style="Muted.TLabel",
            wraplength=920,
        ).pack(anchor="w", pady=(4, 12))

        repo_info = ttk.Frame(self.git_tab)
        repo_info.pack(fill="x")
        self.git_branch_var = tk.StringVar(value="—")
        self.git_origin_var = tk.StringVar(value="—")
        ttk.Label(repo_info, text="Branch:").grid(row=0, column=0, sticky="w")
        ttk.Label(repo_info, textvariable=self.git_branch_var).grid(row=0, column=1, sticky="w", padx=(6, 24))
        ttk.Label(repo_info, text="Origin:").grid(row=0, column=2, sticky="w")
        ttk.Label(repo_info, textvariable=self.git_origin_var).grid(row=0, column=3, sticky="w", padx=(6, 0))

        buttons = ttk.Frame(self.git_tab)
        buttons.pack(fill="x", pady=(10, 8))
        ttk.Button(buttons, text="Refresh Status", command=self.refresh_git_status).pack(side="left")
        ttk.Button(buttons, text="Pull Latest (FF only)", command=self.pull_latest).pack(side="left", padx=(8, 0))

        ttk.Label(self.git_tab, text="Git status").pack(anchor="w")
        self.git_status_text = ScrolledText(self.git_tab, height=13, wrap="none", state="disabled")
        self.git_status_text.pack(fill="both", expand=True, pady=(4, 10))

        commit_row = ttk.Frame(self.git_tab)
        commit_row.pack(fill="x")
        ttk.Label(commit_row, text="Commit message").pack(side="left")
        self.commit_message_var = tk.StringVar(value="Add AI-generated quotations")
        ttk.Entry(commit_row, textvariable=self.commit_message_var).pack(side="left", fill="x", expand=True, padx=(10, 0))

        self.push_confirm_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            self.git_tab,
            text="I want to commit quotation changes and push the current branch to origin.",
            variable=self.push_confirm_var,
        ).pack(anchor="w", pady=(10, 8))

        ttk.Button(self.git_tab, text="Validate, Commit & Push", style="Primary.TButton", command=self.commit_and_push).pack(anchor="w")

    def _build_repository_tab(self) -> None:
        top = ttk.Frame(self.repository_tab)
        top.pack(fill="x")
        ttk.Label(top, text="Repository categories", style="Heading.TLabel").pack(side="left")
        ttk.Button(top, text="Refresh", command=self.refresh_repository_data).pack(side="right")

        columns = ("name", "count", "file")
        self.category_tree = ttk.Treeview(self.repository_tab, columns=columns, show="headings")
        self.category_tree.heading("name", text="Category")
        self.category_tree.heading("count", text="Count")
        self.category_tree.heading("file", text="File")
        self.category_tree.column("name", width=260, anchor="w")
        self.category_tree.column("count", width=80, anchor="center")
        self.category_tree.column("file", width=620, anchor="w")
        self.category_tree.pack(fill="both", expand=True, pady=(10, 0))

    # ------------------------------------------------------------------
    # Repository refresh
    # ------------------------------------------------------------------
    def refresh_repository_data(self) -> None:
        try:
            catalog = load_catalog(ROOT)
            manifest = load_manifest(ROOT)
            self.categories = list_categories(ROOT)
            self.category_names = [
                str(item.get("name", "")).strip()
                for item in self.categories
                if str(item.get("name", "")).strip()
            ]

            self.metric_quotes.set(str(catalog.get("total_quotations", 0)))
            self.metric_categories.set(str(catalog.get("total_categories", 0)))
            self.metric_version.set(str(manifest.get("content_version", "—")))
            self.metric_updated.set(str(catalog.get("updated_at", "—")).replace("T", " ").replace("Z", " UTC"))

            self.prompt_category_combo["values"] = self.category_names
            self.validation_category_combo["values"] = self.category_names
            if not self.prompt_category_var.get() and self.category_names:
                self.prompt_category_var.set(self.category_names[0])
            if not self.validation_category_var.get() and self.category_names:
                self.validation_category_var.set(self.category_names[0])

            for row in self.category_tree.get_children():
                self.category_tree.delete(row)
            for item in self.categories:
                self.category_tree.insert(
                    "",
                    "end",
                    values=(item.get("name", ""), item.get("count", 0), item.get("file", "")),
                )

            self.refresh_git_status(silent=True)
            self.status_var.set("Repository data refreshed.")
        except Exception as exc:
            self._show_error(exc)

    # ------------------------------------------------------------------
    # Prompt actions
    # ------------------------------------------------------------------
    def generate_prompt(self) -> None:
        try:
            prompt = build_prompt(
                category=self.prompt_category_var.get(),
                count=int(self.prompt_count_var.get()),
                language=self.prompt_language_var.get(),
                tone=self.prompt_tone_var.get(),
                max_words=int(self.prompt_max_words_var.get()),
                themes=self.prompt_themes_var.get(),
                extra_instructions=self.prompt_extra_text.get("1.0", "end").strip(),
            )
            self.prompt_output.delete("1.0", "end")
            self.prompt_output.insert("1.0", prompt)
            self.validation_category_var.set(self.prompt_category_var.get().strip())
            self.status_var.set("Prompt generated. Copy it into your AI tool.")
        except Exception as exc:
            self._show_error(exc)

    def copy_prompt(self) -> None:
        prompt = self.prompt_output.get("1.0", "end").strip()
        if not prompt:
            messagebox.showinfo("No prompt", "Generate a prompt first.", parent=self)
            return
        self.clipboard_clear()
        self.clipboard_append(prompt)
        self.update()
        self.status_var.set("Prompt copied to clipboard.")

    def _send_category_to_validate(self) -> None:
        category = self.prompt_category_var.get().strip()
        if category:
            self.validation_category_var.set(category)
        self.notebook.select(self.validate_tab)

    # ------------------------------------------------------------------
    # Validation actions
    # ------------------------------------------------------------------
    def paste_json_from_clipboard(self) -> None:
        try:
            value = self.clipboard_get()
        except tk.TclError:
            messagebox.showinfo("Clipboard", "Clipboard does not contain text.", parent=self)
            return
        self.raw_json_text.delete("1.0", "end")
        self.raw_json_text.insert("1.0", value)

    def validate_json(self) -> None:
        try:
            preview = preview_import(
                ROOT,
                self.raw_json_text.get("1.0", "end"),
                self.validation_category_var.get(),
            )
            self.preview = preview
            self.last_save = None
            self._render_preview(preview)
            self._update_save_tab(preview)
            self.status_var.set(
                f"Validation complete: {len(preview.accepted)} new, {preview.skipped_count} skipped."
            )
        except Exception as exc:
            self.preview = None
            self._render_preview(None)
            self._update_save_tab(None)
            self._show_error(exc)

    def clear_validation(self) -> None:
        self.raw_json_text.delete("1.0", "end")
        self.preview = None
        self._render_preview(None)
        self._update_save_tab(None)
        self.status_var.set("Validation input cleared.")

    def _render_preview(self, preview: ImportPreview | None) -> None:
        for row in self.preview_tree.get_children():
            self.preview_tree.delete(row)

        if preview is None:
            self.preview_new_var.set("New: 0")
            self.preview_existing_var.set("Existing duplicates: 0")
            self.preview_batch_var.set("Batch duplicates: 0")
            self.preview_invalid_var.set("Invalid: 0")
            return

        self.preview_new_var.set(f"New: {len(preview.accepted)}")
        self.preview_existing_var.set(f"Existing duplicates: {len(preview.duplicate_existing)}")
        self.preview_batch_var.set(f"Batch duplicates: {len(preview.duplicate_batch)}")
        self.preview_invalid_var.set(f"Invalid: {len(preview.invalid)}")

        for item in preview.accepted:
            self.preview_tree.insert("", "end", values=(item.text, item.author, item.language))

    def _update_save_tab(self, preview: ImportPreview | None) -> None:
        self.publish_confirm_var.set(False)
        if preview is None:
            self.save_info_var.set("Validate AI output first.")
            return

        existing_slugs = {str(item.get("id", "")) for item in self.categories}
        is_new_category = preview.category_slug not in existing_slugs
        if is_new_category:
            self.version_bump_var.set("minor")
            category_note = "This creates a new category; a minor version bump is recommended."
        else:
            self.version_bump_var.set("patch")
            category_note = "This updates an existing category; a patch version bump is normally appropriate."

        self.save_info_var.set(
            f"Category: {preview.category}\n"
            f"Target: data/categories/{preview.category_slug}.json\n"
            f"New quotations: {len(preview.accepted)}\n"
            f"Skipped during validation: {preview.skipped_count}\n\n"
            f"{category_note}"
        )

    # ------------------------------------------------------------------
    # Save actions
    # ------------------------------------------------------------------
    def save_validated(self) -> None:
        if self.preview is None:
            messagebox.showinfo("Nothing to save", "Validate AI output first.", parent=self)
            return
        if not self.preview.accepted:
            messagebox.showinfo("Nothing to save", "There are no new quotations in the validated batch.", parent=self)
            return
        if not self.publish_confirm_var.get():
            messagebox.showwarning(
                "Confirmation required",
                "Confirm that you reviewed the quotations and have the right to publish them.",
                parent=self,
            )
            return

        self.status_var.set("Saving quotations, rebuilding catalog, and validating repository…")
        self.update_idletasks()

        try:
            result = save_preview(
                ROOT,
                self.preview,
                version_bump=self.version_bump_var.get(),
            )
            self.last_save = result
            self.preview = None
            self.last_save_var.set(
                f"Saved {result.inserted} quotation(s) to {result.file.relative_to(ROOT)}. "
                f"Skipped {result.skipped}. Content version: {result.content_version}."
            )
            self._render_preview(None)
            self._update_save_tab(None)
            self.refresh_repository_data()
            self.refresh_git_status(silent=True)
            self.status_var.set("Quotations saved successfully.")
            messagebox.showinfo(
                "Saved",
                f"Saved {result.inserted} quotation(s).\n\nContent version: {result.content_version}",
                parent=self,
            )
        except Exception as exc:
            self._show_error(exc)

    # ------------------------------------------------------------------
    # Git actions
    # ------------------------------------------------------------------
    def refresh_git_status(self, silent: bool = False) -> None:
        if not git_available():
            self.git_branch_var.set("Git not installed")
            self.git_origin_var.set("—")
            self._set_git_status("Git is not installed or is not available on PATH.")
            if not silent:
                self.status_var.set("Git is unavailable.")
            return

        if not git_is_repository(ROOT):
            self.git_branch_var.set("Not a Git repository")
            self.git_origin_var.set("—")
            self._set_git_status(
                "This folder is not a Git working tree. Clone the repository with Git and run the manager from that clone.\n\n"
                f"git clone {REPOSITORY_URL}.git\ncd ai-quotations"
            )
            if not silent:
                self.status_var.set("Current folder is not a Git working tree.")
            return

        self.git_branch_var.set(git_current_branch(ROOT) or "—")
        self.git_origin_var.set(git_remote_url(ROOT) or "—")
        result = git_status(ROOT)
        self._set_git_status(result.output if result.output else "Working tree clean.")
        if not silent:
            self.status_var.set("Git status refreshed.")

    def pull_latest(self) -> None:
        if not git_is_repository(ROOT):
            messagebox.showwarning("Git", "This folder is not a Git working tree.", parent=self)
            return

        self.status_var.set("Pulling latest changes…")
        self.update_idletasks()
        result = git_pull(ROOT)
        self._set_git_status(result.output or ("Pull completed." if result.ok else "Git pull failed."))
        if result.ok:
            self.refresh_repository_data()
            messagebox.showinfo("Git pull", result.output or "Repository is up to date.", parent=self)
        else:
            messagebox.showerror("Git pull failed", result.output or "Git pull failed.", parent=self)
        self.status_var.set("Git pull finished.")

    def commit_and_push(self) -> None:
        if not self.push_confirm_var.get():
            messagebox.showwarning("Confirmation required", "Confirm the push action first.", parent=self)
            return

        message = self.commit_message_var.get().strip()
        if not message:
            messagebox.showwarning("Commit message", "Enter a commit message.", parent=self)
            return

        if not messagebox.askyesno(
            "Commit and push",
            "Validate quotation data, commit quotation changes, and push the current branch to origin?",
            parent=self,
        ):
            return

        self.status_var.set("Validating, committing, and pushing…")
        self.update_idletasks()
        results = git_commit_and_push(ROOT, message=message)
        output_lines: list[str] = []
        all_ok = True
        for result in results:
            output_lines.append(f"$ {result.command}\n{result.output or '(no output)'}")
            if not result.ok:
                all_ok = False
                break

        combined = "\n\n".join(output_lines)
        self._set_git_status(combined)
        self.refresh_repository_data()
        self.push_confirm_var.set(False)

        if all_ok:
            messagebox.showinfo("GitHub", "Quotation changes were committed and pushed successfully.", parent=self)
            self.status_var.set("Changes pushed successfully.")
        else:
            messagebox.showerror("GitHub", combined or "Commit/push failed.", parent=self)
            self.status_var.set("Commit/push failed. See Git status output.")

    def _set_git_status(self, value: str) -> None:
        self.git_status_text.configure(state="normal")
        self.git_status_text.delete("1.0", "end")
        self.git_status_text.insert("1.0", value)
        self.git_status_text.configure(state="disabled")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _open_repository(self) -> None:
        webbrowser.open(REPOSITORY_URL)

    def _show_error(self, exc: Exception) -> None:
        message = str(exc)
        self.status_var.set(message)
        messagebox.showerror("AI Quotations Manager", message, parent=self)


def ensure_tkinter_available() -> None:
    """Kept for a clear entry-point contract and future checks."""
    return None


def main() -> int:
    try:
        app = QuotationManagerApp()
        app.mainloop()
        return 0
    except QuotationManagerError as exc:
        try:
            messagebox.showerror("AI Quotations Manager", str(exc))
        except Exception:
            print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
