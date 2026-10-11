export const NOMENCLATURE_TYPES: Record<string, string> = {
  raw_material: "Сырьё",
  semi_finished: "Полуфабрикат",
  finished_good: "Готовая продукция",
};

export const UNITS: Record<string, string> = {
  kg: "кг",
  g: "г",
  pcs: "шт",
  l: "л",
  m: "м",
};

export const WAREHOUSE_TYPES: Record<string, string> = {
  raw: "Склад сырья",
  production: "Производство",
  finished: "Готовая продукция",
  shop: "Магазин",
};

export function label(
  dictionary: Record<string, string>,
  code: string | null | undefined,
): string {
  if (!code) {
    return "—";
  }

  return dictionary[code] ?? code;
}
