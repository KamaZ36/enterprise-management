export const CAN = {
  documentsOpen: ["inventory.document.read", "nomenclature.read"],
  documentsCreate: ["inventory.document.create", "nomenclature.read"],
  balancesOpen: ["inventory.balance.read"],
  lotsOpen: ["inventory.balance.read"],
  movementsOpen: ["inventory.balance.read"],
  nomenclaturesOpen: ["nomenclature.read", "category.read"],
  nomenclatureCreate: ["nomenclature.create", "category.read"],
  orgUnitsOpen: ["org_unit.read"],
  employeesOpen: ["staff.employee.read"],
  employeeEdit: ["staff.employee.manage"],
  employeeResetPassword: ["staff.employee.reset_password"],
  rolesOpen: ["staff.role.read"],
  ordersOpen: ["order.read"],
  customersOpen: ["customer.read"],
  orderCreate: ["order.create", "nomenclature.read"],
  techCardsOpen: ["production.tech_card.read"],
  techCardCreate: [
    "production.tech_card.manage",
    "nomenclature.read",
  ],
  productionOrdersOpen: ["production.order.read"],
  productionOrderCreate: ["production.order.manage"],
} as const;

export const SECTIONS = [
  { path: "/", title: "Главная", icon: "HomeFilled", permissions: [] },
  { module: "inventory", title: "Склад", icon: "OfficeBuilding" },
  { module: "production", title: "Производство", icon: "Box" },
  { module: "catalog", title: "Справочники", icon: "Goods" },
  { module: "staff", title: "Персонал", icon: "User" },
  { module: "sales", title: "Заказы", icon: "Document" },
  { module: "customers", title: "Клиенты", icon: "User" },
] as const;

export type Section = (typeof SECTIONS)[number];
