#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pymupdf>=1.24"]
# ///
"""Stage 1 of the Los Reginas GTFS pipeline.

Deterministically transcribe the published timetable PDFs (which are
Microsoft Excel 'Print To PDF' exports of `Horarios 2026.xlsx`, hence a clean
fixed-column grid) into a normalized, modeling-free JSON.

This stage performs NO GTFS modeling: it only reports what is printed on the
page — the three departure columns, the (*) "only reaches Pedreña" flag, the
"a partir del" effective date and the day type. All schedule modeling happens
in stage 2 (build.py) driven by config.json.

Usage:
    python extract.py [PDF_OR_URL ...] [--config config.json] [-o timetable.json]

Each argument is a local PDF path or an http(s) URL. With no arguments it reads
the URLs pinned in config.json -> source.pdfs, so the feed is sourced from the
live published PDFs (no binary is written or committed). Day type is detected
from the PDF text, so argument order does not matter.
Requires: PyMuPDF (`pip install pymupdf`).
"""
import sys, re, json, ssl, hashlib, argparse
from pathlib import Path
from urllib.request import Request, urlopen

try:
    import fitz  # PyMuPDF
except ImportError:
    sys.exit("PyMuPDF required: pip install pymupdf")

_UA = "Mozilla/5.0 (ferrynorte-gtfs extract; +https://ferrynorte.com)"


def load_pdf(src):
    """(fitz.Document, display_name, sha256) for a local path or an http(s) URL.

    URLs are fetched in memory and opened from the byte stream, so sourcing the
    feed from the live PDFs never writes (or commits) a binary."""
    if re.match(r"^https?://", src, re.IGNORECASE):
        req = Request(src, headers={"User-Agent": _UA})
        with urlopen(req, timeout=60, context=ssl.create_default_context()) as r:
            data = r.read()
        return fitz.open(stream=data, filetype="pdf"), src, hashlib.sha256(data).hexdigest()
    p = Path(src)
    return fitz.open(p), p.name, hashlib.sha256(p.read_bytes()).hexdigest()

MONTHS_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}

# Left-to-right column order, fixed by the spreadsheet layout.
COLS = ["santander_to_pedrena_somo", "somo_to_santander", "pedrena_to_santander"]


def cluster_x(xs, gap=40):
    """Group sorted x-coordinates into clusters separated by gaps > `gap` px."""
    xs = sorted(xs)
    groups = [[xs[0]]]
    for x in xs[1:]:
        if x - groups[-1][-1] > gap:
            groups.append([])
        groups[-1].append(x)
    return [sum(g) / len(g) for g in groups]


def extract_pdf(src):
    doc, name, sha = load_pdf(src)
    page = doc[0]
    words = page.get_text("words")          # (x0, y0, x1, y1, text, block, line, word)
    full = page.get_text()

    times = [w for w in words if re.fullmatch(r"\d{2}:\d{2}", w[4])]
    if not times:
        raise SystemExit(f"{name}: no HH:MM tokens found")

    centers = cluster_x([w[0] for w in times])
    if len(centers) != 3:
        raise SystemExit(
            f"{name}: expected 3 time columns, found {len(centers)} "
            f"at x={[round(c) for c in centers]} — layout changed, review the PDF")

    def col_of(x):
        return min(range(3), key=lambda i: abs(x - centers[i]))

    grid = [[], [], []]                      # per column: list of (y, "HH:MM")
    for w in times:
        grid[col_of(w[0])].append((w[1], w[4]))
    for g in grid:
        g.sort()

    columns = {COLS[i]: [t for _, t in grid[i]] for i in range(3)}

    # (*) markers: asterisk tokens sharing a row with a Santander-column time.
    star_tokens = [w for w in words if "*" in w[4]]
    pedrena_only = []
    for y, t in grid[0]:
        if any(abs(sw[1] - y) < 6 and sw[0] > centers[0] - 30 for sw in star_tokens):
            pedrena_only.append(t)

    # "HORARIO QUE REGIRÁ A PARTIR DEL <d> de <month> de <yyyy>"
    eff = None
    m = re.search(r"PARTIR DEL\s+(\d{1,2})\s+de\s+([A-Za-zÁÉÍÓÚáéíóúñ]+)\s+de\s+(\d{4})",
                  full, re.IGNORECASE)
    if m:
        mon = MONTHS_ES.get(m.group(2).lower())
        if mon:
            eff = f"{int(m.group(3)):04d}-{mon:02d}-{int(m.group(1)):02d}"

    up = full.upper()
    if "LABORABLE" in up:
        day_type, label = "weekday", "LABORABLES"
    elif "SÁBADO" in up or "SABADO" in up or "FESTIVO" in up:
        day_type, label = "weekend", "SÁBADOS, DOMINGOS Y FESTIVOS"
    else:
        day_type, label = "unknown", None

    return {
        "source_file": name,
        "source_title": doc.metadata.get("title"),
        "source_producer": doc.metadata.get("producer"),
        "source_sha256": sha,
        "day_type": day_type,
        "label_es": label,
        "effective_date": eff,
        "pedrena_only": sorted(pedrena_only),
        "columns": columns,
    }


def main():
    here = Path(__file__).parent
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pdfs", nargs="*",
                    help="PDF paths or http(s) URLs (default: config.source.pdfs)")
    ap.add_argument("--config", default=str(here / "config.json"))
    ap.add_argument("-o", "--out", default=str(here / "timetable.json"))
    a = ap.parse_args()

    pdfs = a.pdfs
    if not pdfs:
        pdfs = list(json.loads(Path(a.config).read_text())["source"]["pdfs"].values())

    schedules = [extract_pdf(p) for p in pdfs]
    out = {
        "_about": ("Faithful transcription of the Los Reginas timetable PDFs "
                   "(Excel print-to-PDF). Generated by extract.py — "
                   "do not hand-edit; re-run on new PDFs."),
        "schedules": schedules,
    }
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    for s in schedules:
        c = s["columns"]
        print(f"{s['source_file']}: {s['day_type']} eff={s['effective_date']} "
              f"SAN={len(c['santander_to_pedrena_somo'])} "
              f"SOM={len(c['somo_to_santander'])} "
              f"PED={len(c['pedrena_to_santander'])} "
              f"only={s['pedrena_only']}")
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
