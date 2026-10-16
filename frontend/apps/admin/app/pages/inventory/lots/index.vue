<template>
  <div class="page">
    <h1 class="page__title">Партии</h1>
    <p class="page__subtitle">
      Партии в подразделениях: срок годности, количество и себестоимость каждой партии
    </p>

    <el-alert
      v-if="!canAll(CAN.lotsOpen)"
      title="Нет права видеть партии"
      description="Попросите доступ к партиям."
      type="warning"
      :closable="false"
      show-icon
      class="page__error"
    />
    <div v-if="canAll(CAN.lotsOpen)" class="page__toolbar">
      <el-select
        v-model="locationId"
        placeholder="Выберите точку"
        style="width: 280px"
        @change="load"
      >
        <LocationOptions :locations="locations" />
      </el-select>
      <el-input
        v-model="filter"
        placeholder="Партия или номенклатура"
        style="width: 260px"
        clearable
        @input="onSearch"
      />
      <el-checkbox v-model="onlyExpiring" @change="load">
        Только с истекающим сроком (14 дней)
      </el-checkbox>
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
      description="Нет права видеть стоимость: количества и сроки показаны, суммы — нет."
      type="info"
      :closable="false"
      show-icon
      class="page__error"
    />

    <el-table
      v-if="canAll(CAN.lotsOpen)"
      v-loading="pending"
      :data="lots"
      empty-text="Партий нет"
      class="page__table"
      :row-class-name="rowClass"
    >
      <el-table-column label="Номенклатура" min-width="240">
        <template #default="{ row }">
          {{ row.nomenclature_name ?? shortId(row.nomenclature_id) }}
        </template>
      </el-table-column>
      <el-table-column label="Партия" width="200">
        <template #default="{ row }">{{ row.lot_code }}</template>
      </el-table-column>
      <el-table-column label="Количество" width="150" align="right">
        <template #default="{ row }">{{ formatQuantity(row.quantity) }}</template>
      </el-table-column>
      <el-table-column label="Годен до" width="180">
        <template #default="{ row }">
          <el-tag v-if="row.expires_at" :type="expiryType(row.expires_at)" effect="light">
            {{ formatDate(row.expires_at) }}
          </el-tag>
          <span v-else>—</span>
        </template>
      </el-table-column>
      <el-table-column label="Поставщик" min-width="180">
        <template #default="{ row }">{{ row.supplier_name ?? "—" }}</template>
      </el-table-column>
      <el-table-column
        v-if="costVisible"
        label="Себестоимость"
        width="170"
        align="right"
      >
        <template #default="{ row }">
          {{
            row.unit_cost === null
              ? "—"
              : formatKopecks(Math.round(Number(row.unit_cost) * 100))
          }}
        </template>
      </el-table-column>
      <el-table-column v-if="costVisible" label="Сумма" width="160" align="right">
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
import { CAN } from "~/utils/access";

definePageMeta({ permissions: CAN.lotsOpen });
import type { components } from "@md/api-client";
import { formatKopecks, formatQuantity } from "@md/money";

import { formatDate, shortId } from "~/utils/format";

type Location = components["schemas"]["LocationSchema"];
type LotBalance = components["schemas"]["LotBalanceSchema"];

const WARNING_DAYS = 14;

const api = useApi();
const { can } = useCurrentUser();

const locations = ref<Location[]>([]);
const lots = ref<LotBalance[]>([]);
const locationId = ref("");
const filter = ref("");
const onlyExpiring = ref(false);
const pending = ref(false);
const loaded = ref(false);
const error = ref("");

const costVisible = computed(() => can("inventory.cost.read"));

let searchTimer: ReturnType<typeof setTimeout> | undefined;

function onSearch(): void {
  if (searchTimer) {
    clearTimeout(searchTimer);
  }

  searchTimer = setTimeout(() => {
    void load();
  }, 300);
}

function daysUntil(value: string): number {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const target = new Date(value);
  target.setHours(0, 0, 0, 0);

  return Math.round((target.getTime() - today.getTime()) / 86_400_000);
}

function expiryType(value: string): "danger" | "warning" | "success" {
  const days = daysUntil(value);

  if (days < 0) return "danger";
  if (days <= WARNING_DAYS) return "warning";

  return "success";
}

function rowClass({ row }: { row: LotBalance }): string {
  if (row.expires_at && daysUntil(row.expires_at) < 0) {
    return "row-expired";
  }

  return "";
}

function expiringBefore(): string | undefined {
  if (!onlyExpiring.value) {
    return undefined;
  }

  const date = new Date();
  date.setDate(date.getDate() + WARNING_DAYS);

  return date.toISOString().slice(0, 10);
}

async function loadLocations(): Promise<void> {
  if (!canAll(CAN.lotsOpen)) {
    return;
  }

  const { data, response } = await api.GET("/api/inventory/locations", {});

  if (response.ok && data) {
    locations.value = data;
    locationId.value = data[0]?.id ?? "";
  }
}

async function load(): Promise<void> {
  if (!locationId.value) {
    return;
  }

  pending.value = true;
  error.value = "";

  try {
    const { response, data, error: failure } = await api.GET(
      "/api/inventory/locations/{org_unit_id}/lots",
      {
        params: {
          path: { org_unit_id: locationId.value },
          query: {
            search: filter.value.trim() || undefined,
            expiring_before: expiringBefore(),
          },
        },
      },
    );

    if (!response.ok || !data) {
      const payload = failure as { message?: string } | undefined;
      throw new Error(
        payload?.message ?? `Не удалось загрузить партии: ${response.status}`,
      );
    }

    lots.value = data.items;
    loaded.value = true;
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Ошибка загрузки";
  } finally {
    pending.value = false;
  }
}

onMounted(async () => {
  await loadLocations();
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

:deep(.row-expired) {
  background: #fef0f0;
}
</style>
