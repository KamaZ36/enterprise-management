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
  warehouseCreate: ["inventory.warehouse.manage", "org_unit.read"],
  warehouseEdit: ["inventory.warehouse.manage"],
  balancesOpen: ["inventory.balance.read", "inventory.warehouse.read"],
  nomenclaturesOpen: ["nomenclature.read", "category.read"],
  nomenclatureCreate: ["nomenclature.create", "category.read"],
  orgUnitsOpen: ["org_unit.read", "inventory.warehouse.read"],
  employeesOpen: ["staff.employee.read"],
  employeeEdit: ["staff.employee.manage"],
  employeeResetPassword: ["staff.employee.reset_password"],
  rolesOpen: ["staff.role.read"],
} as const;

export const SECTIONS = [
  { path: "/", title: "Главная", icon: "HomeFilled", permissions: [] },
  { module: "inventory", title: "Склад", icon: "OfficeBuilding" },
  { module: "catalog", title: "Справочники", icon: "Goods" },
  { module: "staff", title: "Персонал", icon: "User" },
] as const;

export type Section = (typeof SECTIONS)[number];
