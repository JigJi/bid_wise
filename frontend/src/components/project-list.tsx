"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Users, Calendar, Building2, ChevronRight } from "lucide-react";
import { api, ProjectListItem, ProjectListResponse } from "@/lib/api";
import {
  formatTHB,
  formatDate,
  methodLabel,
  stepLabel,
  methodTone,
  stepTone,
  bidderCountTone,
} from "@/lib/format";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";

const PAGE_SIZE = 20;

export function ProjectList() {
  const sp = useSearchParams();
  const [data, setData] = useState<ProjectListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    const params = new URLSearchParams(sp.toString());
    if (!params.has("page_size")) params.set("page_size", String(PAGE_SIZE));
    api
      .listProjects(params)
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((e) => {
        if (!cancelled) setError(String(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [sp]);

  if (loading && !data) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-28 w-full" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-300">
        เกิดข้อผิดพลาด: {error}
      </div>
    );
  }

  if (!data || data.items.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-border bg-card p-12 text-center">
        <p className="text-sm text-muted-foreground">ไม่พบโครงการที่ตรงกับเงื่อนไข</p>
      </div>
    );
  }

  const totalPages = Math.max(1, Math.ceil(data.total / data.page_size));

  return (
    <div className="space-y-4">
      <div className="text-xs text-muted-foreground">
        ทั้งหมด <span className="font-semibold text-foreground">{data.total.toLocaleString()}</span>{" "}
        โครงการ
      </div>
      <div className="grid gap-3">
        {data.items.map((p) => (
          <ProjectCard key={p.project_id} project={p} />
        ))}
      </div>
      {totalPages > 1 && <Pagination page={data.page} totalPages={totalPages} />}
    </div>
  );
}

function ProjectCard({ project }: { project: ProjectListItem }) {
  const bTone = bidderCountTone(project.bidder_count);
  const savings =
    project.price_agree && project.project_money
      ? ((Number(project.project_money) - Number(project.price_agree)) /
          Number(project.project_money)) *
        100
      : null;

  return (
    <Link
      href={`/projects/${project.project_id}`}
      className="group block rounded-lg border border-border bg-card p-5 shadow-sm transition-all hover:border-primary/30 hover:shadow-md"
    >
      <div className="mb-3 flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <h3 className="line-clamp-2 text-sm font-semibold leading-snug text-foreground transition-colors group-hover:text-primary">
            {project.project_name}
          </h3>
          <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
            <span className="font-mono text-foreground/70">{project.project_id}</span>
            <span className="hidden sm:inline">·</span>
            <span className="flex items-center gap-1 truncate">
              <Building2 className="h-3 w-3 shrink-0" />
              <span className="truncate">{project.dept_sub_name || "—"}</span>
            </span>
          </div>
        </div>
        <div className="text-right shrink-0">
          <div className="text-base font-bold tabular-nums">
            {formatTHB(project.project_money)}
          </div>
          {project.price_agree && (
            <div className="mt-0.5 inline-flex items-center gap-1 rounded-md bg-green-50 px-1.5 py-0.5 text-[11px] font-medium text-green-700 dark:bg-green-950/40 dark:text-green-300">
              ตกลง {formatTHB(project.price_agree)}
              {savings !== null && (
                <span className="opacity-70">· -{savings.toFixed(1)}%</span>
              )}
            </div>
          )}
        </div>
        <ChevronRight className="mt-1 h-4 w-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-primary" />
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium ${methodTone(project.method_id)}`}
        >
          {methodLabel(project.method_id)}
        </span>
        <span
          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium ${stepTone(project.step_id)}`}
        >
          {stepLabel(project.step_id)}
        </span>
        <span
          className={`ml-auto inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-medium ${bTone.cls}`}
        >
          <Users className="h-3 w-3" />
          {bTone.label}
        </span>
        <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
          <Calendar className="h-3 w-3" />
          {formatDate(project.announce_date)}
        </span>
      </div>
    </Link>
  );
}

function Pagination({ page, totalPages }: { page: number; totalPages: number }) {
  const sp = useSearchParams();
  const buildUrl = (p: number) => {
    const params = new URLSearchParams(sp.toString());
    params.set("page", String(p));
    return `?${params.toString()}`;
  };
  return (
    <div className="flex items-center justify-center gap-2 pt-4">
      <Button asChild variant="outline" size="sm" disabled={page <= 1}>
        <Link href={buildUrl(page - 1)}>ก่อนหน้า</Link>
      </Button>
      <span className="text-sm text-muted-foreground">
        หน้า <span className="font-semibold text-foreground">{page}</span> / {totalPages}
      </span>
      <Button asChild variant="outline" size="sm" disabled={page >= totalPages}>
        <Link href={buildUrl(page + 1)}>ถัดไป</Link>
      </Button>
    </div>
  );
}
