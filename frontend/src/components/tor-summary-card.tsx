"use client";

import { useState } from "react";
import {
  Calendar,
  Coins,
  ListChecks,
  ShieldAlert,
  Sparkles,
  Loader2,
  ChevronDown,
  ChevronUp,
  Award,
  Briefcase,
} from "lucide-react";
import { TorAnalyzeResponse, api } from "@/lib/api";
import { formatTHB } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

type Props = {
  pid: string;
  initial: TorAnalyzeResponse | null;
};

export function TorSummaryCard({ pid, initial }: Props) {
  const [analysis, setAnalysis] = useState<TorAnalyzeResponse | null>(initial);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState({
    items: false,
    qualification: false,
  });

  const runAnalysis = async () => {
    setRunning(true);
    setError(null);
    try {
      const res = await api.runTorAnalysis(pid);
      setAnalysis(res);
    } catch (e) {
      setError(String(e));
    } finally {
      setRunning(false);
    }
  };

  if (!analysis) {
    return (
      <div className="rounded-lg border border-dashed border-border bg-card p-10 text-center shadow-sm">
        <div className="mx-auto mb-4 grid h-12 w-12 place-items-center rounded-lg bg-blue-50 text-blue-600 dark:bg-blue-950/40 dark:text-blue-400">
          <Sparkles className="h-5 w-5" />
        </div>
        <p className="text-sm text-muted-foreground">
          ยังไม่ได้วิเคราะห์ TOR ของโครงการนี้
        </p>
        <Button className="mt-4" onClick={runAnalysis} disabled={running}>
          {running ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              กำลังให้ AI อ่าน TOR...
            </>
          ) : (
            <>
              <Sparkles className="mr-2 h-4 w-4" />
              วิเคราะห์ TOR ด้วย AI
            </>
          )}
        </Button>
        {error && <p className="mt-3 text-xs text-destructive">{error}</p>}
      </div>
    );
  }

  const s = analysis.summary || {};
  const proj = s.project || {};
  const money = s.money || {};
  const scope = s.scope || {};
  const qual = s.qualification || {};
  const rf = s.red_flags || {};

  return (
    <div className="rounded-lg border border-border bg-card shadow-sm">
      <div className="flex items-center justify-between border-b border-border px-5 py-3.5">
        <h2 className="flex items-center gap-2 text-sm font-semibold">
          <span className="grid h-6 w-6 place-items-center rounded bg-blue-50 text-blue-600 dark:bg-blue-950/40 dark:text-blue-400">
            <Sparkles className="h-3.5 w-3.5" />
          </span>
          TOR Summary
          <span className="text-xs font-normal text-muted-foreground">· AI extracted</span>
        </h2>
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-purple-50 px-2 py-0.5 font-mono text-[10px] text-purple-700 dark:bg-purple-950/40 dark:text-purple-300">
            {analysis.model_name?.split("/")[1]?.slice(0, 18) || "model"}
          </span>
          <Button size="sm" variant="ghost" onClick={runAnalysis} disabled={running}>
            {running && <Loader2 className="mr-2 h-3 w-3 animate-spin" />}
            วิเคราะห์ใหม่
          </Button>
        </div>
      </div>

      <div className="p-5">
        <div className="grid gap-3 md:grid-cols-2">
          <Cell tone="green" icon={<Coins />} label="ราคากลาง">
            {money.price_build_thb ? formatTHB(money.price_build_thb) : "—"}
          </Cell>
          <Cell tone="indigo" icon={<Coins />} label="วงเงินงบประมาณ">
            {money.budget_thb ? formatTHB(money.budget_thb) : "—"}
          </Cell>
          <Cell tone="blue" icon={<Calendar />} label="วันประกาศ">
            {proj.announce_date_text || "—"}
          </Cell>
          <Cell tone="purple" icon={<Calendar />} label="ปิดรับข้อเสนอ">
            {proj.submission_deadline_text || "—"}
          </Cell>
          {(money.bid_bond_thb || money.bid_bond_pct) && (
            <Cell tone="orange" icon={<Award />} label="หลักประกันการเสนอราคา">
              {money.bid_bond_thb ? formatTHB(money.bid_bond_thb) : "—"}
              {money.bid_bond_pct ? ` (${money.bid_bond_pct}%)` : ""}
            </Cell>
          )}
          {money.performance_bond_pct && (
            <Cell tone="pink" icon={<Award />} label="หลักประกันสัญญา">
              {money.performance_bond_pct}%
            </Cell>
          )}
        </div>

        {scope.thai_summary && (
          <>
            <Separator className="my-5" />
            <div className="rounded-md bg-blue-50/50 p-3 dark:bg-blue-950/20">
              <div className="mb-1 flex items-center gap-1.5 text-xs font-medium text-blue-700 dark:text-blue-300">
                <Briefcase className="h-3 w-3" />
                ภาพรวมงาน
              </div>
              <p className="text-sm leading-relaxed">{scope.thai_summary}</p>
            </div>
          </>
        )}

        {scope.items && scope.items.length > 0 && (
          <>
            <Separator className="my-5" />
            <button
              onClick={() => setExpanded((e) => ({ ...e, items: !e.items }))}
              className="flex w-full items-center justify-between text-xs font-medium hover:text-foreground"
            >
              <span className="flex items-center gap-2 text-muted-foreground">
                <span className="grid h-5 w-5 place-items-center rounded bg-purple-50 text-purple-600 dark:bg-purple-950/40 dark:text-purple-400">
                  <ListChecks className="h-3 w-3" />
                </span>
                รายการ BOQ
                <span className="rounded-full bg-purple-50 px-1.5 text-[10px] font-semibold text-purple-700 dark:bg-purple-950/40 dark:text-purple-300">
                  {scope.items.length}
                </span>
              </span>
              {expanded.items ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            </button>
            {expanded.items && (
              <ul className="mt-3 space-y-2 text-sm">
                {scope.items.map((it, i) => (
                  <li
                    key={i}
                    className="rounded-md border border-purple-100 bg-purple-50/40 p-2 dark:border-purple-900/40 dark:bg-purple-950/20"
                  >
                    <div className="font-medium">{it.item}</div>
                    {(it.qty || it.unit) && (
                      <div className="text-xs text-muted-foreground">
                        <span className="font-semibold tabular-nums text-purple-700 dark:text-purple-300">
                          {it.qty}
                        </span>{" "}
                        {it.unit || ""}
                        {it.spec && ` · ${it.spec}`}
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </>
        )}

        {(qual.registered_capital_min_thb ||
          (qual.past_work_required && qual.past_work_required.length > 0) ||
          (qual.certifications_required && qual.certifications_required.length > 0)) && (
          <>
            <Separator className="my-5" />
            <button
              onClick={() => setExpanded((e) => ({ ...e, qualification: !e.qualification }))}
              className="flex w-full items-center justify-between text-xs font-medium hover:text-foreground"
            >
              <span className="flex items-center gap-2 text-muted-foreground">
                <span className="grid h-5 w-5 place-items-center rounded bg-indigo-50 text-indigo-600 dark:bg-indigo-950/40 dark:text-indigo-400">
                  <Award className="h-3 w-3" />
                </span>
                คุณสมบัติผู้เสนอ
              </span>
              {expanded.qualification ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            </button>
            {expanded.qualification && (
              <div className="mt-3 space-y-2 rounded-md border border-indigo-100 bg-indigo-50/40 p-3 text-sm dark:border-indigo-900/40 dark:bg-indigo-950/20">
                {qual.registered_capital_min_thb && (
                  <div>
                    <span className="text-muted-foreground">ทุนจดทะเบียนขั้นต่ำ:</span>{" "}
                    <span className="font-semibold tabular-nums text-indigo-700 dark:text-indigo-300">
                      {formatTHB(qual.registered_capital_min_thb)}
                    </span>
                  </div>
                )}
                {qual.past_work_required && qual.past_work_required.length > 0 && (
                  <div>
                    <div className="text-muted-foreground">ผลงานที่ต้องการ:</div>
                    <ul className="ml-4 mt-1 list-disc">
                      {qual.past_work_required.map((w, i) => (
                        <li key={i}>{w.description}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {qual.certifications_required && qual.certifications_required.length > 0 && (
                  <div>
                    <div className="mb-1 text-muted-foreground">ใบรับรอง:</div>
                    <div className="flex flex-wrap gap-1">
                      {qual.certifications_required.map((c, i) => (
                        <span
                          key={i}
                          className="rounded-full bg-indigo-50 px-2 py-0.5 text-[11px] font-medium text-indigo-700 dark:bg-indigo-950/40 dark:text-indigo-300"
                        >
                          {c}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </>
        )}

        {(rf.notes ||
          (rf.unusual_qualifications && rf.unusual_qualifications.length > 0) ||
          rf.brand_specific) && (
          <>
            <Separator className="my-5" />
            <div className="rounded-md border border-orange-200 bg-orange-50 p-3.5 dark:border-orange-900/50 dark:bg-orange-950/20">
              <div className="mb-1.5 flex items-center gap-2 text-xs font-semibold text-orange-700 dark:text-orange-300">
                <ShieldAlert className="h-3.5 w-3.5" />
                Red Flag
              </div>
              {rf.notes && (
                <p className="text-sm leading-relaxed text-foreground">{rf.notes}</p>
              )}
              {rf.unusual_qualifications && rf.unusual_qualifications.length > 0 && (
                <ul className="mt-2 ml-4 list-disc text-sm">
                  {rf.unusual_qualifications.map((u, i) => (
                    <li key={i}>{u}</li>
                  ))}
                </ul>
              )}
              {rf.tight_timeline_days && (
                <div className="mt-2 inline-flex items-center gap-1 rounded-full bg-red-50 px-2 py-0.5 text-[11px] font-medium text-red-700 dark:bg-red-950/40 dark:text-red-300">
                  ระยะเวลายื่น: {rf.tight_timeline_days} วัน
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

const TONES: Record<
  string,
  { iconBg: string }
> = {
  green: { iconBg: "bg-green-50 text-green-600 dark:bg-green-950/40 dark:text-green-400" },
  indigo: { iconBg: "bg-indigo-50 text-indigo-600 dark:bg-indigo-950/40 dark:text-indigo-400" },
  blue: { iconBg: "bg-blue-50 text-blue-600 dark:bg-blue-950/40 dark:text-blue-400" },
  purple: { iconBg: "bg-purple-50 text-purple-600 dark:bg-purple-950/40 dark:text-purple-400" },
  orange: { iconBg: "bg-orange-50 text-orange-600 dark:bg-orange-950/40 dark:text-orange-400" },
  pink: { iconBg: "bg-pink-50 text-pink-600 dark:bg-pink-950/40 dark:text-pink-400" },
};

function Cell({
  tone,
  icon,
  label,
  children,
}: {
  tone: keyof typeof TONES;
  icon: React.ReactNode;
  label: string;
  children: React.ReactNode;
}) {
  const t = TONES[tone];
  return (
    <div className="rounded-md border border-border bg-background p-3">
      <div className="mb-1.5 flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        <span className={`grid h-5 w-5 place-items-center rounded ${t.iconBg}`}>
          <span className="[&>svg]:h-3 [&>svg]:w-3">{icon}</span>
        </span>
        {label}
      </div>
      <div className="text-sm font-semibold">{children}</div>
    </div>
  );
}
