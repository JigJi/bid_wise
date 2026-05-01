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
} from "lucide-react";
import { TorAnalyzeResponse, api } from "@/lib/api";
import { formatTHB } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
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
      <div className="rounded-xl border border-dashed border-border bg-card/40 p-8 text-center">
        <Sparkles className="mx-auto mb-3 h-8 w-8 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">
          ยังไม่ได้วิเคราะห์ TOR ของโครงการนี้
        </p>
        <Button
          className="mt-4"
          onClick={runAnalysis}
          disabled={running}
        >
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
        {error && (
          <p className="mt-3 text-xs text-destructive">{error}</p>
        )}
      </div>
    );
  }

  const s = analysis.summary || {};
  const proj = s.project || {};
  const money = s.money || {};
  const scope = s.scope || {};
  const qual = s.qualification || {};
  const eval_ = s.evaluation || {};
  const rf = s.red_flags || {};

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-border bg-card p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="flex items-center gap-2 text-sm font-medium">
            <Sparkles className="h-4 w-4 text-primary" />
            TOR Summary <span className="text-xs text-muted-foreground">· AI extracted</span>
          </h2>
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className="font-mono text-[10px]">
              {analysis.model_name?.split("/")[1]?.slice(0, 18) || "model"}
            </Badge>
            <Button
              size="sm"
              variant="ghost"
              onClick={runAnalysis}
              disabled={running}
            >
              {running && <Loader2 className="mr-2 h-3 w-3 animate-spin" />}
              วิเคราะห์ใหม่
            </Button>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <Cell icon={<Coins />} label="ราคากลาง">
            {money.price_build_thb
              ? formatTHB(money.price_build_thb)
              : "—"}
          </Cell>
          <Cell icon={<Coins />} label="วงเงินงบประมาณ">
            {money.budget_thb ? formatTHB(money.budget_thb) : "—"}
          </Cell>
          <Cell icon={<Calendar />} label="วันประกาศ">
            {proj.announce_date_text || "—"}
          </Cell>
          <Cell icon={<Calendar />} label="ปิดรับข้อเสนอ">
            {proj.submission_deadline_text || "—"}
          </Cell>
          {(money.bid_bond_thb || money.bid_bond_pct) && (
            <Cell icon={<Coins />} label="หลักประกันการเสนอราคา">
              {money.bid_bond_thb ? formatTHB(money.bid_bond_thb) : "—"}
              {money.bid_bond_pct ? ` (${money.bid_bond_pct}%)` : ""}
            </Cell>
          )}
          {money.performance_bond_pct && (
            <Cell icon={<Coins />} label="หลักประกันสัญญา">
              {money.performance_bond_pct}%
            </Cell>
          )}
        </div>

        {scope.thai_summary && (
          <>
            <Separator className="my-4" />
            <div>
              <div className="mb-1 text-xs font-medium text-muted-foreground">ภาพรวมงาน</div>
              <p className="text-sm leading-relaxed">{scope.thai_summary}</p>
            </div>
          </>
        )}

        {scope.items && scope.items.length > 0 && (
          <>
            <Separator className="my-4" />
            <div>
              <button
                onClick={() => setExpanded((e) => ({ ...e, items: !e.items }))}
                className="flex w-full items-center justify-between text-xs font-medium text-muted-foreground hover:text-foreground"
              >
                <span className="flex items-center gap-2">
                  <ListChecks className="h-3.5 w-3.5" />
                  รายการ BOQ ({scope.items.length} รายการ)
                </span>
                {expanded.items ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              </button>
              {expanded.items && (
                <ul className="mt-3 space-y-2 text-sm">
                  {scope.items.map((it, i) => (
                    <li key={i} className="rounded-md border border-border/50 bg-background/50 p-2">
                      <div className="font-medium">{it.item}</div>
                      {(it.qty || it.unit) && (
                        <div className="text-xs text-muted-foreground">
                          {it.qty} {it.unit || ""}
                          {it.spec && ` · ${it.spec}`}
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </>
        )}

        {(qual.registered_capital_min_thb ||
          (qual.past_work_required && qual.past_work_required.length > 0) ||
          (qual.certifications_required && qual.certifications_required.length > 0)) && (
          <>
            <Separator className="my-4" />
            <button
              onClick={() => setExpanded((e) => ({ ...e, qualification: !e.qualification }))}
              className="flex w-full items-center justify-between text-xs font-medium text-muted-foreground hover:text-foreground"
            >
              <span>คุณสมบัติผู้เสนอ</span>
              {expanded.qualification ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            </button>
            {expanded.qualification && (
              <div className="mt-3 space-y-2 text-sm">
                {qual.registered_capital_min_thb && (
                  <div>
                    <span className="text-muted-foreground">ทุนจดทะเบียนขั้นต่ำ:</span>{" "}
                    {formatTHB(qual.registered_capital_min_thb)}
                  </div>
                )}
                {qual.past_work_required && qual.past_work_required.length > 0 && (
                  <div>
                    <div className="text-muted-foreground">ผลงานที่ต้องการ:</div>
                    <ul className="ml-4 list-disc">
                      {qual.past_work_required.map((w, i) => (
                        <li key={i}>{w.description}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {qual.certifications_required && qual.certifications_required.length > 0 && (
                  <div>
                    <div className="text-muted-foreground">ใบรับรอง:</div>
                    <div className="flex flex-wrap gap-1">
                      {qual.certifications_required.map((c, i) => (
                        <Badge key={i} variant="outline">
                          {c}
                        </Badge>
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
            <Separator className="my-4" />
            <div className="rounded-md border border-amber-500/30 bg-amber-500/5 p-3">
              <div className="mb-1 flex items-center gap-2 text-xs font-medium text-amber-500 dark:text-amber-400">
                <ShieldAlert className="h-3.5 w-3.5" />
                Red Flag
              </div>
              {rf.notes && <p className="text-sm">{rf.notes}</p>}
              {rf.unusual_qualifications && rf.unusual_qualifications.length > 0 && (
                <ul className="mt-2 ml-4 list-disc text-sm">
                  {rf.unusual_qualifications.map((u, i) => (
                    <li key={i}>{u}</li>
                  ))}
                </ul>
              )}
              {rf.tight_timeline_days && (
                <div className="mt-2 text-xs text-muted-foreground">
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

function Cell({
  icon,
  label,
  children,
}: {
  icon: React.ReactNode;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="mb-0.5 flex items-center gap-1.5 text-xs text-muted-foreground">
        <span className="[&>svg]:h-3 [&>svg]:w-3">{icon}</span>
        {label}
      </div>
      <div className="text-sm font-medium">{children}</div>
    </div>
  );
}
