"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname, useSearchParams } from "next/navigation";
import { Search, X, Sliders } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ProjectFilterOptions } from "@/lib/api";
import { methodLabel, stepLabel } from "@/lib/format";

type Props = { options: ProjectFilterOptions };

export function FilterBar({ options }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const sp = useSearchParams();

  const [q, setQ] = useState(sp.get("q") || "");
  const [showAdvanced, setShowAdvanced] = useState(false);

  // debounced search → URL
  useEffect(() => {
    const handle = setTimeout(() => {
      const params = new URLSearchParams(sp.toString());
      if (q) params.set("q", q);
      else params.delete("q");
      params.delete("page");
      router.replace(`${pathname}?${params.toString()}`);
    }, 600);
    return () => clearTimeout(handle);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q]);

  const toggleParam = (key: string, value: string) => {
    const params = new URLSearchParams(sp.toString());
    const current = params.getAll(key);
    if (current.includes(value)) {
      params.delete(key);
      current.filter((v) => v !== value).forEach((v) => params.append(key, v));
    } else {
      params.append(key, value);
    }
    params.delete("page");
    router.replace(`${pathname}?${params.toString()}`);
  };

  const clearAll = () => {
    setQ("");
    router.replace(pathname);
  };

  const isActive = (key: string, value: string) =>
    sp.getAll(key).includes(value);

  const activeCount =
    [...sp.entries()].filter(
      ([k]) => k !== "page" && k !== "page_size",
    ).length;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="ค้นหา ชื่อโครงการ / pid / หน่วยงาน..."
            className="pl-9"
          />
        </div>
        <Button
          variant={showAdvanced ? "default" : "outline"}
          onClick={() => setShowAdvanced((s) => !s)}
        >
          <Sliders className="mr-2 h-4 w-4" />
          ตัวกรอง
          {activeCount > 0 && (
            <Badge variant="secondary" className="ml-2">
              {activeCount}
            </Badge>
          )}
        </Button>
        {activeCount > 0 && (
          <Button variant="ghost" onClick={clearAll}>
            <X className="mr-2 h-4 w-4" />
            ล้าง
          </Button>
        )}
      </div>

      {showAdvanced && (
        <div className="space-y-3 rounded-lg border border-border bg-card/50 p-4">
          <FilterChipRow
            label="วิธี"
            keyName="method_id"
            chips={options.methods.map((m) => ({ value: m.id, label: methodLabel(m.id) }))}
            isActive={isActive}
            onToggle={toggleParam}
          />
          <FilterChipRow
            label="สถานะ"
            keyName="step_id"
            chips={options.steps.map((s) => ({ value: s.id, label: stepLabel(s.id) }))}
            isActive={isActive}
            onToggle={toggleParam}
          />
          <FilterChipRow
            label="ผู้เสนอ"
            keyName="bidder_count"
            chips={options.bidder_count_buckets.map((b) => ({ value: b.key, label: b.label }))}
            isActive={isActive}
            onToggle={toggleParam}
          />
        </div>
      )}
    </div>
  );
}

function FilterChipRow({
  label,
  keyName,
  chips,
  isActive,
  onToggle,
}: {
  label: string;
  keyName: string;
  chips: { value: string; label: string }[];
  isActive: (k: string, v: string) => boolean;
  onToggle: (k: string, v: string) => void;
}) {
  if (chips.length === 0) return null;
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-xs text-muted-foreground w-16 shrink-0">{label}</span>
      {chips.map((chip) => {
        const active = isActive(keyName, chip.value);
        return (
          <button
            key={chip.value}
            onClick={() => onToggle(keyName, chip.value)}
            className={`rounded-full border px-3 py-1 text-xs transition-colors ${
              active
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border bg-background hover:bg-secondary"
            }`}
          >
            {chip.label}
          </button>
        );
      })}
    </div>
  );
}
