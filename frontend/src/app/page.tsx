import { Suspense } from "react";
import { FilterBar } from "@/components/filter-bar";
import { ProjectList } from "@/components/project-list";
import { api } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";

export default async function HomePage() {
  // server-side fetch of filter options (cacheable; rarely changes)
  let options;
  let optionsError: string | null = null;
  try {
    options = await api.filterOptions();
  } catch (e) {
    optionsError = String(e);
  }

  return (
    <div className="mx-auto max-w-7xl px-6 py-10">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">
          โครงการจัดซื้อจัดจ้าง
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          ค้นหา / กรอง / เลือกโครงการ → กดเข้าไปอ่าน TOR ด้วย AI
        </p>
      </div>

      {optionsError ? (
        <div className="rounded-lg border border-destructive/50 bg-destructive/5 p-4 text-sm text-destructive">
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
