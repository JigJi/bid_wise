"""
Spike 2: e-GP per-project HTML — extract bidder list

Goal: verify that process3.gprocurement.go.th project detail HTML is fetchable
without login and that bidder list is parseable.

Sample URL pattern:
  https://process3.gprocurement.go.th/egp2procmainWeb/jsp/procsearch.sch
    ?pid=<PROJECT_ID>&servlet=gojsp&proc_id=ShowHTMLFile&processFlows=Procure

Output: saves raw HTML, lists tables found, attempts to identify bidder section.

Run: python scripts/spike_egp_html.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# Sample project IDs — try a few; replace with known recent e-bidding pids if needed
SAMPLE_PIDS = [
    "68119188722",  # from research agent's confirmed-working sample
]

BASE = "https://process3.gprocurement.go.th/egp2procmainWeb/jsp/procsearch.sch"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

# Thai keywords that mark the bidder section in รายงานผลการพิจารณา-style pages
BIDDER_KEYWORDS = [
    "ผู้เสนอราคา",
    "ผู้ยื่นข้อเสนอ",
    "ผู้ยื่นซอง",
    "รายชื่อผู้",
    "ผู้ผ่านคุณสมบัติ",
    "ผู้ชนะ",
    "ราคาที่เสนอ",
]


def fetch_project_html(pid: str) -> str | None:
    params = {
        "pid": pid,
        "servlet": "gojsp",
        "proc_id": "ShowHTMLFile",
        "processFlows": "Procure",
    }
    url = BASE
    print(f"\n[+] GET {url}?pid={pid}&...")
    try:
        r = requests.get(url, params=params, headers=UA, timeout=30, verify=False)
        print(f"    status={r.status_code} bytes={len(r.content):,} encoding={r.encoding}")
        if r.status_code != 200:
            return None
        return r.text
    except Exception as e:
        print(f"    [!] fetch failed: {e}")
        return None


def analyze_html(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    info = {
        "title": (soup.title.string or "").strip() if soup.title else "",
        "tables": len(soup.find_all("table")),
        "links": len(soup.find_all("a")),
        "pdf_links": [],
        "bidder_keyword_hits": {},
        "iframe_count": len(soup.find_all("iframe")),
    }

    for a in soup.find_all("a", href=True):
        h = a["href"]
        if h.lower().endswith(".pdf") or "pdf" in h.lower():
            info["pdf_links"].append({"href": h, "text": a.get_text(strip=True)[:80]})

    text = soup.get_text(" ", strip=True)
    for kw in BIDDER_KEYWORDS:
        cnt = text.count(kw)
        if cnt:
            info["bidder_keyword_hits"][kw] = cnt

    return info


def find_bidder_table(html: str) -> list[list[str]] | None:
    """Look for an HTML table that mentions bidder keywords + try to extract rows."""
    soup = BeautifulSoup(html, "lxml")
    for tbl in soup.find_all("table"):
        tbl_text = tbl.get_text(" ", strip=True)
        if any(kw in tbl_text for kw in ("ผู้เสนอราคา", "ผู้ยื่น", "ผู้ผ่านคุณสมบัติ")):
            rows = []
            for tr in tbl.find_all("tr"):
                cells = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
                if cells:
                    rows.append(cells)
            return rows
    return None


def main() -> int:
    requests.packages.urllib3.disable_warnings()  # type: ignore

    for pid in SAMPLE_PIDS:
        html = fetch_project_html(pid)
        if not html:
            print(f"    [!] no HTML for pid={pid}")
            continue

        out_path = DATA_DIR / f"egp_project_{pid}.html"
        out_path.write_text(html, encoding="utf-8")
        print(f"    saved -> {out_path}")

        info = analyze_html(html)
        print(f"    title: {info['title'][:120]}")
        print(f"    tables={info['tables']}  links={info['links']}  iframes={info['iframe_count']}")
        print(f"    pdf_links: {len(info['pdf_links'])}")
        for p in info["pdf_links"][:5]:
            print(f"      - {p['text']:50s} {p['href']}")
        print(f"    bidder keyword hits: {info['bidder_keyword_hits']}")

        rows = find_bidder_table(html)
        if rows:
            print(f"\n    [+] candidate bidder table — {len(rows)} rows:")
            for i, r in enumerate(rows[:15]):
                print(f"        row {i}: {r}")
        else:
            print("    [!] no bidder-keyword table found in HTML")
            # Heuristic: dump first 500 chars of body text to see what we got
            body_text = BeautifulSoup(html, "lxml").get_text(" ", strip=True)
            print(f"\n    body preview: {body_text[:400]}...")

    return 0


if __name__ == "__main__":
    sys.exit(main())
