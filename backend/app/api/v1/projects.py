"""Project listing + detail endpoints.

Filter conventions follow smart_e_gp pattern (snake_case query params, AND
combination, distinct-values options endpoint) but the filter set is
vendor-focused: method, step, province, budget range, bidder count bucket,
has-bidder-data, date range. No IT segment / tech stack — bid_wise is
method-agnostic.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.core.database import get_db
from app.models import (
    Project,
    Department,
    Bidder,
    Announcement,
    TorAnalysis,
)
from app.schemas import (
    ProjectListItem,
    ProjectListResponse,
    ProjectDetail,
    ProjectFilterOptions,
    BidderItem,
    AnnouncementItem,
)

router = APIRouter(prefix="/projects", tags=["projects"])

# Static labels — would normally come from /egp-rdb-service/listProcureMethod
# but those rarely change; cache here for response speed.
METHOD_LABELS: dict[str, str] = {
    "01": "ตกลงราคา",
    "02": "สอบราคา",
    "03": "ประกวดราคา",
    "16": "ประกวดราคาอิเล็กทรอนิกส์ (e-bidding)",
    "17": "ประกวดราคาอิเล็กทรอนิกส์ (e-market)",
    "19": "เฉพาะเจาะจง",
}
STEP_LABELS: dict[str, str] = {
    "M03": "หนังสือเชิญชวน/ประกาศเชิญชวน",
    "W03": "อนุมัติสั่งซื้อสั่งจ้างและประกาศผู้ชนะการเสนอราคา",
    "X01": "ประกาศผู้ชนะการเสนอราคา",
    "I03": "จัดทำสัญญา/บริหารสัญญา",
    "C01": "ข้อมูลสาระสำคัญในสัญญา",
}
BIDDER_BUCKETS = [
    {"key": "1", "label": "1 ราย", "min": 1, "max": 1},
    {"key": "2-3", "label": "2-3 ราย", "min": 2, "max": 3},
    {"key": "4+", "label": "4 รายขึ้นไป", "min": 4, "max": None},
    {"key": "0", "label": "ยังไม่มีข้อมูลผู้เสนอ", "min": 0, "max": 0},
]


def _bidder_count_subq(db: Session):
    return (
        db.query(Bidder.project_id, func.count(Bidder.id).label("n"))
        .group_by(Bidder.project_id)
        .subquery()
    )


@router.get("/options", response_model=ProjectFilterOptions)
def filter_options(db: Session = Depends(get_db)) -> ProjectFilterOptions:
    """Distinct-value endpoint that powers dropdown / chip data on the home page."""
    methods_in_use = (
        db.query(Project.method_id).filter(Project.method_id.isnot(None)).distinct().all()
    )
    methods = [
        {"id": m[0], "name": METHOD_LABELS.get(m[0], m[0])}
        for m in sorted(methods_in_use, key=lambda x: x[0] or "")
    ]
    steps_in_use = (
        db.query(Project.step_id).filter(Project.step_id.isnot(None)).distinct().all()
    )
    steps = [
        {"id": s[0], "name": STEP_LABELS.get(s[0], s[0])}
        for s in sorted(steps_in_use, key=lambda x: x[0] or "")
    ]
    provinces_in_use = (
        db.query(Project.province_moi_id, Project.province_moi_name)
        .filter(Project.province_moi_id.isnot(None))
        .distinct()
        .all()
    )
    provinces = [
        {"id": p[0], "name": p[1] or p[0]}
        for p in sorted(provinces_in_use, key=lambda x: x[0] or "")
    ]
    money_min = db.query(func.min(Project.project_money)).scalar() or Decimal("0")
    money_max = db.query(func.max(Project.project_money)).scalar() or Decimal("0")
    return ProjectFilterOptions(
        methods=methods,
        steps=steps,
        provinces=provinces,
        budget_min=money_min,
        budget_max=money_max,
        bidder_count_buckets=[
            {"key": b["key"], "label": b["label"]} for b in BIDDER_BUCKETS
        ],
    )


@router.get("", response_model=ProjectListResponse)
def list_projects(
    db: Session = Depends(get_db),
    q: str | None = Query(None, description="freetext over project_id / name / dept"),
    method_id: list[str] | None = Query(None),
    step_id: list[str] | None = Query(None),
    province_moi_id: list[str] | None = Query(None),
    min_budget: Decimal | None = Query(None),
    max_budget: Decimal | None = Query(None),
    bidder_count: list[str] | None = Query(None, description="bucket keys: 1 / 2-3 / 4+ / 0"),
    has_bidder_data: bool | None = Query(None),
    announce_from: datetime | None = Query(None),
    announce_to: datetime | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("announce_date"),
    sort_order: str = Query("desc"),
) -> ProjectListResponse:
    bidder_sq = _bidder_count_subq(db)

    base = (
        db.query(
            Project,
            Department.dept_sub_name.label("dept_sub_name"),
            func.coalesce(bidder_sq.c.n, 0).label("bidder_count"),
        )
        .outerjoin(Department, Department.dept_sub_id == Project.dept_sub_id)
        .outerjoin(bidder_sq, bidder_sq.c.project_id == Project.project_id)
    )

    conditions = []
    if q:
        like = f"%{q}%"
        conditions.append(
            or_(
                Project.project_id.ilike(like),
                Project.project_name.ilike(like),
                Department.dept_sub_name.ilike(like),
            )
        )
    if method_id:
        conditions.append(Project.method_id.in_(method_id))
    if step_id:
        conditions.append(Project.step_id.in_(step_id))
    if province_moi_id:
        conditions.append(Project.province_moi_id.in_(province_moi_id))
    if min_budget is not None:
        conditions.append(Project.project_money >= min_budget)
    if max_budget is not None:
        conditions.append(Project.project_money <= max_budget)
    if announce_from:
        conditions.append(Project.announce_date >= announce_from)
    if announce_to:
        conditions.append(Project.announce_date <= announce_to)

    if bidder_count:
        bucket_conds = []
        for key in bidder_count:
            bucket = next((b for b in BIDDER_BUCKETS if b["key"] == key), None)
            if bucket is None:
                continue
            n = func.coalesce(bidder_sq.c.n, 0)
            if bucket["max"] is None:
                bucket_conds.append(n >= bucket["min"])
            else:
                bucket_conds.append(and_(n >= bucket["min"], n <= bucket["max"]))
        if bucket_conds:
            conditions.append(or_(*bucket_conds))

    if has_bidder_data is True:
        conditions.append(func.coalesce(bidder_sq.c.n, 0) > 0)
    elif has_bidder_data is False:
        conditions.append(func.coalesce(bidder_sq.c.n, 0) == 0)

    if conditions:
        base = base.filter(and_(*conditions))

    total = base.count()

    sort_map = {
        "announce_date": Project.announce_date,
        "project_money": Project.project_money,
        "price_build": Project.price_build,
        "price_agree": Project.price_agree,
        "project_name": Project.project_name,
        "bidder_count": func.coalesce(bidder_sq.c.n, 0),
    }
    sort_col = sort_map.get(sort_by, Project.announce_date)
    sort_col = sort_col.desc() if sort_order.lower() == "desc" else sort_col.asc()

    rows = base.order_by(sort_col, Project.project_id.desc()).offset((page - 1) * page_size).limit(page_size).all()

    items: list[ProjectListItem] = []
    for proj, dept_name, count in rows:
        items.append(ProjectListItem(
            project_id=proj.project_id,
            project_name=proj.project_name,
            method_id=proj.method_id,
            step_id=proj.step_id,
            project_status=proj.project_status,
            project_money=proj.project_money,
            price_build=proj.price_build,
            price_agree=proj.price_agree,
            announce_date=proj.announce_date,
            dept_sub_id=proj.dept_sub_id,
            dept_sub_name=dept_name,
            province_moi_id=proj.province_moi_id,
            province_moi_name=proj.province_moi_name,
            bidder_count=int(count or 0),
            has_bidder_data=int(count or 0) > 0,
        ))

    return ProjectListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{project_id}", response_model=ProjectDetail)
def project_detail(project_id: str, db: Session = Depends(get_db)) -> ProjectDetail:
    proj = db.get(Project, project_id)
    if proj is None:
        raise HTTPException(status_code=404, detail=f"project_id {project_id} not found")
    dept_name = None
    if proj.dept_sub_id:
        dept = db.get(Department, proj.dept_sub_id)
        dept_name = dept.dept_sub_name if dept else None
    bidders_q = (
        db.query(Bidder).filter_by(project_id=project_id).order_by(Bidder.is_winner.desc(), Bidder.price_proposal.asc()).all()
    )
    announcements_q = (
        db.query(Announcement).filter_by(project_id=project_id).order_by(Announcement.announce_date.asc()).all()
    )
    tor = db.query(TorAnalysis).filter_by(project_id=project_id).order_by(TorAnalysis.id.desc()).first()
    return ProjectDetail(
        project_id=proj.project_id,
        project_name=proj.project_name,
        method_id=proj.method_id,
        type_id=proj.type_id,
        step_id=proj.step_id,
        project_status=proj.project_status,
        project_money=proj.project_money,
        price_build=proj.price_build,
        price_agree=proj.price_agree,
        project_cost=proj.project_cost,
        project_cost_name=proj.project_cost_name,
        deliver_day=proj.deliver_day,
        announce_date=proj.announce_date,
        announce_winner_date=proj.announce_winner_date,
        report_date=proj.report_date,
        dept_sub_id=proj.dept_sub_id,
        dept_sub_name=dept_name,
        province_moi_id=proj.province_moi_id,
        province_moi_name=proj.province_moi_name,
        plan_id=proj.plan_id,
        bidders=[BidderItem.model_validate(b) for b in bidders_q],
        announcements=[AnnouncementItem.model_validate(a) for a in announcements_q],
        has_tor_analysis=tor is not None,
        tor_analysis_status=tor.status if tor else None,
    )
