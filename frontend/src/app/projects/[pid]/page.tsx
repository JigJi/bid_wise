import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, Building2, Calendar, Users } from "lucide-react";
import { api } from "@/lib/api";
import {
  formatTHB,
  formatDate,
  methodLabel,
  stepLabel,
} from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { TorSummaryCard } from "@/components/tor-summary-card";
import { QaChat } from "@/components/qa-chat";
import { Button } from "@/components/ui/button";

type Props = { params: Promise<{ pid: string }> };

export default async function ProjectDetailPage({ params }: Props) {
  const { pid } = await params;
  let project, analysis;
  try {
    [project, analysis] = await Promise.all([
      api.projectDetail(pid),
      api.torAnalysis(pid),
    ]);
  } catch (e) {
    if (String(e).includes("API 404")) notFound();
    throw e;
  }

  const winners = project.bidders.filter((b) => b.is_winner);
  const others = project.bidders.filter((b) => !b.is_winner);

  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
      <Button asChild variant="ghost" size="sm" className="mb-4 -ml-2">
        <Link href="/">
          <ArrowLeft className="mr-2 h-4 w-4" />
          กลับ
        </Link>
      </Button>

      {/* hero */}
      <div className="mb-6">
        <div className="mb-2 flex items-center gap-2 text-xs text-muted-foreground">
          <span className="font-mono">{project.project_id}</span>
          <span>·</span>
          <Badge variant="secondary">{methodLabel(project.method_id)}</Badge>
          <Badge variant="outline">{stepLabel(project.step_id)}</Badge>
        </div>
        <h1 className="text-xl font-semibold leading-snug">
          {project.project_name}
        </h1>
        <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1 text-sm text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <Building2 className="h-3.5 w-3.5" />
            {project.dept_sub_name || "—"}
          </span>
          <span className="flex items-center gap-1.5">
            <Calendar className="h-3.5 w-3.5" />
            ประกาศ {formatDate(project.announce_date)}
          </span>
          <span className="flex items-center gap-1.5">
            <Users className="h-3.5 w-3.5" />
            {project.bidders.length} ผู้เสนอ
          </span>
        </div>
      </div>

      {/* money strip */}
      <div className="mb-6 grid gap-3 md:grid-cols-3">
        <MoneyStrip label="วงเงินงบประมาณ" value={project.project_money} />
        <MoneyStrip label="ราคากลาง" value={project.price_build} />
        <MoneyStrip
          label="ตกลงราคา"
          value={project.price_agree}
          highlight={!!project.price_agree}
          subValue={
            project.price_agree && project.project_money
              ? `ประหยัด ${(((Number(project.project_money) - Number(project.price_agree)) / Number(project.project_money)) * 100).toFixed(1)}%`
              : undefined
          }
        />
      </div>

      {/* TOR + chat side-by-side */}
      <div className="grid gap-6 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <TorSummaryCard pid={pid} initial={analysis} />
        </div>
        <div className="lg:col-span-2">
          <QaChat pid={pid} />
        </div>
      </div>

      {/* bidders table */}
      {project.bidders.length > 0 && (
        <div className="mt-8">
          <h2 className="mb-3 text-sm font-medium">
            ผลการพิจารณา ({project.bidders.length} ผู้เสนอ)
          </h2>
          <div className="overflow-hidden rounded-xl border border-border">
            <table className="w-full text-sm">
              <thead className="bg-secondary/50 text-xs text-muted-foreground">
                <tr>
                  <th className="px-4 py-2 text-left">ผู้เสนอ</th>
                  <th className="px-4 py-2 text-right">ราคาเสนอ</th>
                  <th className="px-4 py-2 text-center">ผลพิจารณา</th>
                  <th className="px-4 py-2 text-right">ราคาตกลง</th>
                </tr>
              </thead>
              <tbody>
                {[...winners, ...others].map((b, i) => (
                  <tr
                    key={i}
                    className={`border-t border-border ${b.is_winner ? "bg-emerald-500/5" : ""}`}
                  >
                    <td className="px-4 py-2.5">
                      <div className="font-medium">
                        {b.is_winner && (
                          <Badge className="mr-2 bg-emerald-500/15 text-emerald-600 hover:bg-emerald-500/15 dark:text-emerald-400">
                            ★ ผู้ชนะ
                          </Badge>
                        )}
                        {b.receive_name_th}
                      </div>
                      <div className="text-xs text-muted-foreground font-mono">
                        TIN {b.vendor_tin}
                      </div>
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums">
                      {formatTHB(b.price_proposal)}
                    </td>
                    <td className="px-4 py-2.5 text-center">
                      {b.result_flag === "P" ? (
                        <Badge variant="secondary" className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                          ผ่าน
                        </Badge>
                      ) : b.result_flag === "N" ? (
                        <Badge variant="outline" className="text-muted-foreground">
                          ไม่ผ่าน
                        </Badge>
                      ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-emerald-600 dark:text-emerald-400">
                      {b.is_winner ? formatTHB(b.price_agree) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function MoneyStrip({
  label,
  value,
  highlight,
  subValue,
}: {
  label: string;
  value: string | null;
  highlight?: boolean;
  subValue?: string;
}) {
  return (
    <div
      className={`rounded-xl border p-4 ${
        highlight
          ? "border-emerald-500/30 bg-emerald-500/5"
          : "border-border bg-card"
      }`}
    >
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-1 text-xl font-semibold tabular-nums">
        {formatTHB(value)}
      </div>
      {subValue && (
        <div className="mt-0.5 text-xs text-emerald-500">{subValue}</div>
      )}
    </div>
  );
}
