import type { Component } from "vue";

import {
  Box,
  Document,
  Files,
  Goods,
  Grid,
  Key,
  Money,
  OfficeBuilding,
  Switch,
  User,
} from "@element-plus/icons-vue";

import { CAN } from "~/utils/access";

export const MODULE_ICONS: Record<string, Component> = {
  HomeFilled: OfficeBuilding,
  OfficeBuilding,
  Goods,
  User,
  Document,
  Box,
  Files,
  Grid,
  Key,
  Money,
  Switch,
};

export type ModuleTab = {
  path: string;
  title: string;
  icon: keyof typeof MODULE_ICONS | string;
  permissions: readonly string[];
};

export type ModuleDefinition = {
  code: string;
  title: string;
  icon: string;
  tabs: ModuleTab[];
};

export const MODULES: ModuleDefinition[
] = [
  {
    code: "inventory",
    title: "Склад",
    icon: "OfficeBuilding",
    tabs: [
      {
        path: "/inventory/documents",
        title: "Журнал",
        icon: "Document",
        permissions: CAN.documentsOpen,
      },
      {
        path: "/inventory/balances",
        title: "Остатки",
        icon: "Box",
        permissions: CAN.balancesOpen,
      },
      {
        path: "/inventory/lots",
        title: "Партии",
        icon: "Files",
        permissions: CAN.lotsOpen,
      },
      {
        path: "/inventory/movements",
        title: "Движения",
        icon: "Switch",
        permissions: CAN.movementsOpen,
      },
    ],
  },
  {
    code: "production",
    title: "Производство",
    icon: "Box",
    tabs: [
      {
        path: "/production/tech-cards",
        title: "Техкарты",
        icon: "Files",
        permissions: CAN.techCardsOpen,
      },
      {
        path: "/production/orders",
        title: "Задания",
        icon: "Box",
        permissions: CAN.productionOrdersOpen,
      },
    ],
  },
  {
    code: "catalog",
    title: "Справочники",
    icon: "Goods",
    tabs: [
      {
        path: "/catalog/nomenclatures",
        title: "Номенклатура",
        icon: "Goods",
        permissions: CAN.nomenclaturesOpen,
      },
      {
        path: "/catalog/categories",
        title: "Категории",
        icon: "Files",
        permissions: ["category.read"],
      },
      {
        path: "/catalog/org-units",
        title: "Организация",
        icon: "Grid",
        permissions: CAN.orgUnitsOpen,
      },
      {
        path: "/catalog/cash-registers",
        title: "Кассы",
        icon: "Money",
        permissions: CAN.cashRegistersOpen,
      },
      {
        path: "/catalog/ofd-receipts",
        title: "Чеки ОФД",
        icon: "Document",
        permissions: CAN.ofdReceiptsOpen,
      },
      {
        path: "/catalog/prices",
        title: "Цены",
        icon: "Money",
        permissions: ["price_list.read", "price.read"],
      },
    ],
  },
  {
    code: "staff",
    title: "Персонал",
    icon: "User",
    tabs: [
      {
        path: "/staff/employees",
        title: "Сотрудники",
        icon: "User",
        permissions: CAN.employeesOpen,
      },
      {
        path: "/staff/roles",
        title: "Роли",
        icon: "Key",
        permissions: CAN.rolesOpen,
      },
    ],
  },
  {
    code: "orders",
    title: "Заказы",
    icon: "Document",
    tabs: [
      {
        path: "/orders",
        title: "Заказы",
        icon: "Document",
        permissions: CAN.ordersOpen,
      },
    ],
  },
  {
    code: "customers",
    title: "Клиенты",
    icon: "User",
    tabs: [
      {
        path: "/customers",
        title: "Клиенты",
        icon: "User",
        permissions: CAN.customersOpen,
      },
    ],
  },
];
