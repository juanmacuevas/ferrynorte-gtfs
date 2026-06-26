# Optional import assist: PDF → GTFS (Santander – Pedreña – Somo)

> **This is a convenience, not the build.** The source of truth is the
> hand-maintained `../gtfs/*.txt`. This tooling exists only to *draft* the
> regular-season schedule when Los Reginas publishes a fresh, clean PDF — you
> then **review the diff and hand-merge** into `../gtfs/`. It is not run by CI
> and nothing downstream depends on it. Ad-hoc changes (event reroutes, one-off
> sailings) are edited directly in `../gtfs/`; transient disruptions (low tides)
> are out of scope for the static feed.

Two-stage, deterministic. The source PDFs live in [`../sources/`](../sources/)
and are Microsoft Excel *Print To PDF* exports of `Horarios 2026.xlsx`, so the
page is a clean fixed-column grid read by cell position — no OCR, no heuristics.

```
../sources/horario-laborable.pdf ┐               ┌─ trips.txt
../sources/horario-finde.pdf     ┼─ extract.py ─→ timetable.json ─ build.py ─┼─ stop_times.txt
                                 │  (stage 1)                      (stage 2)  ├─ calendar.txt
config.json ─────────────────────────────────────────────────────────────────┼─ calendar_dates.txt
                                                                              └─ feed_info.txt
```

## Stage 1 — `extract.py`  (PDF → `timetable.json`)

Pure transcription, **no GTFS modeling**. For each PDF it records only what is
printed: the three departure columns (`Santander→Pedreña/Somo`, `Somo→Santander`,
`Pedreña→Santander`), the `(*)` "only reaches Pedreña" flag, the *a partir del*
effective date, the day type, and source provenance (file name, Excel title,
SHA-256). Columns are located by clustering the x-positions of the `HH:MM`
tokens into three groups; it aborts if the layout isn't three columns.

`timetable.json` is human-diffable: when a new PDF drops, regenerate it and the
git diff shows exactly which sailings changed.

## Stage 2 — `build.py`  (`timetable.json` + `config.json` → `*.txt`)

Everything **not printed on the PDF** lives in `config.json`: stop ids, the
crossing/dwell minutes used to expand departures into full `stop_times`, the
publishing season window, Cantabria holidays (weekday→weekend swaps), feed
metadata, and the static El Puntal line. Modeling rules:

- Santander departure → `SAN→PED→SOM` trip, or `SAN→PED` if flagged `(*)`.
- Somo departure → `SOM→PED→SAN` return.
- A `Pedreña→Santander` time equal to *(a Somo departure + pass-through offset)*
  is that return calling at Pedreña — **not** a separate trip; the rest are
  dedicated `PED→SAN` trips.
- Trips present in **both** schedules → `ped_comun` (daily); the others →
  `ped_lab` (weekday) / `ped_fds` (weekend).

Static files (`agency`, `stops`, `routes`, `shapes`, `frequencies`) are not
touched — they describe geography/identity, not the timetable.

## Run

From the repo root, via the Makefile (uv handles dependencies):

```bash
make setup                      # once: uv sync (installs pymupdf)
make build                      # rebuild operators/los-reginas/gtfs/*.txt from the PDFs
make check                      # rebuild in memory, diff vs committed gtfs/*.txt, write nothing
```

Or run a stage directly (uv reads the PEP-723 header in `extract.py`):

```bash
uv run operators/los-reginas/src/extract.py
uv run operators/los-reginas/src/build.py --check
```

`--check` reports whether the committed feed still matches what this tooling
would produce — useful to confirm the regular season hasn't drifted, but it is
**not** authoritative: hand-edits to `../gtfs/` (events, one-offs) are expected
and will legitimately make `--check` differ. The blocking gate in CI is
`make validate` (structural correctness), not `--check`.

## Updating when a new clean PDF is published

1. Replace the PDF(s) in [`../sources/`](../sources/) (same file names, or pass
   paths to `extract.py`).
2. Adjust `config.json` if the season window, holidays, travel model or feed
   version changed.
3. `make build` to draft the regular-season schedule into `../gtfs/`.
4. **Review `git diff` on `../gtfs/*.txt`** — accept what's right, hand-fix
   anything the PDF expresses that the model doesn't (special sailings, notes).
5. `make validate`, then commit.

If a PDF is too ad-hoc to model cleanly, skip this tooling entirely and edit
`../gtfs/*.txt` by hand — that's a fully supported path.
