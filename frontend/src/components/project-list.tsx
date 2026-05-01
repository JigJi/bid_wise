"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Users, Calendar, Building2 } from "lucide-react";
import { api, ProjectListItem, ProjectListResponse } from "@/lib/api";
import { formatTHB, formatDate, methodLabel, stepLabel } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
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
          <Skeleton key={i} className="h-24 w-full" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-destructive/50 bg-destructive/5 p-4 text-sm text-destructive">
        เกิดข้อผิดพลาด: {error}
      </div>
    );
  }

  if (!data || data.items.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-border bg-card/30 p-12 text-center">
        <p className="text-sm text-muted-foreground">
          ไม่พบโครงการที่ตรงกับเงื่อนไข
        </p>
      </div>
    );
  }

  const page = data.page;
  const totalPages = Math.max(1, Math.ceil(data.total / data.page_size));

  return (
    <div className="space-y-3">
      <div className="text-xs text-muted-foreground">
        ทั้งหมด {data.total.toLocaleString()} โครงการ
      </div>
      <div className="space-y-2">
        {data.items.map((p) => (
          <ProjectCard key={p.project_id} project={p} />
        ))}
      </div>
      {totalPages > 1 && (
        <Pagination page={page} totalPages={totalPages} />
      )}
    </div>
  );
}

function ProjectCard({ project }: { project: ProjectListItem }) {
  return (
    <Link
      href={`/projects/${project.project_id}`}
      className="group block rounded-lg border border-border bg-card p-4 transition-all hover:border-primary/50 hover:shadow-md"
    >
      <div className="mb-2 flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-sm font-medium leading-snug text-foreground group-hover:text-primary">
            {project.project_name}
          </h3>
          <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
            <span className="font-mono">{project.project_id}</span>
            <span>·</span>
            <span className="flex items-center gap-1">
              <Building2 className="h-3 w-3" />
              {project.dept_sub_name || "—"}
            </span>
          </div>
        </div>
        <div className="text-right">
          <div className="text-base font-semibold tabular-nums">
            {formatTHB(project.project_money)}
          </div>
          {project.price_agree && project.project_money && (
            <div className="text-xs text-emerald-500 tabular-nums">
              ตกลง {formatTHB(project.price_agree)}
            </div>
          )}
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="secondary">{methodLabel(project.method_id)}</Badge>
        <Badge variant="outline">{stepLabel(project.step_id)}</Badge>
        <span className="ml-auto flex items-center gap-1 text-xs text-muted-foreground">
          <Users className="h-3 w-3" />
          {project.bidder_count} ผู้เสนอ
        </span>
        <span className="flex items-center gap-1 text-xs text-muted-foreground">
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
        หน้า {page} / {totalPages}
      </span>
      <Button asChild variant="outline" size="sm" disabled={page >= totalPages}>
        <Link href={buildUrl(page + 1)}>ถัดไป</Link>
      </Button>
    </div>
  );
}
