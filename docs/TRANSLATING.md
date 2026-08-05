# Translating Leafkit (community)

English is the source language. Other languages are welcome as community contributions.

## How it works

1. UI strings in code use `_("English text")`.
2. Catalogs live in [`locales/`](../locales/):
   - `en.json` — complete English map (`"English": "English"`)
   - `fr.json`, `de.json`, … — only **translated** strings (English key → local text)
3. Language is chosen automatically from:
   1. Environment variable **`LEAFKIT_LANG`** (e.g. `fr`, `de`, `es`)
   2. OS / `LANG` locale
   3. Fallback: **`en`**

Missing keys always fall back to English.

## Add a language

1. Copy the template:
   ```text
   locales/en.json  →  locales/XX.json
   ```
   Use a short language code: `fr`, `de`, `es`, `pt`, `ja`, …

2. Translate the **values** only. Keep the **keys** (English) unchanged:

   ```json
   {
     "Merge PDFs": "Fusionner les PDF",
     "Add PDFs…": "Ajouter des PDF…",
     "About": "À propos"
   }
   ```

3. You do **not** need every key. Omit or leave empty anything unfinished — English will show.

4. Test locally (Windows PowerShell):
   ```powershell
   $env:LEAFKIT_LANG = "fr"
   pythonw run.py
   ```

5. Open a pull request with `locales/XX.json` only (unless you also fix a string in code).

## Optional: regenerate English catalog

After adding new `_("...")` strings in code:

```powershell
python scripts/generate_en_locale.py
```

Then re-wrap new `text="..."` attributes if needed:

```powershell
python scripts/apply_i18n_wrappers.py
```

## Guidelines

- Prefer clear, short UI phrases.
- Keep keyboard shortcuts as-is (`Ctrl+O`, `F1`, …).
- Do not translate file formats (`PDF`) or product name **Leafkit** unless a locale strongly expects it.
- Tab names (`Merge`, `Share`, …) are currently English API keys; translating them needs a code change — ask maintainers first.
- No machine-only dumps without human review, please.

## Maintainers

- New UI text in Python should use `_("...")`.
- Ship `locales/` inside the Windows build (`--add-data locales;locales`).
- Do not block releases on incomplete translations.

Thank you for helping Leafkit stay free for everyone, in every language.
