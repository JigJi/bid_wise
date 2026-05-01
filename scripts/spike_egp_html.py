"""
Spike 2: e-GP per-project — bidder list via getProcureResult JSON

The moat endpoint (verified 2026-05-01):
  GET egp-atpj27-service/pb/a-egp-allt-project/announcement/getProcureResult?projectId={pid}

Returns the full proposal record for a project: every bidder's legal name,
13-digit TIN, proposal price, pass/fail flag, and (for the winner) the
agreed contract price. Works across all methodIds (e-bidding, สอบราคา,
เฉพาะเจาะจง) and budget years 2014→present. No encrypted projectId, no
template chain, no PDF parsing — only a CDP-warmed Chrome session is needed
to bypass F5/Cloudflare and inherit cookies for ctx.request.

Earlier rounds of this spike chased PDF endpoints (greenBook →
infoApproveTemplate → view-pdf-file) before discovering getProcureResult.
Those are kept in `reference_egp_endpoints.md` as fallbacks; the JSON path
is dramatically simpler and is the primary ingestion channel for phase 1.

Prereq:
  Chrome must be running on CDP port 9231 with the project's chrome_profile/.
  The session must have hit /announcement at least once.

Usage:
  python scripts/spike_egp_html.py            # find one fresh e-bidding winner-announce
                                              # project, then dump its full bidder list

Output (data/):
  - egp_recent_projects.json    candidate projects from the search step
  - egp_procure_result_<pid>.json   getProcureResult body for the picked project
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

CDP = "http://127.0.0.1:9231"
WEB = "https://process5.gprocurement.go.th/egp-agpc01-web/announcement"
HOST = "https://process5.gprocurement.go.th"

SEARCH_API = HOST + "/egp-atpj27-service/pb/a-egp-allt-project/announcement"
PROCURE_RESULT = SEARCH_API + "/getProcureResult"


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


def capture_token(page) -> str | None:
    """Trigger a search and read the announcementToken the SPA writes to sessionStorage."""
    try:
        page.bring_to_front()
    except Exception:
        pass
    btn = page.query_selector("button:has-text('ค้นหา')")
    if btn and btn.is_enabled():
        try:
            btn.click(timeout=4000)
        except Exception:
            pass
        page.wait_for_timeout(3000)
    try:
        raw = page.evaluate("() => sessionStorage.getItem('announcementData')")
        if not raw:
            return None
        obj = json.loads(raw)
        return ((obj.get("searchForm") or {}).get("announcementToken")) or None
    except Exception:
        return None


def search_recent(ctx, token: str, budget_year: str = "2569", page_num: int = 1) -> list[dict]:
    r = ctx.request.get(
        SEARCH_API,
        params={
            "budgetYear": budget_year,
            "announcementTodayFlag": "false",
            "page": str(page_num),
            "announcementToken": token,
        },
        headers={"Referer": WEB, "Accept": "application/json"},
    )
    if r.status != 200 or "json" not in r.headers.get("content-type", ""):
        return []
    j = r.json()
    return (j.get("data") or {}).get("data") or []


def fetch_procure_result(ctx, pid: str) -> dict:
    r = ctx.request.get(
        PROCURE_RESULT,
        params={"projectId": pid},
        headers={"Referer": WEB, "Accept": "application/json"},
    )
    if r.status != 200:
        return {"_status": r.status, "_body": r.text()[:300]}
    try:
        return r.json()
    except Exception as e:
        return {"_parse_error": str(e), "_body": r.text()[:300]}


def summarize(result: dict) -> None:
    data = result.get("data") or {}
    groups = data.get("procureResultList") or []
    print(f"   procureResultList: {len(groups)} consider-group(s)")
    for grp in groups:
        bidders = grp.get("procureResultDataResponse") or []
        print(f"   group: {(grp.get('considerDesc') or '')[:80]!r}  bidders={len(bidders)}")
        for bd in bidders:
            mark = "★" if bd.get("priceAgree") else " "
            name = (bd.get("receiveNameTh") or "")[:42]
            tin = bd.get("receiveTin") or ""
            price = bd.get("priceProposal")
            flag = bd.get("resultFlag")
            print(f"     {mark} {name:<42} tin={tin:<14} price={price}  flag={flag}")


def main() -> int:
    print(f"[+] connecting to Chrome via CDP {CDP}")
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP)
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        page = find_or_open_announcement_tab(ctx)
        print(f"[+] using tab: {page.url}")

        token = capture_token(page)
        if not token:
            print("[!] failed to capture announcementToken (open the SPA and click ค้นหา manually, then re-run)")
            return 1
        print(f"[+] token len={len(token)}")

        # Pull a few candidate projects across recent budget years.
        candidates: list[dict] = []
        for by in ("2569", "2568"):
            items = search_recent(ctx, token, budget_year=by, page_num=1)
            print(f"    budgetYear={by}: {len(items)} items")
            candidates.extend(items)
            if len(candidates) >= 10:
                break

        # prefer e-bidding (methodId=16) since เฉพาะเจาะจง has only 1 bidder by design
        ebidding = [c for c in candidates if str(c.get("methodId")) == "16"]
        pool = ebidding or candidates
        if not pool:
            print("[!] no candidates")
            return 2

        (DATA / "egp_recent_projects.json").write_text(
            json.dumps([{
                "projectId": c.get("projectId"),
                "projectName": (c.get("projectName") or "")[:160],
                "methodId": c.get("methodId"),
                "stepId": c.get("stepId"),
                "flowName": c.get("flowName"),
                "deptSubName": c.get("deptSubName"),
            } for c in candidates], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"[+] saved {len(candidates)} candidates -> data/egp_recent_projects.json")

        # Probe up to 3 different projects so we see realistic shape variation
        for c in pool[:3]:
            pid = str(c.get("projectId") or "")
            if not pid:
                continue
            print(f"\n--- pid={pid}  methodId={c.get('methodId')}  flow={c.get('flowName')} ---")
            result = fetch_procure_result(ctx, pid)
            (DATA / f"egp_procure_result_{pid}.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            rc = (result.get("response") or {}).get("responseCode")
            if rc != "0":
                desc = (result.get("response") or {}).get("description")
                print(f"   responseCode={rc} desc={desc!r}")
                continue
            summarize(result)

    print("\n[+] spike 2 done. getProcureResult is the primary bidder-list endpoint.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
