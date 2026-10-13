<template>
  <div class="page">
    <h1 class="page__title">{{ greeting }}, {{ name }}</h1>
    <p class="page__subtitle">{{ subtitle }}</p>

    <div v-if="tiles.length" class="tiles">
      <div
        v-for="tile in tiles"
        :key="tile.title"
        class="tile"
        @click="router.push(tile.path)"
      >
        <div class="tile__value">{{ tile.value }}</div>
        <div class="tile__title">{{ tile.title }}</div>
      </div>
    </div>

    <section v-if="actions.length" class="block">
      <div class="block__title">Быстрые действия</div>
      <div class="actions">
        <el-button
          v-for="action in actions"
          :key="action.title"
          type="primary"
          plain
          @click="router.push(action.path)"
        >
          {{ action.title }}
        </el-button>
      </div>
    </section>

    <section v-if="documents.length" class="block">
      <div class="block__title">Последние поступления</div>
      <el-table :data="documents" empty-text="Документов пока нет">
        <el-table-column label="Дата" width="160">
          <template #default="{ row }">{{ formatDate(row.occurred_at) }}</template>
        </el-table-column>
        <el-table-column label="Поставщик" min-width="200">
          <template #default="{ row }">{{ row.supplier_name ?? "—" }}</template>
        </el-table-column>
        <el-table-column label="Документ" width="160">
          <template #default="{ row }">
            {{ row.supplier_document_number ?? "—" }}
          </template>
        </el-table-column>
        <el-table-column label="Сумма" width="160" align="right">
          <template #default="{ row }">{{ formatKopecks(row.total_kopecks) }}</template>
        </el-table-column>
        <el-table-column label="Статус" width="120">
          <template #default="{ row }">
            <el-tag :type="row.status === 'posted' ? 'success' : 'info'" effect="light">
              {{ row.status === "posted" ? "проведён" : "черновик" }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <el-alert
      v-if="!tiles.length && !actions.length"
      type="info"
      :closable="false"
      show-icon
      title="Доступных разделов пока нет"
      description="Обратитесь к администратору, чтобы вам выдали права на работу."
    />
  </div>
</template>

<script setup lang="ts">
import type { components } from "@md/api-client";
import { formatKopecks } from "@md/money";

import { formatDate } from "~/utils/format";

type Receipt = components["schemas"]["ReceiptListItemSchema"];

const router = useRouter();
const api = useApi();
const { user, can, load } = useCurrentUser();

const documents = ref<Receipt[]>([]);
const counts = reactive({ warehouses: 0, nomenclatures: 0, employees: 0 });

const name = computed(() => {
  const parts = [user.value?.first_name, user.value?.last_name].filter(Boolean);

  return parts.join(" ") || user.value?.roles[0]?.name || "коллега";
});

const greeting = computed(() => {
  const hour = new Date().getHours();

  if (hour < 6) {
    return "Доброй ночи";
  }
  if (hour < 12) {
    return "Доброе утро";
  }
  if (hour < 18) {
    return "Добрый день";
  }

  return "Добрый вечер";
});

const subtitle = computed(() => user.value?.position || "Рабочее место");

const tiles = computed(() => {
  const result: { title: string; value: number; path: string }[] = [];

  if (can("inventory.warehouse.read")) {
    result.push({
      title: "Склады",
      value: counts.warehouses,
      path: "/inventory/warehouses",
    });
  }
  if (can("nomenclature.read")) {
    result.push({
      title: "Номенклатура",
      value: counts.nomenclatures,
      path: "/catalog/nomenclatures",
    });
  }
  if (can("staff.employee.read")) {
    result.push({
      title: "Сотрудники",
      value: counts.employees,
      path: "/staff/employees",
    });
  }

  return result;
});

const actions = computed(() => {
  const result: { title: string; path: string }[] = [];

  if (can("inventory.document.create") && can("inventory.warehouse.read")) {
    result.push({ title: "Новое поступление", path: "/inventory/documents" });
  }
  if (can("nomenclature.create") && can("category.read")) {
    result.push({ title: "Добавить номенклатуру", path: "/catalog/nomenclatures" });
  }
  if (can("staff.employee.manage")) {
    result.push({ title: "Принять на работу", path: "/staff/employees" });
  }
  if (can("staff.role.read")) {
    result.push({ title: "Роли и права", path: "/staff/roles" });
  }

  return result;
});

async function loadTiles(): Promise<void> {
  if (can("inventory.warehouse.read")) {
    const { data, response } = await api.GET("/api/inventory/warehouses", {});
    if (response.ok && data) {
      counts.warehouses = data.length;
    }
  }

  if (can("nomenclature.read")) {
    const { data, response } = await api.GET("/api/catalog/nomenclatures", {
      params: { query: { limit: 1 } },
    });
    if (response.ok && data) {
      counts.nomenclatures = data.total;
    }
  }

  if (can("staff.employee.read")) {
    const { data, response } = await api.GET("/api/staff/employees", {
      params: { query: { limit: 1 } },
    });
    if (response.ok && data) {
      counts.employees = data.total;
    }
  }
}

async function loadDocuments(): Promise<void> {
  if (!can("inventory.document.read") || !can("inventory.warehouse.read")) {
    return;
  }

  const { data, response } = await api.GET("/api/inventory/receipts", {
    params: { query: { limit: 5 } },
  });

  if (response.ok && data) {
    documents.value = data.items;
  }
}

onMounted(async () => {
  await load();
  await loadTiles();
  await loadDocuments();
});
</script>

<style scoped>
.tiles {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.tile {
  padding: 18px 20px;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 10px;
  cursor: pointer;
  transition:
    border-color 0.2s,
    box-shadow 0.2s;
}

.tile:hover {
  border-color: #c6c9cf;
  box-shadow: 0 2px 12px rgb(0 0 0 / 6%);
}

.tile__value {
  font-size: 28px;
  font-weight: 600;
  line-height: 1.2;
}

.tile__title {
  margin-top: 4px;
  color: #909399;
  font-size: 13px;
}

.block {
  margin-top: 24px;
}

.block__title {
  margin-bottom: 12px;
  font-weight: 600;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
