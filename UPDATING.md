# Updating the Backlink Resources Directory

The directory on the Resources page is generated from an Excel workbook.
To update it with a new file, you do **not** need to edit any website code.

## What you need

- Python 3 with `openpyxl` installed (`pip install openpyxl`)
- Your new Excel file in the same loose format: one URL per cell
  (column A of each sheet). A label before the URL is fine, e.g.
  `freead1.net ad — https://freead1.net/ad/...`.

## Steps

1. **Copy your new Excel file** somewhere convenient, e.g. next to the repo:
   `cp ~/Downloads/Backlinks_new.xlsx .`

2. **Regenerate the data files:**
   ```bash
   python3 update_resources.py Backlinks_new.xlsx
   ```
   This rewrites `assets/data/resources.json` and `data-quality-notes.md`.
   Read `data-quality-notes.md` afterwards — it lists how many URLs were
   imported, how many duplicates were removed, and everything excluded
   (with reasons).

3. **Check the result locally (optional but recommended):**
   ```bash
   python3 -m http.server 8000
   # open http://localhost:8000/resources.html and try the search/filters
   ```

4. **Commit and push:**
   ```bash
   git add assets/data/resources.json data-quality-notes.md
   git commit -m "Update backlink resources"
   git push origin main
   ```

5. **Wait 1–2 minutes.** GitHub Pages redeploys automatically from the
   `main` branch. Open https://backlinkforge.github.io/resources.html
   and confirm the new resources appear.

## Notes

- The script de-duplicates exact URLs, validates them, and categorises
  them from evidence in the URL only. It never invents authority scores
  or metrics.
- Entries that are not usable resources (search-engine pages, AI chat
  shares, opaque short links, non-URL header text) are excluded and listed
  in `data-quality-notes.md` — nothing is silently rewritten.
- The sitemap does not need to change when only the directory data changes.
