# BacklinkForge — backlink building services website

Professional static website for BacklinkForge (backlink-building / off-page SEO services),
hosted on GitHub Pages at https://backlinkforge.github.io/

## Structure

- `index.html` — homepage (hero, services overview, curated resources, FAQ)
- `about.html` — about the service and working principles
- `services.html` — the seven services in detail
- `resources.html` — searchable, filterable backlink resources directory
- `contact.html` — mailto contact form (no backend)
- `privacy.html`, `terms.html` — policy pages
- `assets/css/style.css`, `assets/js/main.js`, `assets/js/resources.js`
- `assets/data/resources.json` — the directory data (generated)
- `sitemap.xml`, `robots.txt`
- `update_resources.py` — regenerates `resources.json` + `data-quality-notes.md`
  from a replacement Excel workbook
- `UPDATING.md` — plain-language update instructions
- `data-quality-notes.md` — import counts, categories, exclusions

## Local preview

```bash
cd /path/to/repo
python3 -m http.server 8000
# open http://localhost:8000/
```

## Deploy / update

Push to the `main` branch — GitHub Pages redeploys automatically.

```bash
git add -A
git commit -m "Update site"
git push origin main
```

## Contact email placeholder

`contact.html` uses `hello@example.com` (marked with `<!-- TODO -->` comments).
Replace it with the real address in both the `data-email` attribute and the
`mailto:` link before launch.
