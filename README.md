# BidWise

Thai government procurement intelligence — focused on **bidder analytics**, not just listings.

## Why this exists

Existing tools (G-LEAD, biddingthai, ACT Ai) cover project listings + winners, but none surface real-time **bidder lists, prices, and qualification results** per project. Per พ.ร.บ.จัดซื้อจัดจ้าง 2560 มาตรา 66, agencies are required to disclose this — the data is public but scattered across e-GP HTML pages and PDF "รายงานผลการพิจารณา" attachments.

BidWise scrapes + OCRs that data, builds vendor profiles (win-rate, opponents, agency exposure, pricing pattern), and surfaces it for vendors who want to know **why they keep losing** and **who they're really competing against**.

## Target customer

Vendors that bid for Thai gov contracts and lose more than they win. Pricing target: 1.5–5K THB / month / seat.

## Stack

- **Backend**: FastAPI + SQLAlchemy + Postgres
- **Scraper**: Python + Playwright + Chrome CDP (port 9231)
- **OCR**: PaddleOCR (Thai PP-OCRv5) + GPU
- **Frontend**: Next.js (deferred until backend + spike pass)

## Ports

| Service | Port |
|---|---|
| Backend FastAPI | 8200 |
| Frontend Next.js | 5800 |
| Chrome CDP | 9231 |
| Postgres | 5432 (DB: `bid_wise`) |

## Status

Phase 0 — **Spike validation**. Three scripts under `scripts/` verify the data sources before committing to full build:

- `scripts/spike_act_csv.py` — ACT Ai bulk bidder CSV
- `scripts/spike_egp_html.py` — e-GP per-project HTML (process3.gprocurement.go.th)
- `scripts/spike_pdf_ocr.py` — PDF "รายงานผลการพิจารณา" OCR

## Setup

```bash
# Backend
cd backend
python -m venv venv
venv/Scripts/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8200
```

## Origin & IP separation

Architecture pattern (FastAPI + SQLAlchemy + Playwright + PaddleOCR) is mirrored from a sibling project `D:/0_product_dev/smart_e_gp/`, but **all code in this repo is independently written** — no file copy, no shared DB, no shared Chrome profile.
