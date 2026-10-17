#!/usr/bin/env python3
"""
update_resources.py -- Rebuild the backlink resources directory from an Excel file.

Usage:
    python3 update_resources.py path/to/Backlinks_2026.xlsx

Reads every sheet/row of the workbook, extracts URLs, de-duplicates, validates,
categorises (from evidence in the URL/name only -- no invented metrics), and writes:
    assets/data/resources.json
    data-quality-notes.md
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse, parse_qsl, urlencode

import openpyxl

REPO_ROOT = Path(__file__).resolve().parent
RESOURCES_JSON = REPO_ROOT / "assets" / "data" / "resources.json"
QUALITY_NOTES = REPO_ROOT / "data-quality-notes.md"

URL_RE = re.compile(r"https?://[^\s'\"<>]+", re.I)
LABEL_URL_RE = re.compile(r"^(.*?)\s+[—–-]\s+(https?://\S+)\s*$")
PROFILE_RE = re.compile(r"/(?:profile|user|users|member|members|channel|u|author)/([^/?#\s]+)", re.I)
AT_RE = re.compile(r"/@([^/?#\s]+)")
TRAILING_PUNCT = ".,;:!?'\"\\)]}"

# Hosts that are not backlink resources (kept out of the directory).
EXCLUDED_HOST_PATTERNS = [
    # search engines & support pages
    "google.", "bing.com", "search.yahoo.com", "yahoo.com", "yandex.",
    # AI chatbot share links (ephemeral, not link-building resources)
    "chatgpt.com", "claude.ai", "grok.com", "deepseek.com", "share.gemini.google",
    # opaque URL shorteners / one-off shares (no descriptive value)
    "bit.ly", "tinyurl.com", "tr.ee", "jali.me", "aveli.link", "lite.link",
    "canva.link",
    # personal/admin pages, not public resources
    "admin.typeform.com", "app-na2.hubspot.com", "notebook.google.com",
    "docs.google.com",
]

# One exact URL that is off-topic/inappropriate for a professional directory.
EXCLUDED_EXACT_URLS = {
    "https://www.casualdiscourse.com/casual-intercourse/12746-oldfags-nostalgia-trip-anyones-active.html",
}

KNOWN_PLATFORM_NAMES = {
    "medium.com": "Medium", "quora.com": "Quora", "linkedin.com": "LinkedIn",
    "producthunt.com": "Product Hunt", "dev.to": "Dev.to", "github.com": "GitHub",
    "substack.com": "Substack", "vimeo.com": "Vimeo", "about.me": "About.me",
    "trello.com": "Trello", "stackoverflow.com": "Stack Overflow",
}
KNOWN_PLATFORM_NAMES.update({
    "reddit.com": "Reddit", "tumblr.com": "Tumblr", "pinterest.com": "Pinterest",
    "twitter.com": "Twitter / X", "x.com": "X (Twitter)", "facebook.com": "Facebook",
    "instagram.com": "Instagram", "youtube.com": "YouTube", "flickr.com": "Flickr",
    "behance.net": "Behance", "dribbble.com": "Dribbble",
})

SOCIAL_BOOKMARK_HOSTS = {
    "about.me", "linktr.ee", "solo.to", "gravatar.com", "diigo.com",
    "scoop.it", "pearltrees.com", "flipboard.com", "wakelet.com",
    "instapaper.com", "getpocket.com", "are.na", "linkmate.mn.co",
    "joy.bio", "tapmybio.com", "magicly.bio", "spot.fund",
}

def _hosts(s):
    return {w.replace(" ", ".") for w in s.split(",")}

VIDEO_MEDIA_HOSTS = _hosts(
    "youtube com,vimeo com,giphy com,gifyu com,pixabay com,"
    "pexels com,unsplash com,sketchfab com,coub com,"
    "speakerdeck com,slideshare net,issuu com,anyflip com,"
    "pubhtml5 com,heyzine com,flipsnack com"
)


def clean_url(raw):
    """Strip trailing punctuation that the regex may have captured."""
    return raw.rstrip(TRAILING_PUNCT).strip()


def normalize_for_dedup(url):
    """Canonical key for de-duplication (drops fragments and utm_* params)."""
    p = urlparse(url)
    host = p.netloc.lower()
    if host.endswith(":80") and p.scheme == "http":
        host = host[:-3]
    if host.endswith(":443") and p.scheme == "https":
        host = host[:-4]
    path = p.path.rstrip("/") or "/"
    query = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
             if not k.lower().startswith("utm_")]
    query.sort()
    qs = urlencode(query)
    return "%s://%s%s" % (p.scheme.lower(), host, path) + ("?%s" % qs if qs else "")


def valid_url(url):
    if not re.match(r"^https?://", url, re.I):
        return False
    try:
        p = urlparse(url)
    except Exception:
        return False
    host = p.netloc.lower()
    return bool(host) and "." in host and " " not in host


def host_excluded(host):
    labels = host.split(".")
    for pat in EXCLUDED_HOST_PATTERNS:
        p = pat.rstrip(".")
        # multi-label patterns: exact host or subdomain match
        if host == p or host.endswith("." + p):
            return pat
        # single-label patterns (e.g. "google"): match any domain label
        if "." not in p and p in labels:
            return pat
    return None


def derive_name(label, url):
    if label:
        return label.strip()
    host = urlparse(url).netloc.lower()
    host = re.sub(r"^www\.", "", host)
    pretty = KNOWN_PLATFORM_NAMES.get(host, host)
    p = urlparse(url).path or ""
    m = AT_RE.search(p) or PROFILE_RE.search(p)
    if m:
        user = m.group(1).strip().strip("@")
        if user:
            if AT_RE.search(p):
                return "%s — @%s" % (pretty, user)
            return "%s — %s" % (pretty, user)
    return pretty


def categorize(url):
    u = url.lower()
    host = urlparse(url).netloc.lower()
    path = urlparse(url).path.lower()

    if re.search(r"/(profile|user|users|member|members|channel|u|author)/|/@", path):
        return "Profile Backlinks"
    if re.search(r"forum|/thread|/topic|/board|/bbs|phorum|community", u):
        return "Forums & Communities"
    if ("blogspot." in host or "blogger.com" in host or "medium.com" in host
            or "substack.com" in host or "wordpress.com" in host
            or "blog" in host or "telegra.ph" in host or "write.as" in host
            or "hackmd.io" in host or "posteezy.com" in host):
        return "Blogs & Web 2.0"
    if re.search(r"/ad/|/item/|freead|indads|adpost|qwikad|verdeclassifieds|classified", u):
        return "Classified Ads"
    if "directory" in host or "submit.php" in path or "/submit" in path \
            or "linkcentre" in host:
        return "Directories"
    if host in SOCIAL_BOOKMARK_HOSTS:
        return "Social & Bookmarks"
    if host in VIDEO_MEDIA_HOSTS:
        return "Video & Media"
    return "Other"


def parse_workbook(path):
    """Return (entries, stats, exclusions)."""
    wb = openpyxl.load_workbook(path, data_only=True)
    entries = []
    stats = {"sheets": wb.sheetnames, "non_empty_cells": 0, "empty_cells": 0,
             "non_url_cells": 0}
    exclusions = []

    for sheet in wb.sheetnames:
        ws = wb[sheet]
        for row in ws.iter_rows(values_only=True):
            cell = row[0]
            status = row[2] if len(row) > 2 else None
            if cell is None or (isinstance(cell, str) and not cell.strip()):
                stats["empty_cells"] += 1
                continue
            text = str(cell).strip()
            stats["non_empty_cells"] += 1

            label, url_part = None, text
            m = LABEL_URL_RE.match(text)
            if m:
                label, url_part = m.group(1).strip(), m.group(2).strip()

            urls = URL_RE.findall(url_part)
            if not urls:
                bare = re.match(r"^([a-z0-9][a-z0-9.\-]*\.[a-z]{2,}(/\S*)?)$",
                                text, re.I)
                if bare and " " not in text:
                    entries.append({"sheet": sheet, "label": label or None,
                                    "url": "https://" + bare.group(1),
                                    "status": status, "assumed_scheme": True})
                    continue
                stats["non_url_cells"] += 1
                exclusions.append((sheet, text[:90],
                                   "not a URL (header/label text)"))
                continue

            for raw in urls:
                entries.append({"sheet": sheet, "label": label or None,
                                "url": clean_url(raw), "status": status,
                                "assumed_scheme": False})
    return entries, stats, exclusions


def build(path):
    entries, stats, exclusions = parse_workbook(path)

    seen = {}
    resources = []
    dup_count = 0
    for e in entries:
        url = e["url"]
        if not valid_url(url):
            exclusions.append((e["sheet"], url[:90],
                               "invalid URL (bad scheme/host)"))
            continue
        host = urlparse(url).netloc.lower()
        pat = host_excluded(host)
        if pat:
            exclusions.append((e["sheet"], url[:90],
                               "excluded: non-resource pattern '%s'" % pat))
            continue
        key = normalize_for_dedup(url).split("#")[0]
        if key in EXCLUDED_EXACT_URLS:
            exclusions.append((e["sheet"], url[:90],
                               "excluded: off-topic/inappropriate content"))
            continue
        if key in seen:
            dup_count += 1
            continue
        seen[key] = e
        item = {"name": derive_name(e["label"], url), "url": url,
                "category": categorize(url), "source_sheet": e["sheet"]}
        if e.get("status"):
            item["status"] = str(e["status"]).strip()
        if e.get("assumed_scheme"):
            item["note"] = "https scheme assumed (cell had no scheme)"
        resources.append(item)

    resources.sort(key=lambda r: (r["category"], r["name"].lower()))

    RESOURCES_JSON.parent.mkdir(parents=True, exist_ok=True)
    RESOURCES_JSON.write_text(json.dumps(resources, indent=2,
                                         ensure_ascii=False) + "\n",
                              encoding="utf-8")

    cat_counts = Counter(r["category"] for r in resources)
    lines = [
        "# Data Quality Notes -- backlink resources import",
        "",
        "Source workbook: `%s`" % path.name,
        "",
        "## Counts",
        "",
        "- Sheets processed: %d (%s)" % (len(stats["sheets"]),
                                         ", ".join(stats["sheets"])),
        "- Non-empty cells: %d" % stats["non_empty_cells"],
        "- Empty cells skipped: %d" % stats["empty_cells"],
        "- Raw URL entries extracted: %d" % len(entries),
        "- Exact duplicates removed: %d" % dup_count,
        "- Unique resources kept: **%d**" % len(resources),
        "- Excluded entries: %d" % len(exclusions),
        "",
        "## Resources by category",
        "",
    ]
    for cat, n in sorted(cat_counts.items()):
        lines.append("- %s: %d" % (cat, n))
    lines += ["", "## Exclusions", ""]
    if exclusions:
        lines.append("Each excluded entry is listed with its sheet and reason. "
                     "Nothing was silently rewritten into a different URL.")
        lines.append("")
        for sheet, cell, reason in exclusions:
            lines.append("- [%s] `%s` -- %s" % (sheet, cell, reason))
    else:
        lines.append("None.")
    lines += [
        "",
        "## Notes",
        "",
        "- Cells with no scheme (e.g. a bare domain) had https assumed; "
        "this is flagged per-entry in resources.json.",
        "- No domain authority, traffic, or quality scores are invented -- "
        "categories come only from evidence in the URL or its label.",
        "- Re-run `python3 update_resources.py <new-file>.xlsx` after replacing "
        "the workbook to regenerate these files.",
        "",
    ]
    QUALITY_NOTES.write_text("\n".join(lines), encoding="utf-8")

    print("Sheets: %d | non-empty cells: %d | raw URL entries: %d | "
          "duplicates removed: %d | excluded: %d | unique resources: %d"
          % (len(stats["sheets"]), stats["non_empty_cells"], len(entries),
             dup_count, len(exclusions), len(resources)))
    print("Wrote %s and %s" % (RESOURCES_JSON, QUALITY_NOTES))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 update_resources.py path/to/workbook.xlsx")
        sys.exit(1)
    build(Path(sys.argv[1]))
