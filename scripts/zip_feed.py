#!/usr/bin/env python3
"""Package an operator's gtfs/ feed into a GTFS zip, deterministically.

GTFS requires the .txt at the zip root (no folders), so files are stored flat.
Entry order is sorted and timestamps/permissions are fixed, so identical feed
content always produces byte-identical output — no phantom "feed changed"
churn for downstream consumers (Google Transit, Mobility Database).

Usage: zip_feed.py <gtfs_dir> <out.zip>
Pure standard library (no dependencies).
"""
import sys, os, glob, zipfile

EPOCH = (1980, 1, 1, 0, 0, 0)   # the lowest timestamp the zip format allows


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: zip_feed.py <gtfs_dir> <out.zip>")
    gtfs_dir, out = sys.argv[1], sys.argv[2]
    files = sorted(glob.glob(os.path.join(gtfs_dir, "*.txt")))
    if not files:
        sys.exit(f"no .txt files in {gtfs_dir}")
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            info = zipfile.ZipInfo(os.path.basename(f), date_time=EPOCH)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, open(f, "rb").read())
    print(f"wrote {out} ({len(files)} files)")


if __name__ == "__main__":
    main()
