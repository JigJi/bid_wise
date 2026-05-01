const THB = new Intl.NumberFormat("th-TH", {
  style: "currency",
  currency: "THB",
  maximumFractionDigits: 0,
});

const NUM = new Intl.NumberFormat("th-TH");

const DATE = new Intl.DateTimeFormat("th-TH-u-ca-buddhist", {
  year: "numeric",
  month: "short",
  day: "numeric",
});

const DATETIME = new Intl.DateTimeFormat("th-TH-u-ca-buddhist", {
  year: "numeric",
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

export function formatTHB(v: number | string | null | undefined): string {
  if (v === null || v === undefined || v === "") return "—";
  const n = typeof v === "string" ? Number(v) : v;
  if (!Number.isFinite(n)) return "—";
  return THB.format(n);
}

export function formatNumber(v: number | string | null | undefined): string {
  if (v === null || v === undefined || v === "") return "—";
  const n = typeof v === "string" ? Number(v) : v;
  if (!Number.isFinite(n)) return "—";
  return NUM.format(n);
}

export function formatDate(v: string | null | undefined): string {
  if (!v) return "—";
  try {
    return DATE.format(new Date(v));
  } catch {
    return v;
  }
}

export function formatDateTime(v: string | null | undefined): string {
  if (!v) return "—";
  try {
    return DATETIME.format(new Date(v));
  } catch {
    return v;
  }
}

export function methodLabel(id: string | null): string {
  return (
    {
      "01": "ตกลงราคา",
      "02": "สอบราคา",
      "03": "ประกวดราคา",
      "16": "e-bidding",
      "17": "e-market",
      "19": "เฉพาะเจาะจง",
    }[id || ""] || id || "—"
  );
}

export function stepLabel(id: string | null): string {
  return (
    {
      M03: "ประกาศเชิญชวน",
      W03: "ประกาศผู้ชนะ",
      X01: "ประกาศผู้ชนะ",
      I03: "จัดทำสัญญา",
      C01: "สาระสำคัญในสัญญา",
    }[id || ""] || id || "—"
  );
}

/**
 * Status badge palette mirrors smart_e_gp's flat-fill semantic colors
 * (bg-{color}-50 + text-{color}-700, no border, rounded-full).
 */
export function methodTone(id: string | null): string {
  const map: Record<string, string> = {
    "16": "bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300", // e-bidding
    "17": "bg-sky-50 text-sky-700 dark:bg-sky-950/40 dark:text-sky-300", // e-market
    "19": "bg-purple-50 text-purple-700 dark:bg-purple-950/40 dark:text-purple-300", // เฉพาะเจาะจง
    "02": "bg-orange-50 text-orange-700 dark:bg-orange-950/40 dark:text-orange-300", // สอบราคา
    "03": "bg-pink-50 text-pink-700 dark:bg-pink-950/40 dark:text-pink-300", // ประกวดราคา
    "01": "bg-indigo-50 text-indigo-700 dark:bg-indigo-950/40 dark:text-indigo-300", // ตกลงราคา
  };
  return map[id || ""] || "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300";
}

export function stepTone(id: string | null): string {
  const map: Record<string, string> = {
    M03: "bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300",
    W03: "bg-green-50 text-green-700 dark:bg-green-950/40 dark:text-green-300",
    X01: "bg-green-50 text-green-700 dark:bg-green-950/40 dark:text-green-300",
    I03: "bg-yellow-50 text-yellow-700 dark:bg-yellow-950/40 dark:text-yellow-300",
    C01: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300",
  };
  return map[id || ""] || "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300";
}

export function bidderCountTone(n: number): { cls: string; label: string } {
  if (n === 0)
    return {
      cls: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
      label: "ยังไม่มี",
    };
  if (n === 1)
    return {
      cls: "bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-300",
      label: "1 ราย",
    };
  if (n <= 3)
    return {
      cls: "bg-yellow-50 text-yellow-700 dark:bg-yellow-950/40 dark:text-yellow-300",
      label: `${n} ราย`,
    };
  return {
    cls: "bg-green-50 text-green-700 dark:bg-green-950/40 dark:text-green-300",
    label: `${n} ราย`,
  };
}
