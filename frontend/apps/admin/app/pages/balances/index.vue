<template>
  <div>
    <h1 class="page__title">Остатки</h1>
    <p class="page__subtitle">Что и сколько лежит на складе и по какой себестоимости</p>

    <div class="page__toolbar">
      <el-select
        v-model="warehouseId"
        placeholder="Выберите склад"
        style="width: 320px"
        @change="load"
      >
        <el-option
          v-for="warehouse in warehouses"
          :key="warehouse.id"
          :label="warehouse.name"
          :value="warehouse.id"
        />
      </el-select>
      <el-input
        v-model="filter"
        placeholder="Фильтр по названию"
        style="width: 280px"
        clearable
      />
    </div>

    <el-alert
      v-if="error"
      :title="error"
      type="error"
      :closable="false"
      show-icon
      class="page__error"
    />
    <el-alert
      v-if="loaded && !costVisible"
      title="Себестоимость скрыта"
      description="Нет права видеть стоимость: количества показаны, суммы — нет."
      type="info"
      :closable="false"
      show-icon
      class="page__error"
    />

    <el-table
      v-loading="pending"
      :data="visible"
      empty-text="Остатков нет"
      class="page__table"
    >
      <el-table-column label="Номенклатура" min-width="300">
        <template #default="{ row }">
          {{ row.nomenclature_name ?? shortId(row.nomenclature_id) }}
        </template>
      </el-table-column>
      <el-table-column label="Количество" width="180" align="right">
        <template #default="{ row }">{{ formatQuantity(row.quantity) }}</template>
      </el-table-column>
      <el-table-column
        v-if="costVisible"
        label="Средняя себестоимость"
        width="220"
        align="right"
      >
        <template #default="{ row }">
          {{
            row.average_unit_cost === null
              ? "—"
              : formatKopecks(Math.round(Number(row.average_unit_cost) * 100))
          }}
        </template>
      </el-table-column>
      <el-table-column v-if="costVisible" label="Сумма" width="200" align="right">
        <template #default="{ row }">
          {{
            row.total_value_kopecks === null
              ? "—"
              : formatKopecks(row.total_value_kopecks)
          }}
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import type { components } from "@md/api-client";
import { formatKopecks, formatQuantity } from "@md/money";

import { shortId } from "~/utils/format";

type Warehouse = components["schemas"]["WarehouseSchema"];
type Balance = components["schemas"]["BalanceSchema"];

const api = useApi();
const { can } = useCurrentUser();

const warehouses = ref<Warehouse[]>([]);
const balances = ref<Balance[]>([]);
const warehouseId = ref("");
const filter = ref("");
const pending = ref(false);
const loaded = ref(false);
const error = ref("");

const costVisible = computed(() => can("inventory.cost.read"));

const visible = computed(() => {
  const needle = filter.value.trim().toLowerCase();
  if (!needle) {
    return balances.value;
  }

  return balances.value.filter((item) =>
    (item.nomenclature_name ?? "").toLowerCase().includes(needle),
  );
});

async function loadWarehouses(): Promise<void> {
  const { data, response } = await api.GET("/api/inventory/warehouses", {});

  if (response.ok && data) {
    warehouses.value = data;
    warehouseId.value = data[0]?.id ?? "";
  }
}

async function load(): Promise<void> {
  if (!warehouseId.value) {
    return;
  }

  pending.value = true;
  error.value = "";

  try {
    const { response, data, error: failure } = await api.GET(
      "/api/inventory/warehouses/{warehouse_id}/balances",
      { params: { path: { warehouse_id: warehouseId.value } } },
    );

    if (!response.ok || !data) {
      const payload = failure as { message?: string } | undefined;
      throw new Error(
        payload?.message ?? `Не удалось загрузить остатки: ${response.status}`,
      );
    }

    balances.value = data.items;
    loaded.value = true;
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Ошибка загрузки";
  } finally {
    pending.value = false;
  }
}

onMounted(async () => {
  await loadWarehouses();
  await load();
});
</script>

<style scoped>
.page__error {
  margin-bottom: 12px;
}

.page__table {
  margin-top: 4px;
}
</style>
