from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict


class BidderItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    vendor_tin: str
    receive_name_th: str
    consider_desc: str | None = None
    price_proposal: Decimal | None = None
    price_agree: Decimal | None = None
    result_flag: str | None = None
    is_winner: bool = False


class AnnouncementItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    announce_type: str
    announce_type_desc: str | None = None
    template_type: str | None = None
    seq_no: int | None = None
    no: str | None = None
    announce_date: Any = None
    price_build: Decimal | None = None


class ProjectListItem(BaseModel):
    """Card row in the project listing — keep it lean."""
    model_config = ConfigDict(from_attributes=True)
    project_id: str
    project_name: str
    method_id: str | None = None
    step_id: str | None = None
    project_status: str | None = None
    project_money: Decimal | None = None
    price_build: Decimal | None = None
    price_agree: Decimal | None = None
    announce_date: datetime | None = None
    dept_sub_id: str | None = None
    dept_sub_name: str | None = None
    province_moi_id: str | None = None
    province_moi_name: str | None = None
    bidder_count: int = 0
    has_bidder_data: bool = False


class ProjectListResponse(BaseModel):
    items: list[ProjectListItem]
    total: int
    page: int
    page_size: int


class ProjectDetail(BaseModel):
    """Full project view — used by the detail page."""
    model_config = ConfigDict(from_attributes=True)
    project_id: str
    project_name: str
    method_id: str | None = None
    type_id: str | None = None
    step_id: str | None = None
    project_status: str | None = None
    project_money: Decimal | None = None
    price_build: Decimal | None = None
    price_agree: Decimal | None = None
    project_cost: str | None = None
    project_cost_name: str | None = None
    deliver_day: int | None = None
    announce_date: datetime | None = None
    announce_winner_date: datetime | None = None
    report_date: datetime | None = None
    dept_sub_id: str | None = None
    dept_sub_name: str | None = None
    province_moi_id: str | None = None
    province_moi_name: str | None = None
    plan_id: str | None = None
    bidders: list[BidderItem] = []
    announcements: list[AnnouncementItem] = []
    has_tor_analysis: bool = False
    tor_analysis_status: str | None = None


class ProjectFilterOptions(BaseModel):
    methods: list[dict]              # [{id: "16", name: "ประกวดราคาอิเล็กทรอนิกส์"}]
    steps: list[dict]                # [{id: "W03", name: "ประกาศผู้ชนะ"}]
    provinces: list[dict]            # [{id: "10", name: "กรุงเทพ"}]
    budget_min: Decimal
    budget_max: Decimal
    bidder_count_buckets: list[dict] # [{key: "1", label: "1 ราย"}, ...]
