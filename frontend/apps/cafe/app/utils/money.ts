const UNIT_LABELS: Record<string, string> = {
  kg: "кг",
  g: "г",
  l: "л",
  m: "м",
  pcs: "шт",
};


export function unitLabel(unit: string | null | undefined): string {
  return unit ? (UNIT_LABELS[unit] ?? "") : "";
}


export function trimQuantity(quantity: number): number {
  return Math.round(quantity * 1000) / 1000;
}


export function priceLabel(kopecks: number | null | undefined): string {
  if (kopecks === null || kopecks === undefined) {
    return "—";
  }

  const rubles = kopecks / 100;
  const formatted = Number.isInteger(rubles)
    ? rubles.toLocaleString("ru-RU")
    : rubles.toLocaleString("ru-RU", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      });

  return `${formatted}\u00a0₽`;
}


export function priceWithUnit(
  kopecks: number | null | undefined,
  unit: string | null | undefined,
): string {
  const price = priceLabel(kopecks);
  const label = unitLabel(unit);

  if (!label || unit === "pcs") {
    return price;
  }

  return `${price}/${label}`;
}


export function quantityLabel(
  quantity: number,
  unit: string | null | undefined,
): string {
  const value = trimQuantity(quantity);
  const label = unitLabel(unit);

  return label ? `${value} ${label}` : String(value);
}


export function lineTotal(quantity: number, unitPrice: number): number {
  return Math.round(trimQuantity(quantity) * unitPrice);
}
