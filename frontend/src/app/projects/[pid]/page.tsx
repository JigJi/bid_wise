import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, Building2, Calendar, Users, TrendingDown, Award, Coins } from "lucide-react";
import { api } from "@/lib/api";
import {
  formatTHB,
  formatDate,
  methodLabel,
  stepLabel,
  methodTone,
  stepTone,
} from "@/lib/format";
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

  const savingsPct =
    project.price_agree && project.project_money
      ? ((Number(project.project_money) - Number(project.price_agree)) /
          Number(project.project_money)) *
        100
      : null;

  return (
    <div className="mx-auto max-w-7xl px-6 py-6">
      <Button asChild variant="ghost" size="sm" className="mb-3 -ml-2">
        <Link href="/">
          <ArrowLeft className="mr-2 h-4 w-4" />
          กลับ
        </Link>
      </Button>

      <div className="mb-6">
        <div className="mb-2 flex flex-wrap items-center gap-2 text-xs">
          <span className="font-mono text-muted-foreground">{project.project_id}</span>
          <span className="text-muted-foreground">·</span>
          <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium ${methodTone(project.method_id)}`}>
            {methodLabel(project.method_id)}
          </span>
          <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium ${stepTone(project.step_id)}`}>
            {stepLabel(project.step_id)}
          </span>
        </div>
        <h1 className="text-xl font-bold leading-snug text-primary dark:text-foreground sm:text-2xl">
          {project.project_name}
        </h1>
        <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1.5 text-sm text-muted-foreground">
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
            <span className="font-semibold text-foreground">{project.bidders.length}</span> ผู้เสนอ
          </span>
        </div>
      </div>

      <div className="mb-6 grid gap-4 md:grid-cols-3">
        <MoneyStrip
          icon={<Coins />}
          tone="indigo"
          label="วงเงินงบประมาณ"
          value={project.project_money}
        />
        <MoneyStrip
          icon={<Coins />}
          tone="blue"
          label="ราคากลาง"
          value={project.price_build}
        />
        <MoneyStrip
          icon={<TrendingDown />}
          tone="green"
          label="ตกลงราคา"
          value={project.price_agree}
          subValue={savingsPct !== null ? `ประหยัด ${savingsPct.toFixed(1)}%` : undefined}
          highlight
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <TorSummaryCard pid={pid} initial={analysis} />
        </div>
        <div className="lg:col-span-2">
          <QaChat pid={pid} />
        </div>
      </div>

      {project.bidders.length > 0 && (
        <div className="mt-8">
          <div className="mb-3 flex items-center gap-2">
            <span className="grid h-6 w-6 place-items-center rounded bg-green-50 text-green-600 dark:bg-green-950/40 dark:text-green-400">
              <Award className="h-3.5 w-3.5" />
            </span>
            <h2 className="text-sm font-semibold">
              ผลการพิจารณา{" "}
              <span className="font-normal text-muted-foreground">
                ({project.bidders.length} ผู้เสนอ
                {winners.length > 0 ? `, ${winners.length} ผู้ชนะ` : ""})
              </span>
            </h2>
          </div>
          <div className="overflow-hidden rounded-lg border border-border bg-card shadow-sm">
            <table className="w-full text-sm">
              <thead className="bg-secondary text-xs text-muted-foreground">
                <tr>
                  <th className="px-4 py-3 text-left font-medium">ผู้เสนอ</th>
                  <th className="px-4 py-3 text-right font-medium">ราคาเสนอ</th>
                  <th className="px-4 py-3 text-center font-medium">ผลพิจารณา</th>
                  <th className="px-4 py-3 text-right font-medium">ราคาตกลง</th>
                </tr>
              </thead>
              <tbody>
                {[...winners, ...others].map((b, i) => (
                  <tr
                    key={i}
                    className={`border-t border-border ${
                      b.is_winner ? "bg-green-50/50 dark:bg-green-950/20" : "hover:bg-secondary/50"
                    }`}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {b.is_winner && (
                          <span className="inline-flex items-center gap-1 rounded-full bg-green-600 px-2 py-0.5 text-[10px] font-bold text-white">
                            <Award className="h-3 w-3" />
                            ผู้ชนะ
                          </span>
                        )}
                        <span className="font-medium">{b.receive_name_th}</span>
                      </div>
                      <div className="mt-0.5 font-mono text-xs text-muted-foreground">
                        TIN {b.vendor_tin}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums">
                      {formatTHB(b.price_proposal)}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {b.result_flag === "P" ? (
                        <span className="inline-flex items-center rounded-full bg-green-50 px-2.5 py-0.5 text-[11px] font-medium text-green-700 dark:bg-green-950/40 dark:text-green-300">
                          ผ่าน
                        </span>
                      ) : b.result_flag === "N" ? (
                        <span className="inline-flex items-center rounded-full bg-red-50 px-2.5 py-0.5 text-[11px] font-medium text-red-700 dark:bg-red-950/40 dark:text-red-300">
                          ไม่ผ่าน
                        </span>
                      ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums">
                      {b.is_winner ? (
                        <span className="font-semibold text-green-700 dark:text-green-400">
                          {formatTHB(b.price_agree)}
                        </span>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
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

const STRIP_TONES = {
  indigo: {
    icon: "bg-indigo-50 text-indigo-600 dark:bg-indigo-950/40 dark:text-indigo-400",
    text: "",
  },
  blue: {
    icon: "bg-blue-50 text-blue-600 dark:bg-blue-950/40 dark:text-blue-400",
    text: "",
  },
  green: {
    icon: "bg-green-50 text-green-600 dark:bg-green-950/40 dark:text-green-400",
    text: "text-green-700 dark:text-green-400",
  },
} as const;

function MoneyStrip({
  icon,
  tone,
  label,
  value,
  highlight,
  subValue,
}: {
  icon: React.ReactNode;
  tone: keyof typeof STRIP_TONES;
  label: string;
  value: string | null;
  highlight?: boolean;
  subValue?: string;
}) {
  const t = STRIP_TONES[tone];
  return (
    <div className="rounded-lg border border-border bg-card p-5 shadow-sm">
      <div className="flex items-start justify-between">
        <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {label}
        </div>
        <div className={`grid h-9 w-9 place-items-center rounded-md ${t.icon} [&>svg]:h-4 [&>svg]:w-4`}>
          {icon}
        </div>
      </div>
      <div className={`mt-2 text-2xl font-bold tabular-nums ${highlight ? t.text : ""}`}>
        {formatTHB(value)}
      </div>
      {highlight && subValue && (
        <div className="mt-1 inline-flex items-center gap-1 text-xs font-medium text-green-700 dark:text-green-400">
          <TrendingDown className="h-3 w-3" />
          {subValue}
        </div>
      )}
    </div>
  );
}
