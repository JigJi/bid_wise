"""
Spike 1: ACT Ai bulk bidder dataset

Goal: verify we can download bidder data from opendata.actai.co and
inspect schema + a sample of records.

Datasets of interest:
  - ds_001_007: นิติบุคคลที่ยื่นซอง (entities that submitted bids)
  - ds_001_005: นิติบุคคลที่ผ่านคุณสมบัติ (entities that passed qualification)

Output: prints schema + first 10 rows of each. Saves CSVs to data/.

Run: python scripts/spike_act_csv.py
"""
from __future__ import annotations

import csv
import json
import os
import sys
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

DATASETS = [
    "ds_001_007",  # bidders
    "ds_001_005",  # qualified bidders
]

UA = {"User-Agent": "Mozilla/5.0 (BidWise spike test)"}


def find_resource_urls(dataset_id: str) -> list[dict]:
    """Scrape ACT Open Data dataset page for downloadable resource URLs."""
    url = f"https://opendata.actai.co/dataset/{dataset_id}"
    print(f"\n[+] Fetching dataset page: {url}")
    r = requests.get(url, headers=UA, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")

    resources = []
    # CKAN typically exposes resource links via class="resource-item" or similar
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if any(href.lower().endswith(ext) for ext in (".csv", ".csv.gz", ".zip", ".json")):
            resources.append({"url": urljoin(url, href), "label": a.get_text(strip=True)[:80]})
        elif "download" in href.lower() and "resource" in href.lower():
            resources.append({"url": urljoin(url, href), "label": a.get_text(strip=True)[:80]})

    # Also look for gsutil / gs:// URLs in the page text
    for m in re.finditer(r"gs://[^\s\"']+", r.text):
        resources.append({"url": m.group(0), "label": "gsutil"})

    # Look for raw URLs containing storage.googleapis.com
    for m in re.finditer(r"https?://storage\.googleapis\.com/[^\s\"'<>]+", r.text):
        resources.append({"url": m.group(0), "label": "GCS direct"})

    return resources


def try_download(url: str, dest: Path) -> bool:
    if url.startswith("gs://"):
        print(f"   -> gsutil URL detected: {url}")
        print(f"      install gsutil and run: gsutil cp '{url}' '{dest}'")
        return False
    print(f"   -> HTTP download: {url}")
    try:
        r = requests.get(url, headers=UA, timeout=120, stream=True)
        r.raise_for_status()
        size = 0
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=64 * 1024):
                if chunk:
                    f.write(chunk)
                    size += len(chunk)
        print(f"      saved {size:,} bytes -> {dest}")
        return True
    except Exception as e:
        print(f"      [!] download failed: {e}")
        return False


def inspect_csv(path: Path, limit: int = 10) -> None:
    print(f"\n[+] Inspecting {path.name}")
    try:
        with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
            reader = csv.reader(f)
            try:
                header = next(reader)
            except StopIteration:
                print("    (empty)")
                return
            print(f"    columns ({len(header)}): {header}")
            for i, row in enumerate(reader):
                if i >= limit:
                    break
                print(f"    row {i + 1}: {dict(zip(header, row))}")
    except Exception as e:
        print(f"    [!] inspect failed: {e}")


def main() -> int:
    summary = {}
    for ds in DATASETS:
        print(f"\n{'=' * 60}\nDATASET: {ds}\n{'=' * 60}")
        try:
            resources = find_resource_urls(ds)
        except Exception as e:
            print(f"[!] could not fetch dataset page: {e}")
            summary[ds] = {"resources": [], "downloaded": False}
            continue

        print(f"[+] found {len(resources)} candidate resource URL(s):")
        for r in resources[:10]:
            print(f"    - {r['label']:40s} {r['url']}")

        downloaded = False
        for r in resources:
            if r["url"].startswith("gs://"):
                continue
            ext = ".csv"
            if r["url"].lower().endswith((".gz", ".zip", ".json")):
                ext = "." + r["url"].rsplit(".", 1)[-1].lower()
            dest = DATA_DIR / f"{ds}{ext}"
            if try_download(r["url"], dest):
                downloaded = True
                if ext == ".csv":
                    inspect_csv(dest)
                break

        summary[ds] = {"resources": resources, "downloaded": downloaded}

    print("\n" + "=" * 60)
    print("SPIKE 1 SUMMARY")
    print("=" * 60)
    print(json.dumps(
        {k: {"resources_found": len(v["resources"]), "downloaded": v["downloaded"]} for k, v in summary.items()},
        indent=2, ensure_ascii=False,
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
