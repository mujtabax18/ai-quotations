# AI Prompt for New Quotations

Generate original quotations for the requested category.

Requirements:

- Return JSON only.
- Return a JSON array.
- Do not copy or imitate known quotations.
- Do not attribute text to a real person.
- Use original wording.
- Use `source: "ai"`.
- Use `author: ""`.
- Use a unique `uid`.
- Keep these defaults:
  - `is_favorite`: 0
  - `is_used`: 0
  - `usage_count`: 0
  - `background_style`: "sunrise"
  - `text_align`: "center"
  - `font_size`: 30.0
  - `show_author`: 1

Follow `templates/quotation.json`.
