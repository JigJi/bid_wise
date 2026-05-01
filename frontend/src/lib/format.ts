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
