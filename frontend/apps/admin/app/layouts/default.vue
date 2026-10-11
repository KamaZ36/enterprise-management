<template>
  <el-container class="shell">
    <el-aside width="236px" class="shell__aside">
      <div class="brand">
        <div class="brand__mark">МД</div>
        <div>
          <div class="brand__title">Мясная деревня</div>
          <div class="brand__subtitle">рабочее место</div>
        </div>
      </div>

      <el-menu :default-active="activeMenu" router class="shell__menu">
        <el-menu-item v-for="section in visibleSections" :key="section.path" :index="section.path">
          {{ section.title }}
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="shell__header">
        <span class="shell__section">{{ sectionTitle }}</span>

        <div class="who">
          <div class="who__name">{{ currentName }}</div>
          <div class="who__position">{{ currentPosition }}</div>
        </div>

        <el-button text @click="signOut">Выйти</el-button>
      </el-header>

      <el-main class="shell__main">
        <slot />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { useAuth } from "~/composables/useAuth";
import { useCurrentUser } from "~/composables/useCurrentUser";

const route = useRoute();
const { signOut } = useAuth();
const { user, load, can, displayName } = useCurrentUser();

const sections = [
  { path: "/documents", title: "Журнал", permission: "inventory.document.read" },
  { path: "/balances", title: "Остатки", permission: "inventory.balance.read" },
  { path: "/nomenclatures", title: "Номенклатура", permission: "nomenclature.read" },
  { path: "/warehouses", title: "Склады", permission: "inventory.warehouse.read" },
  { path: "/org-units", title: "Организация", permission: "org_unit.read" },
  { path: "/employees", title: "Сотрудники", permission: "staff.employee.read" },
  { path: "/roles", title: "Роли", permission: "staff.role.read" },
];

const visibleSections = computed(() =>
  sections.filter((section) => can(section.permission)),
);

const current = computed(() =>
  sections.find((section) => route.path.startsWith(section.path)),
);
const activeMenu = computed(() => current.value?.path ?? route.path);
const sectionTitle = computed(() => current.value?.title ?? "");
const currentName = computed(() => displayName());
const currentPosition = computed(() => user.value?.position ?? "");

onMounted(load);
</script>

<style scoped>
.shell {
  min-height: 100vh;
}

.shell__aside {
  background: #fff;
  border-right: 1px solid var(--md-border);
  display: flex;
  flex-direction: column;
}

.brand {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 18px 16px;
}

.brand__mark {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: #7f1d1d;
  color: #fff;
  display: grid;
  place-items: center;
  font-weight: 700;
  font-size: 13px;
}

.brand__title {
  font-weight: 600;
  font-size: 14px;
}

.brand__subtitle {
  color: #909399;
  font-size: 11px;
}

.shell__menu {
  border-right: none;
}

.shell__header {
  background: #fff;
  border-bottom: 1px solid var(--md-border);
  display: flex;
  align-items: center;
  gap: 16px;
}

.shell__section {
  font-weight: 600;
}

.who {
  margin-left: auto;
  text-align: right;
  line-height: 1.25;
}

.who__name {
  font-size: 13px;
  font-weight: 600;
}

.who__position {
  font-size: 11px;
  color: #909399;
}

.shell__main {
  padding: 0;
}
</style>
