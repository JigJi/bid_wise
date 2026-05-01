"""
Spike 1: ACT Ai bulk bidder dataset (ds_001_007 = นิติบุคคลที่ยื่นซอง)

Data lives in a public GCS bucket (act_opendata) — not on the CKAN portal HTML.
Discovered via CKAN package_show API: resources[0].url points to a
`console.cloud.google.com/storage/browser/...` link, which corresponds to a
prefix inside `gs://act_opendata/`.

Usage:
  python scripts/spike_act_csv.py            # list + sample (default)
  python scripts/spike_act_csv.py --full     # download every shard under the prefix

Output:
  - data/ds_001_007_listing.json   bucket listing snapshot
  - data/ds_001_007_combined.csv   merged sample (or full) of bidder rows
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

BUCKET = "act_opendata"
PREFIX = "opendata/master_data/ds_001/001/submit/"
LIST_API = f"https://storage.googleapis.com/storage/v1/b/{BUCKET}/o"
OBJ_BASE = f"https://storage.googleapis.com/{BUCKET}/"

EXPECTED_COLS = ["document_id", "buydoc_date", "name", "submit_date", "type", "company_id"]


def list_objects(prefix: str) -> list[dict]:
    """Page through the GCS JSON listing API."""
    out: list[dict] = []
    page_token: str | None = None
    while True:
        params: dict[str, str] = {"prefix": prefix, "maxResults": "1000"}
        if page_token:
            params["pageToken"] = page_token
        r = requests.get(LIST_API, params=params, timeout=30)
        r.raise_for_status()
        j = r.json()
        out.extend(j.get("items", []))
        page_token = j.get("nextPageToken")
        if not page_token:
            break
    return out


def fetch_csv_rows(object_name: str) -> tuple[list[str], list[list[str]]]:
    url = OBJ_BASE + object_name
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    text = r.content.decode("utf-8", errors="replace")
    rdr = csv.reader(io.StringIO(text))
    rows = list(rdr)
    if not rows:
        return [], []
    return rows[0], rows[1:]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="download every shard (slow)")
    ap.add_argument("--sample-shards", type=int, default=10, help="how many shards to pull in default mode")
    args = ap.parse_args()

    print(f"[+] listing gs://{BUCKET}/{PREFIX} ...")
    objs = list_objects(PREFIX)
    csv_objs = [o for o in objs if o["name"].endswith(".csv") and "split" in o["name"]]
    print(f"    total objects: {len(objs)}   csv shards: {len(csv_objs)}")

    listing_path = DATA_DIR / "ds_001_007_listing.json"
    listing_path.write_text(
        json.dumps([{"name": o["name"], "size": o.get("size"), "updated": o.get("updated")} for o in csv_objs], indent=2),
        encoding="utf-8",
    )
    print(f"    saved listing -> {listing_path}")

    if not csv_objs:
        print("[!] no shards found — bucket layout may have changed")
        return 1

    total_size = sum(int(o.get("size", 0)) for o in csv_objs)
    print(f"    aggregate size: {total_size:,} bytes ({total_size/1024/1024:.1f} MiB)")

    targets = csv_objs if args.full else csv_objs[: args.sample_shards]
    print(f"\n[+] pulling {len(targets)} shard(s) ({'FULL' if args.full else 'sample'}) ...")

    combined_path = DATA_DIR / "ds_001_007_combined.csv"
    rows_total = 0
    bidder_unique: set[str] = set()
    project_unique: set[str] = set()

    with open(combined_path, "w", encoding="utf-8", newline="") as fout:
        w = csv.writer(fout)
        w.writerow(EXPECTED_COLS)
        for i, obj in enumerate(targets, 1):
            try:
                header, rows = fetch_csv_rows(obj["name"])
            except Exception as e:
                print(f"    [!] {obj['name']}: {e}")
                continue
            if header != EXPECTED_COLS:
                print(f"    [!] unexpected header in {obj['name']}: {header}")
                continue
            for row in rows:
                w.writerow(row)
                rows_total += 1
                rec = dict(zip(header, row))
                if rec.get("name"):
                    bidder_unique.add(rec["name"].strip())
                if rec.get("document_id"):
                    project_unique.add(rec["document_id"])
            if i % 5 == 0 or i == len(targets):
                print(f"    [{i}/{len(targets)}] rows so far: {rows_total:,}")

    print(f"\n[+] merged -> {combined_path}  ({rows_total:,} bidder rows)")
    print(f"    unique projects: {len(project_unique):,}")
    print(f"    unique bidder names: {len(bidder_unique):,}")

    print("\n[+] sample — first 3 distinct projects with their bidders:")
    with open(combined_path, "r", encoding="utf-8", newline="") as fin:
        rdr = csv.DictReader(fin)
        seen_proj: dict[str, list[dict]] = {}
        for row in rdr:
            pid = row["document_id"]
            seen_proj.setdefault(pid, []).append(row)
            if len(seen_proj) >= 3 and len(seen_proj[pid]) >= 3:
                # keep collecting only this many
                pass
        for pid, bidders in list(seen_proj.items())[:3]:
            print(f"\n    project {pid}  ({len(bidders)} bidders)")
            for b in bidders[:8]:
                print(f"       - {b['name']:50s}  tax_id={b['company_id']:20s}  submit={b['submit_date']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
