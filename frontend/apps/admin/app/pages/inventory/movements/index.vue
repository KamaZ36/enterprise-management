<template>
  <div class="page">
    <h1 class="page__title">Движения</h1>
    <p class="page__subtitle">
      Регистр движений: приход и расход по подразделениям
    </p>

    <el-alert
      v-if="!canAll(CAN.movementsOpen)"
      title="Нет права видеть движения"
      description="Попросите доступ к остаткам."
      type="warning"
      :closable="false"
      show-icon
      class="page__error"
    />

    <div v-if="canAll(CAN.movementsOpen)" class="page__toolbar">
      <el-select
        v-model="locationId"
        placeholder="Все подразделения"
        clearable
        style="width: 260px"
        @change="reload"
      >
        <el-option label="Все подразделения" :value="''" />
        <LocationOptions :locations="locations" />
      </el-select>

      <el-select
        v-model="nomenclatureId"
        filterable
        clearable
        placeholder="Все номенклатуры"
        style="width: 280px"
        @change="reload"
      >
        <el-option label="Все номенклатуры" :value="''" />
        <el-option
          v-for="item in nomenclatures"
          :key="item.id"
          :label="item.sku ? `${item.name} · ${item.sku}` : item.name"
          :value="item.id"
        />
      </el-select>

      <el-select
        v-model="movementTypes"
        multiple
        collapse-tags
        clearable
        placeholder="Все типы"
        style="width: 260px"
      >
        <el-option
          v-for="(title, code) in MOVEMENT_TYPES"
          :key="code"
          :label="title"
          :value="code"
        />
      </el-select>

      <el-date-picker
        v-model="period"
        type="datetimerange"
        range-separator="—"
        start-placeholder="С"
        end-placeholder="По"
        style="width: 380px"
      />

      <el-button type="primary" :loading="pending" @click="reload">Показать</el-button>
    </div>

    <el-alert
      v-if="error"
      :title="error"
      type="error"
      :closable="false"
      show-icon
      class="page__error"
    />

    <el-table
      v-if="canAll(CAN.movementsOpen)"
      v-loading="pending"
      :data="items"
      empty-text="Движений нет"
      class="page__table"
    >
      <el-table-column label="Дата" width="170">
        <template #default="{ row }">{{ formatDateTime(row.occurred_at) }}</template>
      </el-table-column>
      <el-table-column label="Подразделение" min-width="180">
        <template #default="{ row }">{{ row.location_name ?? "—" }}</template>
      </el-table-column>
      <el-table-column label="Номенклатура" min-width="240">
        <template #default="{ row }">
          {{ row.nomenclature_name ?? shortId(row.nomenclature_id) }}
        </template>
      </el-table-column>
      <el-table-column label="Партия" width="160">
        <template #default="{ row }">{{ row.lot_code ?? "—" }}</template>
      </el-table-column>
      <el-table-column label="Тип" min-width="200">
        <template #default="{ row }">
          {{ label(MOVEMENT_TYPES, row.movement_type) }}
        </template>
      </el-table-column>
      <el-table-column label="Количество" width="150" align="right">
        <template #default="{ row }">
          <span :class="{ 'qty--negative': Number(row.quantity) < 0 }">
            {{ quantityText(row.quantity) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="Сумма" width="160" align="right">
        <template #default="{ row }">
          {{
            row.total_cost_kopecks === null || row.total_cost_kopecks === undefined
              ? "—"
              : formatKopecks(row.total_cost_kopecks)
          }}
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-if="canAll(CAN.movementsOpen)"
      v-model:current-page="page"
      class="pager"
      layout="prev, pager, next, total"
      :page-size="PAGE_SIZE"
      :total="total"
      :disabled="pending"
      @current-change="load"
    />
  </div>
</template>

<script setup lang="ts">
import { CAN } from "~/utils/access";

definePageMeta({ permissions: CAN.movementsOpen });

import type { components } from "@md/api-client";
import { formatKopecks, formatQuantity } from "@md/money";

import { shortId } from "~/utils/format";
import { label, MOVEMENT_TYPES } from "~/utils/labels";
import type { Location } from "~/utils/locations";

type MovementItem = components["schemas"]["MovementItemSchema"];
type Nomenclature = components["schemas"]["NomenclatureSchema"];

const PAGE_SIZE = 50;

const api = useApi();

const locations = ref<Location[]>([]);
const nomenclatures = ref<Nomenclature[]>([]);
const items = ref<MovementItem[]>([]);
const total = ref(0);
const page = ref(1);
const pending = ref(false);
const error = ref("");

const locationId = ref("");
const nomenclatureId = ref("");
const movementTypes = ref<string[]>([]);
const period = ref<[Date, Date] | null>(null);

function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function quantityText(value: string | null | undefined): string {
  if (value === null || value === undefined || value === "") {
    return "—";
  }

  const numeric = Number(value);
  if (Number.isNaN(numeric)) {
    return formatQuantity(value);
  }

  const sign = numeric > 0 ? "+" : numeric < 0 ? "−" : "";

  return `${sign}${formatQuantity(Math.abs(numeric))}`;
}

async function loadLocations(): Promise<void> {
  if (!canAll(CAN.movementsOpen)) {
    return;
  }

  const { data, response } = await api.GET("/api/inventory/locations", {});

  if (response.ok && data) {
    locations.value = data;
  }
}

async function loadNomenclatures(): Promise<void> {
  if (!canAll(CAN.movementsOpen)) {
    return;
  }

  const { data, response } = await api.GET("/api/catalog/nomenclatures", {
    params: { query: { limit: 100 } },
  });

  if (response.ok && data) {
    nomenclatures.value = data.items;
  }
}

async function load(): Promise<void> {
  pending.value = true;
  error.value = "";

  try {
    const { response, data, error: failure } = await api.GET(
      "/api/inventory/movements",
      {
        params: {
          query: {
            org_unit_id: locationId.value || undefined,
            nomenclature_id: nomenclatureId.value || undefined,
            movement_types: movementTypes.value.length
              ? movementTypes.value.join(",")
              : undefined,
            occurred_from: period.value?.[0]?.toISOString(),
            occurred_to: period.value?.[1]?.toISOString(),
            limit: PAGE_SIZE,
            offset: (page.value - 1) * PAGE_SIZE,
          },
        },
      },
    );

    if (!response.ok || !data) {
      const payload = failure as { message?: string } | undefined;
      throw new Error(
        payload?.message ?? `Не удалось загрузить движения: ${response.status}`,
      );
    }

    items.value = data.items;
    total.value = data.total;
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Ошибка загрузки";
  } finally {
    pending.value = false;
  }
}

async function reload(): Promise<void> {
  page.value = 1;
  await load();
}

onMounted(async () => {
  await loadLocations();
  await loadNomenclatures();
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

.pager {
  margin-top: 18px;
  justify-content: flex-end;
}

.qty--negative {
  color: var(--el-color-danger);
}
</style>
