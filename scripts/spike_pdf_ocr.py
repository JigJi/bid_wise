"""
Spike 3: PDF "รายงานผลการพิจารณา" extraction

Goal: verify that PDF attachments from e-GP can be parsed for bidder + price + qualification.

Strategy:
  1. Try pdfplumber first (works for text-based PDFs — fast, no GPU)
  2. If text is empty / mostly empty → flag as scanned PDF, requires PaddleOCR
     (defer OCR setup to phase 1; for spike, just identify which PDFs are scanned)

Usage:
  python scripts/spike_pdf_ocr.py <pdf_path_or_url>

If no arg given, will try to fetch one PDF from a sample e-GP project.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import requests
import pdfplumber

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

UA = {"User-Agent": "Mozilla/5.0 (BidWise spike test)"}

BIDDER_HINTS = ["ผู้เสนอราคา", "ผู้ยื่น", "ผู้ผ่านคุณสมบัติ", "ราคาที่เสนอ", "ผู้ชนะ"]


def download_pdf(url: str, dest: Path) -> bool:
    print(f"[+] downloading PDF: {url}")
    try:
        r = requests.get(url, headers=UA, timeout=60, verify=False, stream=True)
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=64 * 1024):
                if chunk:
                    f.write(chunk)
        print(f"    saved {dest.stat().st_size:,} bytes -> {dest}")
        return True
    except Exception as e:
        print(f"    [!] download failed: {e}")
        return False


def extract_text(path: Path) -> dict:
    """Returns dict with per-page text + summary stats."""
    out = {"pages": 0, "total_chars": 0, "has_text": False, "preview": "", "tables_found": 0}
    try:
        with pdfplumber.open(path) as pdf:
            out["pages"] = len(pdf.pages)
            all_text = []
            for page in pdf.pages:
                t = page.extract_text() or ""
                all_text.append(t)
                tables = page.extract_tables()
                out["tables_found"] += len(tables) if tables else 0
            joined = "\n".join(all_text)
            out["total_chars"] = len(joined)
            out["has_text"] = len(joined.strip()) > 50
            out["preview"] = joined[:1500]
            out["full_text"] = joined
    except Exception as e:
        out["error"] = str(e)
    return out


def find_bidder_signals(text: str) -> dict:
    hits = {kw: text.count(kw) for kw in BIDDER_HINTS if kw in text}
    # Detect price-looking patterns near bidder hints
    price_lines = []
    for line in text.splitlines():
        if any(kw in line for kw in BIDDER_HINTS):
            price_lines.append(line.strip()[:200])
        elif re.search(r"\d{1,3}(,\d{3})+(\.\d+)?\s*(บาท|฿)?", line) and len(price_lines) < 30:
            price_lines.append(line.strip()[:200])
    return {"keyword_hits": hits, "candidate_lines_sample": price_lines[:20]}


def main() -> int:
    requests.packages.urllib3.disable_warnings()  # type: ignore

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg.startswith("http"):
            local = DATA_DIR / "spike3_input.pdf"
            if not download_pdf(arg, local):
                return 1
        else:
            local = Path(arg)
    else:
        # Default: prompt user to pass a URL or path. We don't auto-discover here
        # because PDFs on e-GP usually require the project page context.
        print(__doc__)
        print("\n[!] no PDF path/url given. Pass one as argv.")
        print("    e.g.  python scripts/spike_pdf_ocr.py <url-of-รายงานผลการพิจารณา.pdf>")
        return 2

    if not local.exists():
        print(f"[!] file not found: {local}")
        return 1

    print(f"\n[+] extracting text from {local.name}")
    info = extract_text(local)
    print(f"    pages={info['pages']} total_chars={info['total_chars']} has_text={info['has_text']} tables={info['tables_found']}")
    if info.get("error"):
        print(f"    [!] extract error: {info['error']}")
        return 1

    if not info["has_text"]:
        print("\n[!] PDF appears to be SCANNED (no extractable text layer).")
        print("    Next step: install PaddleOCR + run with GPU. Reuse alma/ pipeline.")
        return 0

    print(f"\n    preview (first 1500 chars):\n    {info['preview']!r}")

    sig = find_bidder_signals(info.get("full_text", ""))
    print(f"\n[+] bidder keyword hits in PDF: {sig['keyword_hits']}")
    print(f"\n[+] candidate bidder/price lines (first 20):")
    for ln in sig["candidate_lines_sample"]:
        print(f"    - {ln}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
