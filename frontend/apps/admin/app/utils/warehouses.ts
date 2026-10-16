import type { components } from "@md/api-client";

export type Warehouse = components["schemas"]["WarehouseSchema"];

export type WarehouseGroup = {
  key: string;
  title: string;
  warehouses: Warehouse[];
};

/**
 * Склады разных точек часто называются одинаково («Основной склад»).
 * Показываем название точки рядом со складом, чтобы их различать.
 */
export function warehouseDisplay(
  warehouse: Warehouse | null | undefined,
): string {
  if (!warehouse) {
    return "—";
  }

  return warehouse.org_unit_name
    ? `${warehouse.org_unit_name} — ${warehouse.name}`
    : warehouse.name;
}

/** Группирует склады по подразделению-владельцу (для выпадающих списков). */
export function groupWarehousesByUnit(
  warehouses: readonly Warehouse[],
): WarehouseGroup[] {
  const groups = new Map<string, WarehouseGroup>();

  for (const warehouse of warehouses) {
    const existing = groups.get(warehouse.org_unit_id);

    if (existing) {
      existing.warehouses.push(warehouse);
    } else {
      groups.set(warehouse.org_unit_id, {
        key: warehouse.org_unit_id,
        title: warehouse.org_unit_name ?? warehouse.name,
        warehouses: [warehouse],
      });
    }
  }

  return [...groups.values()];
}
