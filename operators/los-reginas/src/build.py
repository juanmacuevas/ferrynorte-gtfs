#!/usr/bin/env python3
"""Stage 2 of the Los Reginas GTFS pipeline.

Turn the normalized timetable.json (stage 1) plus config.json into the
schedule-dependent GTFS files:

    trips.txt  stop_times.txt  calendar.txt  calendar_dates.txt  feed_info.txt

plus the config-driven fare files (static, not timetable-derived, but kept in
one place — config.fares — so prices are edited once):

    fare_attributes.txt  fare_rules.txt

The static files (agency.txt, stops.txt, routes.txt, shapes.txt,
frequencies.txt) describe geography/identity, not the timetable, so they are
left untouched.

Modeling, all deterministic:
  * Each Santander departure -> a SAN->PED->SOM trip, unless it is flagged
    Pedreña-only (*) in which case it is a SAN->PED trip.
  * Each Somo departure -> a SOM->PED->SAN return.
  * Each Pedreña->Santander departure that equals (some Somo departure + the
    Somo->Pedreña pass-through offset) is that return passing through Pedreña
    and is NOT a separate trip; the remainder are dedicated PED->SAN trips.
  * Trips that appear in BOTH the weekday and weekend schedule become the
    `common` service (runs daily); the rest become weekday-only / weekend-only.
  * Stop times are expanded from the published departure using the crossing and
    dwell minutes in config.network.

Usage:
    python build.py [--timetable timetable.json] [--config config.json]
                         [--out OPERATOR_DIR] [--check]

--check writes nowhere; it diffs the generated content against the files
already in --out and exits non-zero on any difference.
Default --out is the operator's gtfs/ directory (sibling of this script's folder).
"""
import sys, json, argparse, difflib
from pathlib import Path

# kind -> id suffix; ordering of kinds within a service block (stable output)
SUFFIX = {"OUT_SOM": "O", "RET_SOM": "R", "OUT_PED": "P"}
KIND_ORDER = {"DED_PED": 0, "OUT_PED": 1, "OUT_SOM": 2, "RET_SOM": 3}


def m2(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def hms(x):
    return f"{x // 60:02d}:{x % 60:02d}:00"


def hhmm4(x):
    return f"{x // 60:02d}{x % 60:02d}"


def ymd(iso):
    return iso.replace("-", "")


def puntal_rows(spec):
    """Expand the El Puntal frequency spec into explicit trips + stop_times.

    Half-hourly shuttle with one crossing each way. Emits all outbound trips
    (direction 0) then all returns (direction 1), matching the feed layout.
    trip_id is PUN_<HHMM><suffix> keyed on that leg's departure time.
    """
    leg, hw = spec["leg_minutes"], spec["headway_minutes"]
    route, service = spec["route_id"], spec["service_id"]
    trips, sts = [], []
    for direction, key in ((0, "outbound"), (1, "return")):
        d = spec[key]
        dep = m2(d["first"])
        while dep <= m2(d["last"]):
            tid = f"PUN_{hhmm4(dep)}{d['id_suffix']}"
            trips.append(f"{tid},{route},{service},{d['shape']},{direction},{d['headsign']},0,1")
            sts.append(f"{tid},{hms(dep)},{hms(dep)},{d['from']},1,,0,1,1")
            sts.append(f"{tid},{hms(dep + leg)},{hms(dep + leg)},{d['to']},2,,1,0,1")
            dep += hw
    return trips, sts


def trips_for(sch, pass_offset):
    """Set of (kind, dep_minute) trips implied by one schedule's columns."""
    cols = sch["columns"]
    only = set(sch["pedrena_only"])
    som_min = {m2(t) for t in cols["somo_to_santander"]}
    out = set()
    for t in cols["santander_to_pedrena_somo"]:
        out.add(("OUT_PED" if t in only else "OUT_SOM", m2(t)))
    for t in cols["somo_to_santander"]:
        out.add(("RET_SOM", m2(t)))
    for t in cols["pedrena_to_santander"]:
        if (m2(t) - pass_offset) in som_min:
            continue                                  # return passing through Pedreña
        out.add(("DED_PED", m2(t)))
    return out


def build(timetable, config):
    stops, net = config["stops"], config["network"]
    SAN, PED, SOM = stops["santander"], stops["pedrena"], stops["somo"]
    sp = net["leg_minutes"]["SAN-PED"]
    ps = net["leg_minutes"]["PED-SOM"]
    dwell = net["dwell_minutes"]
    pass_offset = ps + dwell                          # Somo dep -> Pedreña dep on return

    def stoptimes(kind, dep):
        if kind == "OUT_SOM":
            return [(SAN, dep, dep, 0, 1),
                    (PED, dep + sp, dep + sp + dwell, 0, 0),
                    (SOM, dep + sp + dwell + ps, dep + sp + dwell + ps, 1, 0)]
        if kind == "RET_SOM":
            return [(SOM, dep, dep, 0, 1),
                    (PED, dep + ps, dep + ps + dwell, 0, 0),
                    (SAN, dep + ps + dwell + sp, dep + ps + dwell + sp, 1, 0)]
        if kind == "OUT_PED":
            return [(SAN, dep, dep, 0, 1), (PED, dep + sp, dep + sp, 1, 0)]
        if kind == "DED_PED":
            return [(PED, dep, dep, 0, 1), (SAN, dep + sp, dep + sp, 1, 0)]
        raise ValueError(kind)

    sched = {s["day_type"]: s for s in timetable["schedules"]}
    for need in ("weekday", "weekend"):
        if need not in sched:
            sys.exit(f"timetable.json missing a '{need}' schedule")
    wk = trips_for(sched["weekday"], pass_offset)
    fd = trips_for(sched["weekend"], pass_offset)
    common, weekday_only, weekend_only = wk & fd, wk - fd, fd - wk

    svc, tpl, route = config["services"], config["trip_template"], config["route"]["route_id"]

    def trip_id(letter, kind, dep):
        if kind == "DED_PED":
            return f"PS_{letter}_PED{hhmm4(dep)}"
        return f"PS_{letter}_{hhmm4(dep)}{SUFFIX[kind]}"

    static = config["static"]
    static_trips, static_st = list(static.get("trips", [])), list(static.get("stop_times", []))
    if "puntal" in static:                            # El Puntal: expanded from a frequency spec
        pt, pst = puntal_rows(static["puntal"])
        static_trips, static_st = pt + static_trips, pst + static_st

    trip_rows = ["trip_id,route_id,service_id,shape_id,direction_id,trip_headsign,"
                 "wheelchair_accessible,bikes_allowed"] + static_trips
    st_rows = ["trip_id,arrival_time,departure_time,stop_id,stop_sequence,stop_headsign,"
               "pickup_type,drop_off_type,timepoint"] + static_st

    for letter, service_id, trips in (("C", svc["common"], common),
                                      ("L", svc["weekday"], weekday_only),
                                      ("F", svc["weekend"], weekend_only)):
        for kind, dep in sorted(trips, key=lambda kd: (KIND_ORDER[kd[0]], kd[1])):
            t = tpl[kind]
            tid = trip_id(letter, kind, dep)
            trip_rows.append(f"{tid},{route},{service_id},{t['shape']},"
                             f"{t['direction']},{t['headsign']},0,1")
            for seq, (stop, a, d, pu, do) in enumerate(stoptimes(kind, dep), 1):
                st_rows.append(f"{tid},{hms(a)},{hms(d)},{stop},{seq},,{pu},{do},1")

    start, end = ymd(config["season"]["start_date"]), ymd(config["season"]["end_date"])
    cal_rows = ["service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,"
                "start_date,end_date"] + list(config["static"]["calendar"]) + [
        f"{svc['common']},1,1,1,1,1,1,1,{start},{end}",
        f"{svc['weekday']},1,1,1,1,1,0,0,{start},{end}",
        f"{svc['weekend']},0,0,0,0,0,1,1,{start},{end}",
    ]

    cd_rows = ["service_id,date,exception_type"] + list(config["static"]["calendar_dates"])
    for h in config["holidays_weekend_schedule"]:
        cd_rows.append(f"{svc['weekday']},{ymd(h)},2")     # remove weekday service
        cd_rows.append(f"{svc['weekend']},{ymd(h)},1")     # add weekend service

    starts = [start] + [r.split(",")[8] for r in config["static"]["calendar"]]
    ends = [end] + [r.split(",")[9] for r in config["static"]["calendar"]]
    f = config["feed"]
    feed_rows = ["feed_publisher_name,feed_publisher_url,feed_lang,feed_start_date,"
                 "feed_end_date,feed_version,feed_contact_email",
                 f"{f['feed_publisher_name']},{f['feed_publisher_url']},{f['feed_lang']},"
                 f"{min(starts)},{max(ends)},{f['feed_version']},{f['feed_contact_email']}"]

    files = {
        "trips.txt": trip_rows,
        "stop_times.txt": st_rows,
        "calendar.txt": cal_rows,
        "calendar_dates.txt": cd_rows,
        "feed_info.txt": feed_rows,
    }

    fares = config.get("fares")
    if fares:
        cur, pm = fares["currency"], fares["payment_method"]
        fa_rows = ["fare_id,price,currency_type,payment_method,transfers"]
        fr_rows = ["fare_id,route_id"]
        for p in fares["products"]:
            fa_rows.append(f"{p['fare_id']},{p['price']},{cur},{pm},{p['transfers']}")
            fr_rows.append(f"{p['fare_id']},{p['route_id']}")
        files["fare_attributes.txt"] = fa_rows
        files["fare_rules.txt"] = fr_rows

    return files


def main():
    here = Path(__file__).parent
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--timetable", default=str(here / "timetable.json"))
    ap.add_argument("--config", default=str(here / "config.json"))
    ap.add_argument("--out", default=str(here.parent / "gtfs"))
    ap.add_argument("--check", action="store_true",
                    help="diff against existing files, write nothing, exit 1 on mismatch")
    a = ap.parse_args()

    timetable = json.loads(Path(a.timetable).read_text())
    config = json.loads(Path(a.config).read_text())
    files = build(timetable, config)
    outdir = Path(a.out)

    diffs = 0
    for name, rows in files.items():
        content = "\n".join(rows) + "\n"
        target = outdir / name
        if a.check:
            existing = target.read_text() if target.exists() else ""
            if existing != content:
                diffs += 1
                print(f"DIFF {name}:")
                for line in difflib.unified_diff(existing.splitlines(), content.splitlines(),
                                                 name + " (on disk)", name + " (generated)",
                                                 lineterm=""):
                    print("  " + line)
            else:
                print(f"ok   {name} ({len(rows) - 1} rows)")
        else:
            target.write_text(content)
            print(f"wrote {target} ({len(rows) - 1} rows)")

    if a.check and diffs:
        sys.exit(f"\n{diffs} file(s) differ from disk")
    if a.check:
        print("\nAll generated files match disk. ✓")


if __name__ == "__main__":
    main()
