const UNIT_TITLES: Record<string, string> = {
  kg: "кг",
  g: "г",
  pcs: "шт",
  l: "л",
  m: "м",
};

export function unitTitle(unit: string): string {
  return UNIT_TITLES[unit] ?? unit;
}
