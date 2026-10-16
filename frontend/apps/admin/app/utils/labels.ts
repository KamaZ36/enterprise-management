export const MOVEMENT_TYPES: Record<string, string> = {
  receipt: "Поступление",
  issue: "Выдача",
  write_off: "Списание",
  sale: "Продажа",
  transfer_in: "Перемещение (приход)",
  transfer_out: "Перемещение (расход)",
  production_in: "Производство (приход)",
  production_out: "Производство (расход)",
  inventory_surplus: "Излишек",
  inventory_shortage: "Недостача",
};

export const UNITS: Record<string, string> = {
  kg: "кг",
  g: "г",
  pcs: "шт",
  l: "л",
  m: "м",
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
