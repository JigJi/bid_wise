"""
Spike 2: e-GP per-project — discover the bidder list endpoint

Strategy (validated 2026-05-01):
  1. Open the public announcement SPA in headless Chromium so the F5 BIG-IP
     ASM + Cloudflare Turnstile gates issue real cookies + UA.
  2. Listen for any outbound XHR whose URL contains `announcementToken`,
     capture the token (it's session-scoped, JS-injected per page load).
  3. Use the token to call the search API and collect a few recent project IDs
     across announceType 1 + 2.
  4. For each candidate pid, open its detail page in the same browser context
     and intercept *every* JSON XHR — that surfaces whichever endpoint the SPA
     uses to render the bidder/qualification panel.

Output:
  - data/egp_token_sample.json     captured token + cookies (do not commit)
  - data/egp_recent_projects.json  search-API results
  - data/egp_detail_<pid>.json     full detail JSON per candidate project
  - data/egp_detail_<pid>_xhrs.json list of every JSON URL the detail page hit
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

WEB = "https://process5.gprocurement.go.th/egp-agpc01-web/announcement"
SEARCH_API = "https://process5.gprocurement.go.th/egp-atpj27-service/pb/a-egp-allt-project/announcement"
SUMMARY_API = SEARCH_API + "/sumProjectMoneyAndCount"
DETAIL_API = SEARCH_API + "/getProcurementDetail"


def capture_token(page) -> str | None:
    """Listen for any request whose URL carries an announcementToken query param."""
    captured: list[str] = []

    def on_req(req):
        if "announcementToken" in req.url:
            qs = parse_qs(urlparse(req.url).query)
            tok = qs.get("announcementToken", [None])[0]
            if tok and tok not in captured:
                captured.append(tok)

    page.on("request", on_req)
    return captured


def search_recent(ctx, token: str, day: str, atype: str = "2", page_num: int = 1) -> list[dict]:
    params = {
        "announceType": atype,
        "announceSDate": day,
        "announceEDate": day,
        "announcementTodayFlag": "false",
        "page": str(page_num),
        "announcementToken": token,
    }
    r = ctx.request.get(SEARCH_API, params=params, headers={"Referer": WEB, "Accept": "application/json"})
    if r.status != 200 or "json" not in r.headers.get("content-type", ""):
        print(f"   [!] search returned status={r.status} ct={r.headers.get('content-type')}")
        return []
    j = r.json()
    return (j.get("data") or {}).get("data") or []


def fetch_detail(ctx, pid: str) -> dict:
    r = ctx.request.get(f"{DETAIL_API}?projectId={pid}", headers={"Referer": WEB, "Accept": "application/json"})
    if r.status != 200:
        return {"_status": r.status, "_body": r.text()[:300]}
    try:
        return r.json()
    except Exception as e:
        return {"_parse_error": str(e), "_body": r.text()[:300]}


def probe_detail_page(ctx, pid: str) -> list[dict]:
    """Open the detail SPA page and capture every JSON XHR it fires."""
    detail_url = f"{WEB}/detail/{pid}"
    page = ctx.new_page()
    xhrs: list[dict] = []

    def on_resp(resp):
        u = resp.url
        ct = resp.headers.get("content-type", "")
        if "gprocurement" in u and "json" in ct:
            try:
                body = resp.body()
                size = len(body)
            except Exception:
                size = -1
            xhrs.append({
                "url": u,
                "method": resp.request.method,
                "status": resp.status,
                "size": size,
                "path": urlparse(u).path,
                "params": list(parse_qs(urlparse(u).query).keys()),
            })

    page.on("response", on_resp)
    print(f"   [+] opening detail page for pid={pid}")
    try:
        page.goto(detail_url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(8000)
    except Exception as e:
        print(f"   [!] navigation error: {e}")
    page.close()
    return xhrs


def main() -> int:
    print(f"[+] launching headless browser, warming session against {WEB}")
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(locale="th-TH")
        page = ctx.new_page()

        captured = capture_token(page)
        page.goto(WEB, wait_until="domcontentloaded", timeout=45000)
        # SPA fires a few requests on initial render — give it a couple seconds
        page.wait_for_timeout(6000)

        # If the page still hasn't fired a token-bearing XHR, force one by
        # calling the bypasscloudflare endpoint via the page.
        for _ in range(3):
            if captured:
                break
            page.wait_for_timeout(2000)

        if not captured:
            print("[!] failed to capture announcementToken from page traffic")
            print("    workaround: try clicking a search filter / date input to force XHR")
            b.close()
            return 1

        token = captured[0]
        cookies = ctx.cookies()
        print(f"[+] captured token (len={len(token)})  cookies={len(cookies)}")
        (DATA_DIR / "egp_token_sample.json").write_text(
            json.dumps({"token_len": len(token), "cookies_count": len(cookies)}, indent=2),
            encoding="utf-8",
        )

        # Search recent projects. Start with today; if empty, walk back a few days.
        candidates: list[dict] = []
        today = datetime.now().date()
        for offset in range(0, 8):
            day = (today - timedelta(days=offset)).strftime("%Y-%m-%d")
            for atype in ("1", "2"):
                items = search_recent(ctx, token, day, atype=atype, page_num=1)
                print(f"    {day} type={atype}: {len(items)} items")
                candidates.extend(items[:5])
                if len(candidates) >= 10:
                    break
            if len(candidates) >= 10:
                break

        (DATA_DIR / "egp_recent_projects.json").write_text(
            json.dumps([{
                "projectId": c.get("projectId"),
                "projectName": (c.get("projectName") or "")[:120],
                "announceType": c.get("announceType"),
                "announceDate": c.get("announceDate"),
                "flowName": c.get("flowName"),
                "stepId": c.get("stepId"),
                "deptSubName": c.get("deptSubName"),
            } for c in candidates], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\n[+] saved {len(candidates)} candidate(s) -> data/egp_recent_projects.json")

        # Pick up to 3 candidates and probe their detail pages
        probe_n = min(3, len(candidates))
        for c in candidates[:probe_n]:
            pid = str(c.get("projectId"))
            print(f"\n--- pid={pid}  type={c.get('announceType')}  flow={c.get('flowName')} ---")
            detail = fetch_detail(ctx, pid)
            (DATA_DIR / f"egp_detail_{pid}.json").write_text(
                json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            xhrs = probe_detail_page(ctx, pid)
            (DATA_DIR / f"egp_detail_{pid}_xhrs.json").write_text(
                json.dumps(xhrs, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"   captured {len(xhrs)} JSON XHRs:")
            seen_paths: set[str] = set()
            for x in xhrs:
                if x["path"] in seen_paths:
                    continue
                seen_paths.add(x["path"])
                print(f"     {x['status']}  {x['size']:>7}B  {x['path']}")

        b.close()

    print("\n[+] done. inspect data/egp_detail_<pid>_xhrs.json for the bidder endpoint.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
