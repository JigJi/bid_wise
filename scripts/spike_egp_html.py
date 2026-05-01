"""
Spike 2: e-GP per-project — discover bidder/winner data via PDF chain

Validates the end-to-end UI flow that reaches the winner-announcement PDF
(templateType=W13). The bidder list itself lives in two later PDFs (the
"สรุปข้อมูลการเสนอราคาเบื้องต้น" and "รายงานผลการพิจารณา") which are gated by
the SPA's W1 modal until the project announces สาระสำคัญในสัญญา. Downloading
those PDFs reuses the same chain on a project that has progressed further;
spike 2's job is just to prove the chain works.

Endpoint chain:
  1. greenBook?mode=LINK&methodId=...&tempProjectId=...&pageAnnounceType=W0
       → list of announcements (B0/D0/W0/price/BOQ/...)
  2. infoApproveTemplate?projectId=...&templateType=W13
       → templateId (UUID)
  3. view-pdf-file?templateId={uuid}
       → binary application/pdf

Prereq: Chrome must be running on CDP port 9231 with a fresh profile under
chrome_profile/. The script connects via playwright.connect_over_cdp.

Usage:
  python scripts/spike_egp_html.py            # find first e-bidding winner-announce
                                              # project of the day, dump greenBook + W13 PDF

Output (data/):
  - egp_recent_projects.json    e-bidding winner-announce projects of the day
  - egp_greenbook_<pid>.json    full greenBook listLINK response
  - egp_winner_<pid>.pdf        the W13 PDF
  - egp_template_<pid>.json     infoApproveTemplate metadata
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

CDP = "http://127.0.0.1:9231"
WEB = "https://process5.gprocurement.go.th/egp-agpc01-web/announcement"
HOST = "https://process5.gprocurement.go.th"

GREENBOOK = HOST + "/egp-atpj27-service/pb/a-egp-allt-project/announcement/greenBook"
INFO_TPL = HOST + "/egp-approval-service/apv-common/infoApproveTemplate"
VIEW_PDF = HOST + "/egp-template-service/dwnt/view-pdf-file"


def find_or_open_announcement_tab(ctx):
    for pg in ctx.pages:
        try:
            if "egp-agpc01-web/announcement" in pg.url and "/procurement/" not in pg.url:
                return pg
        except Exception:
            continue
    pg = ctx.new_page()
    pg.goto(WEB, wait_until="domcontentloaded", timeout=60000)
    pg.wait_for_timeout(5000)
    return pg


def pick_ngselect(page, placeholder: str, want: list[str]) -> bool:
    sel = None
    for el in page.query_selector_all("ng-select"):
        try:
            if placeholder in (el.inner_text() or ""):
                sel = el
                break
        except Exception:
            continue
    if sel is None:
        return False
    try:
        sel.click(timeout=4000)
    except Exception:
        sel.click(timeout=4000, force=True)
    page.wait_for_timeout(700)
    for opt in page.query_selector_all(".ng-dropdown-panel .ng-option"):
        try:
            t = opt.inner_text().strip()
        except Exception:
            continue
        if any(w in t for w in want):
            opt.click()
            page.wait_for_timeout(400)
            return True
    page.keyboard.press("Escape")
    return False


def open_winner_ebidding_project(page) -> str | None:
    """Drive the SPA: advanced search → ประเภทประกาศ=ประกาศผู้ชนะ + วิธีการจัดหา=e-bidding,
    click ค้นหา, then click the first valid result row. Returns the encrypted
    procurement URL on success, None on failure.
    """
    try:
        page.bring_to_front()
    except Exception:
        pass

    # open advanced search if its modal isn't already showing
    if not page.query_selector("div.modal.fade.show[aria-modal='true']"):
        adv = page.query_selector("button:has-text('ค้นหาขั้นสูง')")
        if adv:
            try:
                adv.click(timeout=4000)
            except Exception:
                adv.click(timeout=4000, force=True)
            page.wait_for_timeout(1200)

    if not pick_ngselect(page, "เลือกประเภทประกาศ", ["ประกาศรายชื่อผู้ชนะการเสนอราคา"]):
        print("   [!] couldn't set ประเภทประกาศ")
        return None
    if not pick_ngselect(page, "เลือกวิธีการจัดหา", ["ประกวดราคาอิเล็กทรอนิกส์ (e-bidding)"]):
        print("   [!] couldn't set วิธีการจัดหา (continuing anyway)")

    btn = (
        page.query_selector("div.modal.fade.show button:has-text('ค้นหา')")
        or page.query_selector("button:has-text('ค้นหา')")
    )
    try:
        btn.click(timeout=5000)
    except Exception:
        btn.click(timeout=5000, force=True)
    page.wait_for_timeout(7000)
    try:
        page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass

    rows = page.query_selector_all("table tbody tr")
    target = None
    for r in rows:
        try:
            txt = (r.inner_text() or "").strip()
            if not r.is_visible() or len(txt) < 20:
                continue
            if "E1530" in txt or "ปฎิเสธ" in txt:
                continue
            first = txt.split("\t", 1)[0].strip()
            if first.isdigit():
                target = r
                break
        except Exception:
            continue
    if target is None:
        print("   [!] no winner-announce e-bidding rows found today")
        return None
    icon = target.query_selector("egp-all-button a") or target.query_selector("a.btn-icon")
    if icon is None:
        print("   [!] row has no detail-link icon")
        return None
    try:
        icon.scroll_into_view_if_needed(timeout=2000)
    except Exception:
        pass
    try:
        icon.click(timeout=5000)
    except Exception:
        icon.click(timeout=5000, force=True)
    page.wait_for_timeout(7000)
    try:
        page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass
    return page.url if "/procurement/" in page.url else None


def fetch_greenbook(ctx, pid: str, method_id: str = "16") -> dict:
    r = ctx.request.get(
        GREENBOOK,
        params={
            "mode": "LINK",
            "methodId": method_id,
            "tempProjectId": pid,
            "pageAnnounceType": "W0",
        },
        headers={"Referer": WEB, "Accept": "application/json"},
    )
    return r.json() if "json" in r.headers.get("content-type", "") else {"_status": r.status}


def fetch_template_and_pdf(ctx, pid: str, template_type: str = "W13") -> tuple[dict, bytes | None]:
    r1 = ctx.request.get(
        INFO_TPL,
        params={"projectId": pid, "templateType": template_type},
        headers={"Referer": WEB, "Accept": "application/json"},
    )
    meta = r1.json()
    tid = (meta.get("data") or {}).get("templateId")
    if not tid:
        return meta, None
    r2 = ctx.request.get(
        VIEW_PDF,
        params={"templateId": tid},
        headers={"Referer": WEB, "Accept": "application/pdf,*/*"},
    )
    body = r2.body()
    if not body.startswith(b"%PDF"):
        return meta, None
    return meta, body


def main() -> int:
    print(f"[+] connecting to Chrome via CDP {CDP}")
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP)
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        page = find_or_open_announcement_tab(ctx)
        print(f"[+] using tab: {page.url}")

        proc_url = open_winner_ebidding_project(page)
        if proc_url is None:
            print("[!] could not reach a /procurement/{enc} page")
            return 1
        print(f"[+] procurement detail: {proc_url}")

        # The SPA stores the resolved projectId in the page's stored greenBook
        # response; the tab also exposes it inside text on the page.
        body_text = page.inner_text("body")
        # ลองหา "เลขที่โครงการ" column
        pid = None
        for line in body_text.splitlines():
            ln = line.strip()
            if ln.isdigit() and 10 <= len(ln) <= 14:
                pid = ln
                break
        if pid is None:
            # fall back to extracting from the page text after the label
            import re
            m = re.search(r"เลขที่โครงการ\s+(\d{10,14})", body_text)
            if m:
                pid = m.group(1)
        if pid is None:
            print("[!] couldn't extract projectId from the detail page text")
            return 2
        print(f"[+] projectId = {pid}")

        gb = fetch_greenbook(ctx, pid, method_id="16")
        (DATA / f"egp_greenbook_{pid}.json").write_text(
            json.dumps(gb, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        items = ((gb.get("data") or {}).get("greenBookAnnouncementTypeLinkDto") or [])
        print(f"[+] greenBook returned {len(items)} announcement(s):")
        for it in items:
            print(f"    type={it.get('announceType'):<6} desc={(it.get('announceTypeDesc') or '')[:50]}")

        meta, pdf = fetch_template_and_pdf(ctx, pid, template_type="W13")
        (DATA / f"egp_template_{pid}.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        if pdf:
            out = DATA / f"egp_winner_{pid}.pdf"
            out.write_bytes(pdf)
            print(f"[+] saved W13 PDF -> {out}  ({len(pdf):,} bytes)")
        else:
            print(f"[!] no PDF returned for templateType=W13 / pid={pid}")
            print(f"    meta response: {json.dumps(meta, ensure_ascii=False)[:300]}")

    print("\n[+] spike 2 done — feed the PDF into spike_pdf_ocr.py to extract winner+price.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
