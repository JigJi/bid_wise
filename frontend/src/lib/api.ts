/**
 * Typed client for the bid_wise FastAPI backend (default :8200).
 * Mirrors backend/app/schemas — keep the types in sync when the API evolves.
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8200";

// ---------------------------------------------------------------- types
export type ProjectListItem = {
  project_id: string;
  project_name: string;
  method_id: string | null;
  step_id: string | null;
  project_status: string | null;
  project_money: string | null;
  price_build: string | null;
  price_agree: string | null;
  announce_date: string | null;
  dept_sub_id: string | null;
  dept_sub_name: string | null;
  province_moi_id: string | null;
  province_moi_name: string | null;
  bidder_count: number;
  has_bidder_data: boolean;
};

export type ProjectListResponse = {
  items: ProjectListItem[];
  total: number;
  page: number;
  page_size: number;
};

export type FilterOption = { id: string; name: string };
export type BucketOption = { key: string; label: string };

export type ProjectFilterOptions = {
  methods: FilterOption[];
  steps: FilterOption[];
  provinces: FilterOption[];
  budget_min: string;
  budget_max: string;
  bidder_count_buckets: BucketOption[];
};

export type BidderItem = {
  vendor_tin: string;
  receive_name_th: string;
  consider_desc: string | null;
  price_proposal: string | null;
  price_agree: string | null;
  result_flag: string | null;
  is_winner: boolean;
};

export type AnnouncementItem = {
  announce_type: string;
  announce_type_desc: string | null;
  template_type: string | null;
  seq_no: number | null;
  no: string | null;
  announce_date: string | null;
  price_build: string | null;
};

export type ProjectDetail = {
  project_id: string;
  project_name: string;
  method_id: string | null;
  type_id: string | null;
  step_id: string | null;
  project_status: string | null;
  project_money: string | null;
  price_build: string | null;
  price_agree: string | null;
  project_cost: string | null;
  project_cost_name: string | null;
  deliver_day: number | null;
  announce_date: string | null;
  announce_winner_date: string | null;
  report_date: string | null;
  dept_sub_id: string | null;
  dept_sub_name: string | null;
  province_moi_id: string | null;
  province_moi_name: string | null;
  plan_id: string | null;
  bidders: BidderItem[];
  announcements: AnnouncementItem[];
  has_tor_analysis: boolean;
  tor_analysis_status: string | null;
};

export type TorSummary = {
  project?: {
    name?: string | null;
    dept_name?: string | null;
    method?: string | null;
    announce_date_text?: string | null;
    submission_deadline_text?: string | null;
    bid_open_date_text?: string | null;
  };
  money?: {
    budget_thb?: number | null;
    price_build_thb?: number | null;
    bid_bond_thb?: number | null;
    bid_bond_pct?: number | null;
    performance_bond_pct?: number | null;
  };
  scope?: {
    thai_summary?: string;
    items?: { item: string; qty: number | null; unit: string | null; spec: string | null }[];
    delivery_days?: number | null;
    delivery_location?: string | null;
  };
  qualification?: {
    juridical_type?: string | null;
    registered_capital_min_thb?: number | null;
    paid_capital_min_thb?: number | null;
    past_work_required?: { description: string; value_min_thb: number | null; recency_years: number | null }[];
    certifications_required?: string[];
    sme_advantage?: boolean | null;
    blacklist_check?: boolean | null;
  };
  evaluation?: { criteria?: string | null; min_quality_score?: number | null };
  red_flags?: {
    unusual_qualifications?: string[];
    tight_timeline_days?: number | null;
    brand_specific?: boolean | null;
    notes?: string | null;
  };
};

export type TorAnalyzeResponse = {
  project_id: string;
  status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";
  prompt_version: string;
  model_name: string;
  summary: TorSummary | null;
  raw_response: string | null;
  error_message: string | null;
  input_tokens: number | null;
  output_tokens: number | null;
  duration_sec: string | null;
  last_run_at: string | null;
};

export type TorQAResponse = {
  answer: string;
  model: string;
  duration_sec: string;
  input_tokens: number | null;
  output_tokens: number | null;
};

// ---------------------------------------------------------------- client
async function request<T>(
  path: string,
  init: RequestInit = {},
  cache: RequestCache = "no-store",
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    cache,
    headers: {
      "Content-Type": "application/json",
      ...(init.headers || {}),
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json();
}

export const api = {
  listProjects: (params: URLSearchParams = new URLSearchParams()) =>
    request<ProjectListResponse>(`/api/v1/projects?${params.toString()}`),
  filterOptions: () =>
    request<ProjectFilterOptions>(`/api/v1/projects/options`),
  projectDetail: (pid: string) =>
    request<ProjectDetail>(`/api/v1/projects/${pid}`),
  torAnalysis: (pid: string) =>
    request<TorAnalyzeResponse>(`/api/v1/tor/${pid}`).catch((e) => {
      // 404 = not yet analyzed, surface as null
      if (String(e).includes("API 404")) return null;
      throw e;
    }),
  runTorAnalysis: (pid: string) =>
    request<TorAnalyzeResponse>(`/api/v1/tor/${pid}/analyze`, {
      method: "POST",
    }),
  askTor: (pid: string, question: string, companyProfile?: object) =>
    request<TorQAResponse>(`/api/v1/tor/${pid}/qa`, {
      method: "POST",
      body: JSON.stringify({ question, company_profile: companyProfile || null }),
    }),
};
