import { Suspense } from "react";
import { Sparkles, FileText, Users, Search } from "lucide-react";
import { FilterBar } from "@/components/filter-bar";
import { ProjectList } from "@/components/project-list";
import { api } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";

export default async function HomePage() {
  let options;
  let optionsError: string | null = null;
  try {
    options = await api.filterOptions();
  } catch (e) {
    optionsError = String(e);
  }

  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
      {/* page header — navy authority + simple */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-primary dark:text-foreground sm:text-3xl">
          โครงการจัดซื้อจัดจ้าง
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          ค้นหา · กรอง · เลือกโครงการ → กดเข้าไปอ่าน TOR ด้วย AI
        </p>
      </div>

      {/* stat cards — colored icon-in-box, smart_e_gp style */}
      <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard
          icon={<Search className="h-5 w-5" />}
          label="โครงการที่ index"
          value="3"
          tone="blue"
        />
        <StatCard
          icon={<Sparkles className="h-5 w-5" />}
          label="TOR analyzed"
          value="3"
          tone="purple"
        />
        <StatCard
          icon={<Users className="h-5 w-5" />}
          label="ผู้เสนอเก็บไว้แล้ว"
          value="11"
          tone="green"
        />
      </div>

      {optionsError ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-300">
          ไม่สามารถโหลดตัวกรองจาก backend ได้ ({optionsError})
          <div className="mt-2 text-xs text-muted-foreground">
            ตรวจสอบว่า uvicorn ทำงานที่ http://127.0.0.1:8200
          </div>
        </div>
      ) : options ? (
        <div className="space-y-6">
          <FilterBar options={options} />
          <Suspense fallback={<Skeleton className="h-96 w-full" />}>
            <ProjectList />
          </Suspense>
        </div>
      ) : null}
    </div>
  );
}

const STAT_TONES = {
  blue: {
    icon: "bg-blue-50 text-blue-600 dark:bg-blue-950/50 dark:text-blue-400",
  },
  green: {
    icon: "bg-green-50 text-green-600 dark:bg-green-950/50 dark:text-green-400",
  },
  orange: {
    icon: "bg-orange-50 text-orange-600 dark:bg-orange-950/50 dark:text-orange-400",
  },
  purple: {
    icon: "bg-purple-50 text-purple-600 dark:bg-purple-950/50 dark:text-purple-400",
  },
  yellow: {
    icon: "bg-yellow-50 text-yellow-600 dark:bg-yellow-950/50 dark:text-yellow-400",
  },
} as const;

function StatCard({
  icon,
  label,
  value,
  tone,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  tone: keyof typeof STAT_TONES;
}) {
  const t = STAT_TONES[tone];
  return (
    <div className="rounded-lg border border-border bg-card p-5 shadow-sm transition-shadow hover:shadow-md">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {label}
          </div>
          <div className="mt-1 text-2xl font-bold tabular-nums">{value}</div>
        </div>
        <div className={`grid h-12 w-12 place-items-center rounded-lg ${t.icon}`}>
          {icon}
        </div>
      </div>
    </div>
  );
}
