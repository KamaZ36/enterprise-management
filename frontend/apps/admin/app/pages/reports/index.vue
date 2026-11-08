<template>
  <div class="page">
    <div class="reports-head">
      <div>
        <h1 class="page__title">Отчёты</h1>
        <p class="page__subtitle">
          Продажи, склад, производство и списания
        </p>
      </div>

      <div class="reports-filters">
        <el-date-picker
          v-model="period"
          type="daterange"
          value-format="YYYY-MM-DD"
          range-separator="—"
          start-placeholder="С"
          end-placeholder="По"
          :clearable="false"
          style="width: 260px"
          @change="load"
        />
        <el-select
          v-if="points.length > 1"
          v-model="selectedUnitId"
          placeholder="Точка"
          style="width: 240px"
          @change="load"
        >
          <el-option v-if="isCompanyWide" label="Все точки" value="" />
          <el-option
            v-for="point in points"
            :key="point.id"
            :label="point.name"
            :value="point.id"
          />
        </el-select>
        <el-tag
          v-if="points.length <= 1 && selectedPoint"
          type="info"
          effect="light"
        >
          {{ selectedPoint.name }}
        </el-tag>
        <el-button :loading="pending" @click="load">Обновить</el-button>
      </div>
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
      v-if="!canSeeCosts"
      type="info"
      :closable="false"
      show-icon
      title="Себестоимость и маржа скрыты"
      description="Для просмотра сумм нужно право inventory.cost.read."
      class="page__error"
    />

    <div v-if="summary" class="tiles">
      <div class="tile">
        <div class="tile__value">{{ formatKopecks(summary.revenue_kopecks) }}</div>
        <div class="tile__title">Выручка</div>
        <div class="tile__hint">{{ summary.receipts_count }} чеков</div>
      </div>
      <div v-if="canSeeCosts" class="tile">
        <div class="tile__value">{{ formatKopecks(summary.cost_kopecks) }}</div>
        <div class="tile__title">Себестоимость</div>
      </div>
      <div
        v-if="canSeeCosts"
        class="tile"
        :class="{ 'tile--negative': (summary.margin_kopecks ?? 0) < 0 }"
      >
        <div class="tile__value">{{ formatKopecks(summary.margin_kopecks) }}</div>
        <div class="tile__title">Маржа</div>
      </div>
      <div v-if="canSeeCosts" class="tile">
        <div class="tile__value">
          {{ formatKopecks(summary.stock_value_kopecks) }}
        </div>
        <div class="tile__title">Стоимость склада</div>
      </div>
      <div class="tile">
        <div class="tile__value">{{ summary.production_orders }}</div>
        <div class="tile__title">Заданий производства</div>
      </div>
      <div v-if="canSeeCosts" class="tile">
        <div class="tile__value">
          {{ formatKopecks(summary.write_off_cost_kopecks) }}
        </div>
        <div class="tile__title">Списания</div>
      </div>
      <div class="tile" :class="{ 'tile--warning': summary.problem_receipts > 0 }">
        <div class="tile__value">{{ summary.problem_receipts }}</div>
        <div class="tile__title">Проблемные чеки DoKa</div>
        <router-link class="tile__link" to="/pos/receipts">
          открыть
        </router-link>
      </div>
    </div>

    <el-tabs v-model="tab">
      <el-tab-pane label="Продажи" name="sales">
        <el-table
          v-loading="pending"
          :data="sales?.items ?? []"
          stripe
          border
          empty-text="Продаж за период нет"
        >
          <el-table-column label="Дата" width="120">
            <template #default="{ row }">{{ formatDate(row.day) }}</template>
          </el-table-column>
          <el-table-column prop="org_unit_name" label="Точка" min-width="220" />
          <el-table-column label="Чеков" width="90" align="right">
            <template #default="{ row }">{{ row.receipts_count }}</template>
          </el-table-column>
          <el-table-column label="Выручка" width="140" align="right">
            <template #default="{ row }">
              {{ formatKopecks(row.revenue_kopecks) }}
            </template>
          </el-table-column>
          <el-table-column
            v-if="canSeeCosts"
            label="Себестоимость"
            width="150"
            align="right"
          >
            <template #default="{ row }">
              {{ formatKopecks(row.cost_kopecks) }}
            </template>
          </el-table-column>
          <el-table-column
            v-if="canSeeCosts"
            label="Маржа"
            width="140"
            align="right"
          >
            <template #default="{ row }">
              <span :class="{ negative: (row.margin_kopecks ?? 0) < 0 }">
                {{ formatKopecks(row.margin_kopecks) }}
              </span>
            </template>
          </el-table-column>
        </el-table>

        <div v-if="sales && sales.items.length" class="totals">
          <span>Итого: {{ sales.total_receipts }} чеков</span>
          <span>Выручка: {{ formatKopecks(sales.total_revenue_kopecks) }}</span>
          <span v-if="canSeeCosts">
            Маржа: {{ formatKopecks(sales.total_margin_kopecks) }}
          </span>
        </div>
      </el-tab-pane>

      <el-tab-pane label="Склад" name="stock">
        <el-table
          v-loading="pending"
          :data="stock?.items ?? []"
          stripe
          border
          empty-text="Остатков нет"
        >
          <el-table-column prop="org_unit_name" label="Точка" min-width="240" />
          <el-table-column label="Позиций" width="110" align="right">
            <template #default="{ row }">{{ row.positions }}</template>
          </el-table-column>
          <el-table-column
            v-if="canSeeCosts"
            label="Стоимость"
            width="160"
            align="right"
          >
            <template #default="{ row }">
              {{ formatKopecks(row.value_kopecks) }}
            </template>
          </el-table-column>
          <el-table-column label="Истекает за 3 дня" width="180" align="right">
            <template #default="{ row }">
              <el-tag v-if="row.expiring_lots" type="warning" effect="light">
                {{ row.expiring_lots }} парт.
              </el-tag>
              <span v-else>—</span>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="Производство" name="production">
        <el-table
          v-loading="pending"
          :data="production?.items ?? []"
          stripe
          border
          empty-text="Выпуска за период нет"
        >
          <el-table-column prop="org_unit_name" label="Цех" min-width="200" />
          <el-table-column prop="tech_card_code" label="Техкарта" min-width="180" />
          <el-table-column label="Заданий" width="100" align="right">
            <template #default="{ row }">{{ row.orders_count }}</template>
          </el-table-column>
          <el-table-column label="Выпуск" width="140" align="right">
            <template #default="{ row }">
              {{ formatQuantity(row.output_quantity) }}
            </template>
          </el-table-column>
          <el-table-column
            v-if="canSeeCosts"
            label="Себестоимость"
            width="160"
            align="right"
          >
            <template #default="{ row }">
              {{ formatKopecks(row.cost_kopecks) }}
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="Списания" name="write-offs">
        <el-table
          v-loading="pending"
          :data="writeOffs?.items ?? []"
          stripe
          border
          empty-text="Списаний за период нет"
        >
          <el-table-column label="Дата" width="120">
            <template #default="{ row }">{{ formatDate(row.day) }}</template>
          </el-table-column>
          <el-table-column prop="org_unit_name" label="Точка" min-width="200" />
          <el-table-column label="Причина" min-width="180">
            <template #default="{ row }">{{ row.reason ?? "—" }}</template>
          </el-table-column>
          <el-table-column label="Документов" width="120" align="right">
            <template #default="{ row }">{{ row.documents_count }}</template>
          </el-table-column>
          <el-table-column label="Количество" width="130" align="right">
            <template #default="{ row }">
              {{ formatQuantity(row.quantity) }}
            </template>
          </el-table-column>
          <el-table-column
            v-if="canSeeCosts"
            label="Стоимость"
            width="150"
            align="right"
          >
            <template #default="{ row }">
              {{ formatKopecks(row.cost_kopecks) }}
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import type { components } from "@md/api-client";
import { formatKopecks } from "@md/money";

import { formatDate } from "~/utils/format";
import type { WorkspacePoint } from "~/utils/workspace";

definePageMeta({ permissions: ["report.read"] });

type Summary = components["schemas"]["ReportSummarySchema"];
type Sales = components["schemas"]["SalesReportSchema"];
type Stock = components["schemas"]["StockReportSchema"];
type Production = components["schemas"]["ProductionReportSchema"];
type WriteOffs = components["schemas"]["WriteOffReportSchema"];
type OrgUnit = components["schemas"]["OrgUnitSchema"];

const api = useApi();
const { user, can, load: loadUser } = useCurrentUser();
const { units, load: loadUnits } = useMyUnits();

const points = ref<WorkspacePoint[]>([]);
const selectedUnitId = ref("");
const period = ref<[string, string]>(defaultPeriod());
const tab = ref("sales");
const pending = ref(false);
const error = ref("");

const summary = ref<Summary | null>(null);
const sales = ref<Sales | null>(null);
const stock = ref<Stock | null>(null);
const production = ref<Production | null>(null);
const writeOffs = ref<WriteOffs | null>(null);

const canSeeCosts = computed(() => can("inventory.cost.read"));
const isCompanyWide = computed(() => (user.value?.scopes?.length ?? 0) === 0);

const selectedPoint = computed(
  () => points.value.find((point) => point.id === selectedUnitId.value) ?? null,
);

function defaultPeriod(): [string, string] {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - 6);

  return [toIso(start), toIso(end)];
}

function toIso(value: Date): string {
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");

  return `${value.getFullYear()}-${month}-${day}`;
}

function formatQuantity(value: string | number): string {
  const number = Number(value);

  return Number.isFinite(number)
    ? number.toLocaleString("ru-RU", { maximumFractionDigits: 3 })
    : String(value);
}

async function loadPoints(): Promise<void> {
  await loadUnits();

  const scoped = units.value
    .filter((unit) =>
      ["cafe", "shop", "production"].includes(unit.type),
    )
    .map((unit) => ({
      id: unit.id,
      name: unit.title,
      type: unit.type,
      permissions: unit.permissions,
    }));

  if (scoped.length) {
    points.value = scoped.sort((left, right) =>
      left.name.localeCompare(right.name),
    );
    return;
  }

  if (!can("org_unit.read")) {
    return;
  }

  const { data, response } = await api.GET("/api/business/org-units", {});

  if (!response.ok || !data) {
    return;
  }

  points.value = (data as OrgUnit[])
    .filter((unit) => ["cafe", "shop", "production"].includes(unit.type))
    .map((unit) => ({
      id: unit.id,
      name: unit.name,
      type: unit.type,
      permissions: [],
    }))
    .sort((left, right) => left.name.localeCompare(right.name));
}

async function load(): Promise<void> {
  pending.value = true;
  error.value = "";

  const [dateFrom, dateTo] = period.value;
  const query = {
    date_from: dateFrom,
    date_to: dateTo,
    org_unit_id: selectedPoint.value?.id,
  };

  try {
    const [summaryResponse, salesResponse, stockResponse, productionResponse, writeOffsResponse] =
      await Promise.all([
        api.GET("/api/reports/summary", { params: { query } }),
        api.GET("/api/reports/sales", { params: { query } }),
        api.GET("/api/reports/stock", {
          params: { query: { org_unit_id: selectedPoint.value?.id } },
        }),
        api.GET("/api/reports/production", { params: { query } }),
        api.GET("/api/reports/write-offs", { params: { query } }),
      ]);

    if (!summaryResponse.response.ok || !summaryResponse.data) {
      throw new Error("Не удалось загрузить сводку");
    }
    if (!salesResponse.response.ok || !salesResponse.data) {
      throw new Error("Не удалось загрузить продажи");
    }
    if (!stockResponse.response.ok || !stockResponse.data) {
      throw new Error("Не удалось загрузить склад");
    }
    if (!productionResponse.response.ok || !productionResponse.data) {
      throw new Error("Не удалось загрузить производство");
    }
    if (!writeOffsResponse.response.ok || !writeOffsResponse.data) {
      throw new Error("Не удалось загрузить списания");
    }

    summary.value = summaryResponse.data;
    sales.value = salesResponse.data;
    stock.value = stockResponse.data;
    production.value = productionResponse.data;
    writeOffs.value = writeOffsResponse.data;
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Ошибка загрузки";
  } finally {
    pending.value = false;
  }
}

onMounted(async () => {
  await loadUser();
  await loadPoints();
  selectedUnitId.value = isCompanyWide.value
    ? ""
    : (points.value[0]?.id ?? "");
  await load();
});
</script>

<style scoped>
.reports-head {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.reports-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.tiles {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  gap: 16px;
  margin: 18px 0 24px;
}

.tile {
  padding: 18px 20px;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 10px;
}

.tile--negative {
  border-color: #f56c6c;
}

.tile--warning {
  border-color: #e6a23c;
}

.tile__value {
  font-size: 24px;
  font-weight: 600;
  line-height: 1.2;
}

.tile__title {
  margin-top: 6px;
  color: #606266;
}

.tile__hint {
  margin-top: 4px;
  color: #909399;
  font-size: 12px;
}

.tile__link {
  display: inline-block;
  margin-top: 6px;
  color: #409eff;
  font-size: 12px;
  text-decoration: none;
}

.totals {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
  margin-top: 14px;
  color: #606266;
  font-weight: 600;
}

.negative {
  color: #f56c6c;
}
</style>
