"""Single-project ingestion: pull every public e-GP datum we know about
for a given projectId and persist it to the bid_wise Postgres DB.

What it pulls (verified Tier-1 channels, 2026-05-01):
  1. getProcurementDetail        → project meta (name, dept, money, dates)
  2. getProcureResult            → bidder list with TIN + price + result_flag + winner
  3. greenBook(mode=LINK)        → announcement lifecycle (B0/D0/D1/W0/price/BOQ)
  4. infoProcureDocAnnounZip     → zipId of the announcement ZIP
  5. egp-upload-service download → binary ZIP, list entries (PDFs + bond templates + xlsx)
  6. infoApproveTemplate(D1)     → templateId for the rolled-up TOR/BOQ PDF
  7. view-pdf-file(templateId)   → binary PDF (text-based, pdfplumber-friendly)
  8. infoApproveTemplate(W13)    → templateId for winner-announce PDF (when present)
  9. getMixplanId(planId)        → mix_plan_id (when project links to a plan)
 10. process3 RDBI0006/PRINT     → APLT plan-announcement HTML (tis-620 charset)

DB writes are upsert-style (read-then-update) so reruns are idempotent.
ZIP + PDF binaries are stored under data/zips/, data/pdfs/, data/plans/.

Usage:
    python scripts/ingest_project.py 69039576531
    python scripts/ingest_project.py 69049064467 69029427181        # multiple

Prereq: Chrome on CDP 9231 with a warmed /announcement session.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import sys
import zipfile
from datetime import datetime, date
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.database import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Department,
    Vendor,
    ProcurementPlan,
    Project,
    Announcement,
    Bidder,
    JointVentureMember,
    DocumentZip,
    DocumentFile,
    PdfTemplate,
)

import pdfplumber  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

CDP = "http://127.0.0.1:9231"
WEB = "https://process5.gprocurement.go.th/egp-agpc01-web/announcement"
H5 = "https://process5.gprocurement.go.th"
H3 = "https://process3.gprocurement.go.th"

DETAIL = H5 + "/egp-atpj27-service/pb/a-egp-allt-project/announcement/getProcurementDetail"
PROCURE_RESULT = H5 + "/egp-atpj27-service/pb/a-egp-allt-project/announcement/getProcureResult"
GREENBOOK = H5 + "/egp-atpj27-service/pb/a-egp-allt-project/announcement/greenBook"
INFO_ZIP = H5 + "/egp-approval-service/apv-common/infoProcureDocAnnounZip"
DOWNLOAD_FILE = H5 + "/egp-upload-service/v1/downloadFileTest"
INFO_TPL = H5 + "/egp-approval-service/apv-common/infoApproveTemplate"
VIEW_PDF = H5 + "/egp-template-service/dwnt/view-pdf-file"
GET_MIXPLAN = H5 + "/egp-atpj27-service/pb/a-egp-allt-project/announcement/getMixplanId"
PRINT_PLAN = H3 + "/eGPProcure/secureds/RDBI0006/PRINT"

ZIP_DIR = ROOT / "data" / "zips"
PDF_DIR = ROOT / "data" / "pdfs"
EXTRACT_DIR = ROOT / "data" / "extracts"
PLAN_DIR = ROOT / "data" / "plans"
for d in (ZIP_DIR, PDF_DIR, EXTRACT_DIR, PLAN_DIR):
    d.mkdir(parents=True, exist_ok=True)

REF_HEADERS = {"Referer": WEB, "Accept": "application/json"}


def _parse_dt(v):
    if not v:
        return None
    if isinstance(v, (datetime, date)):
        return v
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except Exception:
        return None


def _parse_date(v):
    dt = _parse_dt(v)
    return dt.date() if isinstance(dt, datetime) else dt


def _classify_zip_entry(name: str) -> str:
    n = name.lower()
    if n.startswith("attach_tor"):
        return "attach_tor"
    if n.startswith("tor_") or n == "tor.pdf":
        return "tor"
    if n.startswith("annoudoc"):
        return "annoudoc"
    if "contract" in n:
        return "contract"
    if "bond" in n:
        return "bond"
    if "quotation" in n:
        return "quotation"
    if n.endswith(".xlsx") or n.endswith(".xls"):
        return "xlsx_template"
    return "other"


def _is_juridical(name: str) -> bool | None:
    if not name:
        return None
    keywords = ["บริษัท", "ห้างหุ้นส่วน", "หจก", "ห้าง", "บมจ", "องค์กร", "มูลนิธิ", "สมาคม", "สหกรณ์"]
    if any(k in name for k in keywords):
        return True
    if name.startswith(("นาย", "นาง", "นางสาว", "ด.ช.", "ด.ญ.")):
        return False
    return None


def _normalize_name(name: str) -> str:
    if not name:
        return ""
    s = re.sub(r"^(บริษัท|ห้างหุ้นส่วนจำกัด|ห้างหุ้นส่วนสามัญ|หจก\.?|ห้าง|ร้าน|นาย|นาง|นางสาว)\s*", "", name)
    s = re.sub(r"\s*(จำกัด \(มหาชน\)|จำกัด)$", "", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def _upsert_vendor(db, tin: str | None, name_th: str) -> str:
    """Returns the vendor key (tin or synthesized hash)."""
    if not tin:
        # synthesize stable key when TIN is missing
        h = hashlib.sha1(name_th.encode("utf-8")).hexdigest()[:12]
        tin = f"hash:{h}"
    is_masked = "XXXX" in (tin or "")
    v = db.get(Vendor, tin)
    if v is None:
        db.add(Vendor(
            tin=tin,
            name_th=name_th,
            name_normalized=_normalize_name(name_th),
            is_juridical=_is_juridical(name_th),
            is_tin_masked=is_masked,
        ))
        db.flush()  # make Vendor row visible to subsequent FK inserts
    else:
        v.name_th = name_th
        v.name_normalized = _normalize_name(name_th)
        v.is_tin_masked = is_masked
    return tin


def _upsert_department(db, dept_sub_id: str | None, dept_id: str | None, name: str | None,
                      province_id: str | None = None, province_name: str | None = None,
                      district_id: str | None = None) -> str | None:
    if not dept_sub_id:
        return None
    d = db.get(Department, dept_sub_id)
    if d is None:
        db.add(Department(
            dept_sub_id=dept_sub_id,
            dept_id=dept_id or "",
            dept_sub_name=name or "(unknown)",
            province_moi_id=province_id,
            province_moi_name=province_name,
            district_moi_id=district_id,
        ))
    else:
        if name:
            d.dept_sub_name = name
        if province_id and not d.province_moi_id:
            d.province_moi_id = province_id
            d.province_moi_name = province_name
        if district_id and not d.district_moi_id:
            d.district_moi_id = district_id
    return dept_sub_id


# --------------------------------------------------------------------------
# fetch helpers — each returns parsed JSON dict (or empty dict on miss)
# --------------------------------------------------------------------------

def fetch_detail(ctx, pid: str) -> dict:
    r = ctx.request.get(DETAIL, params={"projectId": pid}, headers=REF_HEADERS)
    if r.status != 200 or "json" not in r.headers.get("content-type", ""):
        return {}
    return r.json()


def fetch_procure_result(ctx, pid: str) -> dict:
    r = ctx.request.get(PROCURE_RESULT, params={"projectId": pid}, headers=REF_HEADERS)
    if r.status != 200 or "json" not in r.headers.get("content-type", ""):
        return {}
    return r.json()


def fetch_greenbook(ctx, pid: str, method_id: str) -> dict:
    r = ctx.request.get(
        GREENBOOK,
        params={"mode": "LINK", "methodId": method_id or "16", "tempProjectId": pid, "pageAnnounceType": "W0"},
        headers=REF_HEADERS,
    )
    if r.status != 200 or "json" not in r.headers.get("content-type", ""):
        return {}
    return r.json()


def fetch_zip_meta(ctx, pid: str) -> dict:
    r = ctx.request.get(INFO_ZIP, params={"projectId": pid}, headers=REF_HEADERS)
    if r.status != 200:
        return {}
    return r.json()


def fetch_zip_binary(ctx, zip_id: str) -> bytes:
    r = ctx.request.get(
        DOWNLOAD_FILE,
        params={"fileId": zip_id},
        headers={"Referer": WEB, "Accept": "*/*"},
    )
    return r.body() if r.status == 200 else b""


def fetch_template_meta(ctx, pid: str, template_type: str) -> dict:
    r = ctx.request.get(INFO_TPL, params={"projectId": pid, "templateType": template_type}, headers=REF_HEADERS)
    if r.status != 200:
        return {}
    try:
        return r.json()
    except Exception:
        return {}


def fetch_pdf_binary(ctx, template_id: str) -> bytes:
    r = ctx.request.get(VIEW_PDF, params={"templateId": template_id}, headers={"Referer": WEB, "Accept": "application/pdf,*/*"})
    return r.body() if r.status == 200 else b""


def fetch_mixplan_id(ctx, plan_id: str) -> str | None:
    r = ctx.request.get(GET_MIXPLAN, params={"planId": plan_id}, headers=REF_HEADERS)
    if r.status != 200:
        return None
    try:
        d = r.json().get("data") or {}
        return d.get("announRef")
    except Exception:
        return None


def fetch_plan_html(ctx, mix_plan_id: str) -> str:
    """Returns the raw template HTML, decoded from tis-620."""
    r = ctx.request.get(
        PRINT_PLAN,
        params={"mixPlanId": mix_plan_id, "templateTypeName": "APLT", "krut": "true"},
        headers={"Referer": WEB, "Accept": "application/json"},
    )
    if r.status != 200:
        return ""
    body = r.body()
    try:
        txt = body.decode("tis-620")
    except Exception:
        txt = body.decode("utf-8", errors="replace")
    try:
        return json.loads(txt).get("templateData", "") or ""
    except Exception:
        return ""


def parse_plan_html_to_fields(html: str) -> dict:
    """Best-effort regex parse of the APLT HTML for structured fields."""
    txt = re.sub(r"<[^>]+>", " ", html)
    txt = re.sub(r"&nbsp;|​", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    out: dict = {}
    m = re.search(r"ประกาศ\s+(.+?)\s+เรื่อง", txt)
    if m:
        out["dept_name"] = m.group(1).strip()
    m = re.search(r"ประกาศ\s*ณ\s*วันที่\s+(\d+)\s+(\S+)\s+พ\.ศ\.\s*(\d+)", txt)
    if m:
        out["plan_announce_date_text"] = m.group(0)
    m = re.search(r"\(\s*([^)]+?)\s*\)\s+(นายก|ผู้อำนวยการ|อธิการ|ปลัด|เลขาธิการ)[^A-Z\n]{0,80}", txt)
    if m:
        out["signed_by_name"] = m.group(1).strip()
        out["signed_by_position"] = m.group(2).strip()
    # planned project: pattern "P{digits} <name> <budget> <month/year>"
    m = re.search(r"P\d{10,14}.*?([\d,]+\.\d{2})\s+(\d{2}/\d{4})", txt)
    if m:
        try:
            out["budget"] = float(m.group(1).replace(",", ""))
        except Exception:
            pass
        out["expected_announce_month"] = m.group(2)
    return out


# --------------------------------------------------------------------------
# main per-project pipeline
# --------------------------------------------------------------------------

def ingest_one(ctx, db, pid: str) -> None:
    print(f"\n=== pid={pid} ===")

    # --- 1. detail ---
    detail = fetch_detail(ctx, pid)
    d = detail.get("data") or {}
    if not d:
        print("   [!] no detail data; skipping")
        return

    dept_sub_id = _upsert_department(
        db,
        d.get("deptSubId"), d.get("deptId"), d.get("deptSubName"),
        d.get("provinceMoiId"), d.get("moiName") or d.get("provinceMoiName"),
        d.get("districtMoiId"),
    )

    proj = db.get(Project, pid)
    if proj is None:
        proj = Project(project_id=pid)
        db.add(proj)
    proj.project_name = d.get("projectName") or proj.project_name
    proj.method_id = d.get("methodId") or proj.method_id
    proj.type_id = d.get("typeId")
    proj.type_project = d.get("typeProject")
    proj.step_id = d.get("stepId")
    proj.project_status = d.get("projectStatus")
    proj.dept_sub_id = dept_sub_id
    proj.project_money = d.get("projectMoney")
    proj.price_build = d.get("priceBuild")
    proj.price_agree = d.get("priceAgree")
    proj.project_cost = d.get("projectCost")
    proj.project_cost_name = d.get("projectCostName")
    proj.min_quality_score = d.get("minQualityScore")
    proj.announce_date = _parse_dt(d.get("announceDate"))
    proj.announce_winner_date = _parse_dt(d.get("announceWinnerDate"))
    proj.report_date = _parse_dt(d.get("reportDate"))
    proj.deliver_day = d.get("deliverDay")
    proj.province_moi_id = d.get("provinceMoiId")
    proj.province_moi_name = d.get("moiName")
    proj.raw_detail = d
    db.flush()
    print(f"   [+] project upserted  method={proj.method_id} step={proj.step_id} money={proj.project_money}")

    # --- 2. procureResult (bidder list) ---
    pr = fetch_procure_result(ctx, pid)
    pr_data = pr.get("data") or {}
    proj.raw_procure_result = pr_data or None
    groups = pr_data.get("procureResultList") or []
    n_bidders = 0
    if groups:
        # wipe existing bidder rows so reruns reflect updates
        for old in db.query(Bidder).filter_by(project_id=pid).all():
            db.query(JointVentureMember).filter_by(bidder_id=old.id).delete()
            db.delete(old)
        db.flush()
        for gi, grp in enumerate(groups, 1):
            for bd in grp.get("procureResultDataResponse") or []:
                name = (bd.get("receiveNameTh") or "").strip()
                tin_raw = (bd.get("receiveTin") or "").strip() or None
                tin = _upsert_vendor(db, tin_raw, name)
                row = Bidder(
                    project_id=pid,
                    vendor_tin=tin,
                    consider_desc=grp.get("considerDesc"),
                    consider_seq=gi,
                    receive_name_th=name,
                    price_proposal=bd.get("priceProposal"),
                    price_agree=bd.get("priceAgree"),
                    result_flag=(bd.get("resultFlag") or "").strip() or None,
                    score_type_id=(bd.get("scoreTypeId") or "").strip() or None,
                    is_winner=bool(bd.get("priceAgree")),
                )
                db.add(row)
                db.flush()
                # JV members
                for jv in bd.get("jointVentureAndConsortiumsResponseList") or []:
                    jv_name = (jv.get("receiveNameTh") or jv.get("memberNameTh") or "").strip()
                    jv_tin = (jv.get("receiveTin") or jv.get("memberTin") or "").strip() or None
                    if jv_name:
                        jv_tin_key = _upsert_vendor(db, jv_tin, jv_name)
                        db.add(JointVentureMember(
                            bidder_id=row.id,
                            member_tin=jv_tin_key,
                            member_name_th=jv_name,
                        ))
                n_bidders += 1
    print(f"   [+] bidders: {n_bidders} across {len(groups)} consider-group(s)")

    # --- 3. greenBook → announcement lifecycle ---
    gb = fetch_greenbook(ctx, pid, str(proj.method_id or ""))
    gb_data = gb.get("data") or {}
    proj.raw_greenbook = gb_data or None
    items = gb_data.get("greenBookAnnouncementTypeLinkDto") or []
    if items:
        db.query(Announcement).filter_by(project_id=pid).delete()
        db.flush()
        for it in items:
            db.add(Announcement(
                project_id=pid,
                announce_type=(it.get("announceType") or "").strip(),
                announce_type_desc=(it.get("announceTypeDesc") or None),
                template_type=(it.get("templateType") or None),
                seq_no=it.get("seqNo"),
                no=str(it.get("no") or "")[:8] or None,
                announce_date=_parse_date(it.get("announceDate")),
                price_build=it.get("priceBuild"),
            ))
    print(f"   [+] announcements: {len(items)}")

    # --- 4 + 5. ZIP meta + binary + entry list ---
    zm = fetch_zip_meta(ctx, pid)
    zm_data = (zm.get("data") or {})
    zip_id = zm_data.get("zipId")
    if zip_id:
        existing_zip = db.query(DocumentZip).filter_by(project_id=pid).first()
        if existing_zip is None or not existing_zip.file_path or not Path(existing_zip.file_path).exists():
            zip_bytes = fetch_zip_binary(ctx, zip_id)
            if zip_bytes.startswith(b"PK"):
                zpath = ZIP_DIR / f"{pid}.zip"
                zpath.write_bytes(zip_bytes)
                sha = hashlib.sha1(zip_bytes).hexdigest()
                if existing_zip is None:
                    existing_zip = DocumentZip(project_id=pid, zip_id=zip_id)
                    db.add(existing_zip)
                existing_zip.zip_id = zip_id
                existing_zip.build_name1 = zm_data.get("buildName1")
                existing_zip.build_name2 = zm_data.get("buildName2")
                existing_zip.file_path = str(zpath.relative_to(ROOT))
                existing_zip.size_bytes = len(zip_bytes)
                existing_zip.sha1 = sha
                # list entries
                z = zipfile.ZipFile(io.BytesIO(zip_bytes))
                names = z.namelist()
                existing_zip.n_entries = len(names)
                db.flush()
                # wipe + re-record file metadata (no extraction yet)
                db.query(DocumentFile).filter_by(zip_id=existing_zip.id).delete()
                db.flush()
                for n in names:
                    info = z.getinfo(n)
                    db.add(DocumentFile(
                        zip_id=existing_zip.id,
                        project_id=pid,
                        name=n,
                        kind=_classify_zip_entry(n),
                        size_bytes=info.file_size,
                    ))
                print(f"   [+] ZIP downloaded {len(zip_bytes):,} bytes, {len(names)} entries -> {zpath.name}")
            else:
                print(f"   [!] ZIP fetch failed (not PK header)")
        else:
            print(f"   [+] ZIP already on disk: {existing_zip.file_path}")
    else:
        print(f"   [-] no zipId from infoProcureDocAnnounZip")

    # --- 6 + 7 + 8. PDFs (D1 ราคากลาง, W13 winner) ---
    for ttype in ("D1", "W13"):
        meta = fetch_template_meta(ctx, pid, ttype)
        m = (meta.get("data") or {})
        tid = m.get("templateId") if isinstance(m, dict) else None
        if not tid:
            continue
        existing = db.query(PdfTemplate).filter_by(project_id=pid, template_type=ttype).first()
        if existing and existing.file_path and Path(existing.file_path).exists():
            print(f"   [+] PDF {ttype} already on disk")
            continue
        pdf = fetch_pdf_binary(ctx, tid)
        if not pdf.startswith(b"%PDF"):
            continue
        ppath = PDF_DIR / f"{pid}_{ttype}.pdf"
        ppath.write_bytes(pdf)
        text = ""
        try:
            with pdfplumber.open(ppath) as pp:
                text = "\n".join((page.extract_text() or "") for page in pp.pages)
        except Exception as e:
            print(f"   [!] pdfplumber: {e}")
        if existing is None:
            existing = PdfTemplate(project_id=pid, template_type=ttype, template_id=tid)
            db.add(existing)
        existing.template_id = tid
        existing.template_name = (m.get("templateName") or "").strip() or None
        existing.file_path = str(ppath.relative_to(ROOT))
        existing.size_bytes = len(pdf)
        existing.sha1 = hashlib.sha1(pdf).hexdigest()
        existing.extracted_text = text
        print(f"   [+] PDF {ttype}  {len(pdf):,}B  text_chars={len(text)}")

    # --- 9 + 10. Procurement plan reverse lookup ---
    plan_id = (d.get("planId") or "").strip()
    if plan_id:
        mix_id = fetch_mixplan_id(ctx, plan_id)
        plan = db.get(ProcurementPlan, plan_id)
        if plan is None:
            plan = ProcurementPlan(plan_id=plan_id)
            db.add(plan)
        plan.mix_plan_id = mix_id or plan.mix_plan_id
        plan.dept_sub_id = dept_sub_id
        plan.budget_year = (d.get("budgetYear") or proj.raw_detail.get("budgetYear") if proj.raw_detail else None) or plan.budget_year
        if mix_id:
            html = fetch_plan_html(ctx, mix_id)
            if html:
                plan.raw_html = html
                fields = parse_plan_html_to_fields(html)
                if fields.get("budget"):
                    plan.budget = fields["budget"]
                if fields.get("expected_announce_month"):
                    plan.expected_announce_month = fields["expected_announce_month"]
                if fields.get("signed_by_name"):
                    plan.signed_by_name = fields["signed_by_name"]
                if fields.get("signed_by_position"):
                    plan.signed_by_position = fields["signed_by_position"]
                # also dump raw plan HTML to disk for debugging
                (PLAN_DIR / f"{plan_id}.html").write_text(html, encoding="utf-8")
        proj.plan_id = plan_id
        print(f"   [+] plan_id={plan_id} mix_plan_id={mix_id}")

    db.commit()
    print(f"   [✓] committed pid={pid}")


def main(pids: list[str]) -> int:
    if not pids:
        print("usage: ingest_project.py <pid> [<pid> …]")
        return 2
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP)
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        # warm session if no /announcement tab is open
        warm = next((x for x in ctx.pages if "egp-agpc01-web/announcement" in x.url), None)
        if warm is None:
            warm = ctx.new_page()
            warm.goto(WEB, wait_until="domcontentloaded", timeout=60000)
            warm.wait_for_timeout(3000)

        db = SessionLocal()
        try:
            for pid in pids:
                try:
                    ingest_one(ctx, db, pid)
                except Exception as e:
                    db.rollback()
                    print(f"   [!] error on pid={pid}: {e}")
        finally:
            db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main([a for a in sys.argv[1:] if a]))
