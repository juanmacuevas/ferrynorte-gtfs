#!/usr/bin/env python3
"""Validate one or more GTFS feeds (the hand-maintained source of truth).

Operator-agnostic structural + referential checks — the safety net for manual
edits. Hard errors only (this gates releases, so no style noise / false alarms).

Usage:
    validate.py [GTFS_DIR ...]      # default: every operators/*/gtfs
Exit code 1 if any feed has errors. Pure standard library.
"""
import sys, csv, glob, os, re

REQUIRED = ["agency.txt", "stops.txt", "routes.txt", "trips.txt", "stop_times.txt"]
DATE_RE = re.compile(r"^\d{8}$")


def load(path):
    if not os.path.exists(path):
        return None
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def ids(rows, col):
    return {r[col] for r in rows if r.get(col)} if rows else set()


def secs(t):
    try:
        h, m, s = t.split(":")
        return int(h) * 3600 + int(m) * 60 + int(s)
    except Exception:
        return None


def validate(gtfs_dir):
    errs = []

    def err(msg):
        errs.append(msg)

    for f in REQUIRED:
        if not os.path.exists(os.path.join(gtfs_dir, f)):
            err(f"missing required file {f}")
    cal = os.path.join(gtfs_dir, "calendar.txt")
    caldates = os.path.join(gtfs_dir, "calendar_dates.txt")
    if not os.path.exists(cal) and not os.path.exists(caldates):
        err("missing calendar.txt and calendar_dates.txt (need at least one)")
    if errs:
        return errs  # can't go further without the core files

    agency = load(os.path.join(gtfs_dir, "agency.txt")) or []
    stops = load(os.path.join(gtfs_dir, "stops.txt")) or []
    routes = load(os.path.join(gtfs_dir, "routes.txt")) or []
    trips = load(os.path.join(gtfs_dir, "trips.txt")) or []
    stop_times = load(os.path.join(gtfs_dir, "stop_times.txt")) or []
    calendar = load(cal) or []
    calendar_dates = load(caldates) or []
    shapes = load(os.path.join(gtfs_dir, "shapes.txt")) or []
    freqs = load(os.path.join(gtfs_dir, "frequencies.txt")) or []
    feedinfo = load(os.path.join(gtfs_dir, "feed_info.txt")) or []
    fare_attrs = load(os.path.join(gtfs_dir, "fare_attributes.txt")) or []
    fare_rules = load(os.path.join(gtfs_dir, "fare_rules.txt")) or []

    agency_ids = ids(agency, "agency_id")
    stop_ids = ids(stops, "stop_id")
    route_ids = ids(routes, "route_id")
    trip_ids = ids(trips, "trip_id")
    shape_ids = ids(shapes, "shape_id")
    service_ids = ids(calendar, "service_id") | ids(calendar_dates, "service_id")

    # uniqueness
    for rows, col, name in ((stops, "stop_id", "stops"), (routes, "route_id", "routes"),
                            (trips, "trip_id", "trips"), (calendar, "service_id", "calendar")):
        seen, dup = set(), set()
        for r in rows:
            v = r.get(col)
            if v in seen:
                dup.add(v)
            seen.add(v)
        for v in sorted(dup):
            err(f"{name}: duplicate {col} '{v}'")

    # agency_id on routes (only required when >1 agency)
    if len(agency_ids) > 1 or any(r.get("agency_id") for r in routes):
        for r in routes:
            a = r.get("agency_id")
            if a and a not in agency_ids:
                err(f"routes: route_id '{r['route_id']}' -> unknown agency_id '{a}'")

    # trips -> route/service/shape
    for t in trips:
        if t["route_id"] not in route_ids:
            err(f"trips: trip_id '{t['trip_id']}' -> unknown route_id '{t['route_id']}'")
        if t["service_id"] not in service_ids:
            err(f"trips: trip_id '{t['trip_id']}' -> unknown service_id '{t['service_id']}'")
        sh = t.get("shape_id")
        if sh and sh not in shape_ids:
            err(f"trips: trip_id '{t['trip_id']}' -> unknown shape_id '{sh}'")

    # calendar_dates -> service (a service may live only in calendar_dates, so allow self)
    cd_only = ids(calendar_dates, "service_id")
    for r in calendar_dates:
        if r["service_id"] not in (ids(calendar, "service_id") | cd_only):
            err(f"calendar_dates: unknown service_id '{r['service_id']}'")

    # frequencies -> trips
    for r in freqs:
        if r["trip_id"] not in trip_ids:
            err(f"frequencies: unknown trip_id '{r['trip_id']}'")

    # fares (v1): rules -> fare_attributes / routes
    fare_ids = ids(fare_attrs, "fare_id")
    for r in fare_rules:
        if r["fare_id"] not in fare_ids:
            err(f"fare_rules: unknown fare_id '{r['fare_id']}'")
        rt = r.get("route_id")
        if rt and rt not in route_ids:
            err(f"fare_rules: fare_id '{r['fare_id']}' -> unknown route_id '{rt}'")

    # stop_times -> trips/stops, and per-trip structure
    per_trip = {}
    for r in stop_times:
        if r["trip_id"] not in trip_ids:
            err(f"stop_times: unknown trip_id '{r['trip_id']}'")
        if r["stop_id"] not in stop_ids:
            err(f"stop_times: trip '{r['trip_id']}' -> unknown stop_id '{r['stop_id']}'")
        per_trip.setdefault(r["trip_id"], []).append(r)

    for tid in trip_ids:
        rows = per_trip.get(tid)
        if not rows:
            err(f"trips: trip_id '{tid}' has no stop_times")
            continue
        rows.sort(key=lambda r: int(r["stop_sequence"]))
        seqs = [int(r["stop_sequence"]) for r in rows]
        if len(set(seqs)) != len(seqs):
            err(f"stop_times: trip '{tid}' has duplicate stop_sequence")
        prev = -1
        for r in rows:
            a, d = secs(r["arrival_time"]), secs(r["departure_time"])
            if a is None or d is None:
                err(f"stop_times: trip '{tid}' has bad time at stop '{r['stop_id']}'")
                continue
            if d < a:
                err(f"stop_times: trip '{tid}' departure before arrival at '{r['stop_id']}'")
            if a < prev:
                err(f"stop_times: trip '{tid}' time goes backwards at '{r['stop_id']}'")
            prev = d

    # date formats
    for r in calendar:
        for c in ("start_date", "end_date"):
            if not DATE_RE.match(r.get(c, "")):
                err(f"calendar: service '{r['service_id']}' bad {c} '{r.get(c)}'")
    for r in calendar_dates:
        if not DATE_RE.match(r.get("date", "")):
            err(f"calendar_dates: bad date '{r.get('date')}'")
    for r in feedinfo:
        for c in ("feed_start_date", "feed_end_date"):
            if r.get(c) and not DATE_RE.match(r[c]):
                err(f"feed_info: bad {c} '{r[c]}'")

    return errs


def main():
    dirs = sys.argv[1:] or sorted(glob.glob("operators/*/gtfs"))
    if not dirs:
        sys.exit("no GTFS directories found")
    total = 0
    for d in dirs:
        errs = validate(d)
        if errs:
            total += len(errs)
            print(f"✗ {d}: {len(errs)} error(s)")
            for e in errs:
                print(f"    - {e}")
        else:
            print(f"✓ {d}")
    if total:
        sys.exit(f"\n{total} validation error(s)")
    print("\nAll feeds valid. ✓")


if __name__ == "__main__":
    main()
