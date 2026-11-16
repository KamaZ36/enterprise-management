export type WorkspaceKind = "office" | "cafe" | "shop" | "production";

export type WorkspacePoint = {
  id: string;
  name: string;
  type: string;
  permissions: string[];
};

type WidgetRule = {
  permissions: readonly string[];
  kinds: readonly WorkspaceKind[];
  match?: "all" | "any";
};

/**
 * Что показывать на рабочем месте. Никаких кодов ролей: только права и тип
 * точки. Поэтому своя роль с нужным набором прав подхватится автоматически.
 */
export const WORKSPACE_WIDGETS: Record<string, WidgetRule> = {
  orders: {
    permissions: ["order.read"],
    kinds: ["office", "cafe", "shop", "production"],
  },
  stopList: {
    permissions: ["stop_list.read"],
    kinds: ["cafe", "shop"],
  },
  balances: {
    permissions: ["inventory.balance.read"],
    kinds: ["cafe", "shop", "production"],
  },
  production: {
    permissions: ["production.order.read"],
    kinds: ["office", "cafe", "shop", "production"],
  },
  receipts: {
    permissions: ["inventory.document.read"],
    kinds: ["office", "cafe", "shop", "production"],
  },
  office: {
    permissions: ["nomenclature.read", "staff.employee.read"],
    kinds: ["office"],
    match: "any",
  },
};

export type QuickAction = {
  title: string;
  path: string;
  permissions: readonly string[];
  kinds?: readonly WorkspaceKind[];
};

export const QUICK_ACTIONS: QuickAction[] = [
  {
    title: "Стоп-лист",
    path: "/catalog/stop-list",
    permissions: ["stop_list.read"],
    kinds: ["cafe", "shop"],
  },
  {
    title: "Заказы",
    path: "/orders",
    permissions: ["order.read"],
  },
  {
    title: "Новое поступление",
    path: "/inventory/documents",
    permissions: ["inventory.document.create"],
  },
  {
    title: "Производственные задания",
    path: "/production/orders",
    permissions: ["production.order.read"],
  },
  {
    title: "Номенклатура",
    path: "/catalog/nomenclatures",
    permissions: ["nomenclature.read"],
  },
  {
    title: "Цены",
    path: "/catalog/prices",
    permissions: ["price_list.read"],
  },
  {
    title: "Сотрудники",
    path: "/staff/employees",
    permissions: ["staff.employee.read"],
  },
  {
    title: "Роли и права",
    path: "/staff/roles",
    permissions: ["staff.role.read"],
  },
  {
    title: "Чеки ОФД",
    path: "/catalog/ofd-receipts",
    permissions: ["cash_register.receipt_read"],
  },
  {
    title: "Чеки DoKa",
    path: "/pos/receipts",
    permissions: ["pos.receipt_read"],
  },
];

export function workspaceKind(type: string | null | undefined): WorkspaceKind {
  if (type === "cafe" || type === "shop" || type === "production") {
    return type;
  }

  return "office";
}

export function widgetVisible(
  code: keyof typeof WORKSPACE_WIDGETS,
  kind: WorkspaceKind,
  can: (permission: string) => boolean,
): boolean {
  const rule = WORKSPACE_WIDGETS[code];
  if (!rule) {
    return false;
  }

  const allowed =
    rule.match === "any"
      ? rule.permissions.some(can)
      : rule.permissions.every(can);

  return rule.kinds.includes(kind) && allowed;
}

export function quickActions(
  kind: WorkspaceKind,
  can: (permission: string) => boolean,
): QuickAction[] {
  return QUICK_ACTIONS.filter(
    (action) =>
      (!action.kinds || action.kinds.includes(kind)) &&
      action.permissions.every(can),
  );
}
