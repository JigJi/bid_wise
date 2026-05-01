import Link from "next/link";
import { Sparkles } from "lucide-react";

export function Topbar() {
  return (
    <header className="sticky top-0 z-40 w-full border-b border-border bg-white/95 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between gap-4 px-6">
        <Link
          href="/"
          className="flex items-center gap-2.5 text-base font-semibold tracking-tight"
        >
          <span className="grid h-7 w-7 place-items-center rounded-md bg-primary text-primary-foreground">
            <Sparkles className="h-3.5 w-3.5" />
          </span>
          <span className="text-primary">bid_wise</span>
          <span className="hidden text-xs font-normal text-muted-foreground sm:inline">
            · smart admin สำหรับ vendor งานรัฐ
          </span>
        </Link>
      </div>
    </header>
  );
}
