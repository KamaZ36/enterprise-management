export const CAN = {
  documentsOpen: [
    "inventory.document.read",
    "inventory.warehouse.read",
    "nomenclature.read",
  ],
  documentsCreate: [
    "inventory.document.create",
    "inventory.warehouse.read",
    "nomenclature.read",
  ],
  warehouseRead: ["inventory.warehouse.read"],
  nomenclatureCreate: ["nomenclature.create", "category.read"],
  balancesOpen: ["inventory.balance.read", "inventory.warehouse.read"],
  nomenclaturesOpen: ["nomenclature.read", "category.read"],
  warehouseCreate: ["inventory.warehouse.manage", "org_unit.read"],
  orgUnitsOpen: ["org_unit.read", "inventory.warehouse.read"],
  warehouseEdit: ["inventory.warehouse.manage"],
  employeesOpen: ["staff.employee.read"],
  employeeEdit: ["staff.employee.manage"],
  employeeResetPassword: ["staff.employee.reset_password"],
  rolesOpen: ["staff.role.read"],
} as const;

export const SECTIONS = [
  { path: "/documents", title: "Журнал", permissions: CAN.documentsOpen },
  { path: "/balances", title: "Остатки", permissions: CAN.balancesOpen },
  {
    path: "/nomenclatures",
    title: "Номенклатура",
    permissions: CAN.nomenclaturesOpen,
  },
  { path: "/categories", title: "Категории", permissions: ["category.read"] },
  { path: "/warehouses", title: "Склады", permissions: CAN.warehouseCreate },
  { path: "/org-units", title: "Организация", permissions: CAN.orgUnitsOpen },
  { path: "/employees", title: "Сотрудники", permissions: CAN.employeesOpen },
  { path: "/roles", title: "Роли", permissions: CAN.rolesOpen },
] as const;

export type Section = (typeof SECTIONS)[number];
