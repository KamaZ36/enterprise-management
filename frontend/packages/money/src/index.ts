const NBSP = "\u00a0";

export function formatKopecks(kopecks: number | null | undefined): string {
  if (kopecks === null || kopecks === undefined) {
    return "—";
  }

  const sign = kopecks < 0 ? "−" : "";
  const absolute = Math.abs(Math.trunc(kopecks));
  const rubles = Math.trunc(absolute / 100);
  const rest = absolute % 100;
  const grouped = new Intl.NumberFormat("ru-RU").format(rubles).replace(/\u00a0/g, NBSP);

  return `${sign}${grouped},${String(rest).padStart(2, "0")}${NBSP}₽`;
}

export function formatKopecksShort(kopecks: number | null | undefined): string {
  return formatKopecks(kopecks).replace(`${NBSP}₽`, "");
}

export function parseRublesToKopecks(input: string | null | undefined): number | null {
  if (!input) {
    return null;
  }

  const cleaned = input.replace(/[\s\u00a0]/g, "").replace(",", ".").replace(/₽|руб\.?/gi, "");
  if (!/^-?\d+(\.\d{0,2})?$/.test(cleaned)) {
    return null;
  }

  const negative = cleaned.startsWith("-");
  const [rubles, fraction = ""] = cleaned.replace("-", "").split(".");
  const kopecks = Number(rubles) * 100 + Number(fraction.padEnd(2, "0"));

  return negative ? -kopecks : kopecks;
}

export function formatQuantity(
  value: string | number | null | undefined,
  digits = 3,
): string {
  if (value === null || value === undefined || value === "") {
    return "—";
  }

  const numeric = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(numeric)) {
    return "—";
  }

  return new Intl.NumberFormat("ru-RU", {
    minimumFractionDigits: 0,
    maximumFractionDigits: digits,
  }).format(numeric);
}
