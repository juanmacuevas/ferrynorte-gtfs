#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Watch the Los Reginas website for a newly published timetable.

Los Reginas publish each timetable as a date-stamped PDF linked from a single
listing page. When a schedule changes they upload a new PDF under a new name
(e.g. `horario-fines-de-semana-04.07.pdf`) and swap the link; the old file lingers
but is no longer linked. This script fetches that page, scrapes the
`horario-*.pdf` links, and compares them to the URLs pinned in
`config.json` -> `source.pdfs`.

It is a *detector*, not an updater: when it fires, a human reviews the new PDF,
updates `source.pdfs`, runs `make build`, and reviews the GTFS diff.

Exit codes (so cron/CI can branch on them):
  0  linked PDFs match config          -> nothing to do
  1  links differ from config          -> a new timetable was likely published
  2  could not check (network/parse)   -> NOT a schedule signal; look manually

Run:  uv run python check_source.py [--config config.json] [--url LISTING_URL]
"""
import sys, re, json, argparse, ssl
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from urllib.error import URLError

UA = "Mozilla/5.0 (ferrynorte-gtfs source-watch; +https://ferrynorte.com)"

# horario PDFs are linked as .../horario-<something>.pdf, in single- or
# double-quoted href attributes. Match by filename, not by surrounding markup,
# so a WordPress theme/layout change does not blind the detector.
PDF_RE = re.compile(r"""href=['"]([^'"]*?/horario-[^'"/]*?\.pdf)['"]""", re.IGNORECASE)


def fetch(url, timeout=30):
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=timeout, context=ssl.create_default_context()) as r:
        charset = r.headers.get_content_charset() or "utf-8"
        return r.read().decode(charset, "replace")


def discover(html, base_url):
    """Ordered, de-duplicated absolute horario-*.pdf links found on the page."""
    seen, out = set(), []
    for m in PDF_RE.finditer(html):
        u = urljoin(base_url, m.group(1))
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def slot_of(url):
    """Map a PDF URL to its logical schedule slot by filename convention."""
    name = url.rsplit("/", 1)[-1].lower()
    if "laborable" in name:
        return "weekday"
    if "fines-de-semana" in name or "finde" in name or "festivo" in name:
        return "weekend"
    return "other"


def main():
    here = Path(__file__).parent
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=str(here / "config.json"))
    ap.add_argument("--url", help="override the listing URL from config")
    ap.add_argument("--timeout", type=int, default=30)
    a = ap.parse_args()

    try:
        cfg = json.loads(Path(a.config).read_text())
        src = cfg["source"]
        listing = a.url or src["listing_url"]
        pinned = dict(src["pdfs"])            # {slot: url}
    except (OSError, KeyError, json.JSONDecodeError) as e:
        print(f"cannot read config source block: {e}", file=sys.stderr)
        return 2

    try:
        html = fetch(listing, a.timeout)
    except (URLError, TimeoutError, OSError) as e:
        print(f"could not fetch {listing}: {e}", file=sys.stderr)
        return 2

    live = discover(html, listing)
    if not live:
        print(f"no horario-*.pdf links found on {listing}", file=sys.stderr)
        print("the page structure may have changed — check it by hand.", file=sys.stderr)
        return 2

    live_by_slot = {}
    for u in live:
        live_by_slot.setdefault(slot_of(u), []).append(u)

    changed = False
    lines = []
    for slot, purl in pinned.items():
        found = live_by_slot.get(slot, [])
        if found == [purl]:
            lines.append(f"  ok      {slot:8} {purl}")
        elif purl in found:
            changed = True
            others = [u for u in found if u != purl]
            lines.append(f"  EXTRA   {slot:8} pinned link present, but also: {others}")
        elif found:
            changed = True
            lines.append(f"  CHANGED {slot:8} pinned {purl}")
            for u in found:
                lines.append(f"          {'':8} site   {u}")
        else:
            changed = True
            lines.append(f"  MISSING {slot:8} pinned {purl} — no matching link on site")

    # links on the site we don't track at all (e.g. a new 'other' schedule)
    untracked = [u for u in live if slot_of(u) not in pinned]
    for u in untracked:
        changed = True
        lines.append(f"  NEW     {slot_of(u):8} {u} (not in config.source.pdfs)")

    print(f"listing: {listing}")
    print("\n".join(lines))

    if changed:
        print("\nSource changed — a new timetable was likely published.")
        print("Review the new PDF, update config.source.pdfs, then `make build`.")
        return 1
    print("\nSource unchanged. ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
