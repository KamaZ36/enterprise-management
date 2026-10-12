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
  {
    path: "/documents",
    title: "Журнал",
    icon: "Document",
    permissions: CAN.documentsOpen,
  },
  {
    path: "/balances",
    title: "Остатки",
    icon: "Box",
    permissions: CAN.balancesOpen,
  },
  {
    path: "/nomenclatures",
    title: "Номенклатура",
    icon: "Goods",
    permissions: CAN.nomenclaturesOpen,
  },
  {
    path: "/categories",
    title: "Категории",
    icon: "Files",
    permissions: ["category.read"],
  },
  {
    path: "/warehouses",
    title: "Склады",
    icon: "OfficeBuilding",
    permissions: CAN.warehouseCreate,
  },
  {
    path: "/org-units",
    title: "Организация",
    icon: "Grid",
    permissions: CAN.orgUnitsOpen,
  },
  {
    path: "/employees",
    title: "Сотрудники",
    icon: "User",
    permissions: CAN.employeesOpen,
  },
  { path: "/roles", title: "Роли", icon: "Key", permissions: CAN.rolesOpen },
] as const;

export type Section = (typeof SECTIONS)[number];
