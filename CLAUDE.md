# BidWise — Project Memory

## Goal
SaaS for Thai gov procurement **bidder analytics** (not just listings). Differentiator vs competitors (G-LEAD, biddingthai, ACT Ai): real-time bidder list + prices + qualification status per project, derived from e-GP HTML + PDF "รายงานผลการพิจารณา" OCR.

Target persona: **vendors who bid and lose** — willing to pay 1.5–5K THB/month for win-rate analytics, opponent intel, and price benchmarks.

## Architecture
Mirrors `D:/0_product_dev/smart_e_gp/` pattern but **independently coded** (IP separation):
- `backend/` — FastAPI + SQLAlchemy + Postgres
- `scripts/` — scrapers (e-GP HTML, ACT CSV, PDF OCR)
- `alma/` — PaddleOCR pipeline (Thai PP-OCRv5)
- `frontend/` — Next.js (deferred until backend stable)

## Ports (project-specific)
| Service | Port |
|---|---|
| Backend FastAPI | **8200** |
| Frontend Next.js | **5800** |
| Chrome CDP | **9231** |
| Postgres | 5432 (shared instance, DB `bid_wise`) |

## Data sources (verified 2026-05-01)
| Channel | Coverage | Refresh | Use |
|---|---|---|---|
| ACT Ai bulk CSV (`opendata.actai.co/dataset/ds_001_007`) | bidder name + tax ID, NO prices | every 6 mo | bootstrap historical |
| e-GP per-project HTML (`process3.gprocurement.go.th/egp2procmainWeb/.../procsearch.sch?pid=...`) | bidder list, qualification | real-time | live scraping |
| PDF "รายงานผลการพิจารณา" (e-GP attachment) | bidder + price + qualified Y/N + reasoning | real-time | **moat — full picture, OCR required** |

Coverage caveat: only **e-bidding** projects have full bidder data. **เฉพาะเจาะจง** (~50% of records) has only winner.

Legal basis: พ.ร.บ.จัดซื้อจัดจ้าง 2560 มาตรา 66 — agencies MUST publicly disclose all bidders + prices + qualification.

## What NOT to do
- **No code/data import from `D:/0_product_dev/smart_e_gp/`** — that codebase is owned by user's employer (Appworks). BidWise is a personal side project.
- **No use of `egp_scraper_profile` Chrome profile** — fresh profile under `chrome_profile/` only.
- **No shared Postgres DB** — `bid_wise` DB only.

## Status
Phase 0 — spike validation in progress. Three scripts under `scripts/spike_*.py` verify data sources before scaffolding full pipeline.
