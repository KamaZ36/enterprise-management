<template>
  <div class="page">
    <div class="workspace-head">
      <div>
        <h1 class="page__title">{{ greeting }}, {{ name }}</h1>
        <p class="page__subtitle">{{ subtitle }}</p>
      </div>

      <div class="workspace-head__point">
        <el-select
          v-if="points.length > 1"
          v-model="selectedId"
          placeholder="Точка"
          style="width: 300px"
          @change="loadAll"
        >
          <el-option v-if="isCompanyWide" label="Вся сеть" value="" />
          <el-option
            v-for="point in points"
            :key="point.id"
            :label="point.name"
            :value="point.id"
          />
        </el-select>
        <el-tag v-else-if="selected" type="info" effect="light" size="large">
          {{ selected.name }}
        </el-tag>
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

    <div v-if="kpis.length" class="tiles">
      <div
        v-for="kpi in kpis"
        :key="kpi.title"
        class="tile"
        :class="{ 'tile--link': kpi.path }"
        @click="kpi.path && router.push(kpi.path)"
      >
        <div class="tile__value">{{ kpi.value }}</div>
        <div class="tile__title">{{ kpi.title }}</div>
        <div v-if="kpi.hint" class="tile__hint">{{ kpi.hint }}</div>
      </div>
    </div>

    <section v-if="actions.length" class="block">
      <div class="block__title">Быстрые действия</div>
      <div class="actions">
        <el-button
          v-for="action in actions"
          :key="action.path"
          type="primary"
          plain
          @click="router.push(action.path)"
        >
          {{ action.title }}
        </el-button>
      </div>
    </section>

    <div class="workspace-grid">
      <section v-if="widgets.orders" class="block">
        <div class="block__title">
          Заказы сегодня
          <router-link class="block__link" to="/orders">все заказы</router-link>
        </div>

        <el-table :data="orders" empty-text="Заказов пока нет" size="small">
          <el-table-column label="№" width="80">
            <template #default="{ row }">{{ row.number ?? "—" }}</template>
          </el-table-column>
          <el-table-column label="Статус" width="130">
            <template #default="{ row }">
              <el-tag :type="orderStatusType(row.status)" effect="light">
                {{ orderStatusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="Сумма" width="130" align="right">
            <template #default="{ row }">
              {{ formatKopecks(row.total) }}
            </template>
          </el-table-column>
          <el-table-column label="Создан" width="110">
            <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
          </el-table-column>
          <el-table-column width="110" align="right">
            <template #default="{ row }">
              <el-button
                text
                @click="router.push(`/orders/${row.id}`)"
              >
                Открыть
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </section>

      <section v-if="widgets.stopList" class="block">
        <div class="block__title">
          Стоп-лист
          <router-link class="block__link" to="/catalog/stop-list">
            управлять
          </router-link>
        </div>

        <el-empty
          v-if="!stopItems.length"
          description="Все позиции в продаже"
          :image-size="60"
        />

        <div v-for="item in stopItems" :key="item.nomenclature_id" class="stop-row">
          <div>
            <div>{{ item.nomenclature_name }}</div>
            <div class="muted hint">{{ item.sku }}</div>
          </div>
          <el-button
            v-if="canManageStop"
            text
            type="success"
            :loading="busyStopId === item.nomenclature_id"
            @click="resumeStop(item as StopItem)"
          >
            вернуть
          </el-button>
        </div>
      </section>

      <section v-if="widgets.balances" class="block">
        <div class="block__title">
          Остатки точки
          <router-link class="block__link" to="/inventory/balances">
            подробнее
          </router-link>
        </div>

        <el-table :data="balances" empty-text="Остатков пока нет" size="small">
          <el-table-column prop="nomenclature_name" label="Товар" min-width="200">
            <template #default="{ row }">{{ row.nomenclature_name ?? "—" }}</template>
          </el-table-column>
          <el-table-column label="Количество" width="130" align="right">
            <template #default="{ row }">
              {{ formatQuantity(row.quantity) }}
            </template>
          </el-table-column>
        </el-table>

        <div v-if="balancesTotal > balances.length" class="muted hint block__foot">
          Всего позиций: {{ balancesTotal }}
        </div>
      </section>

      <section v-if="widgets.production" class="block">
        <div class="block__title">
          Производство
          <router-link class="block__link" to="/production/orders">
            все задания
          </router-link>
        </div>

        <el-table
          :data="productionOrders"
          empty-text="Заданий пока нет"
          size="small"
        >
          <el-table-column label="Техкарта" min-width="180">
            <template #default="{ row }">{{ row.tech_card_code }}</template>
          </el-table-column>
          <el-table-column label="Статус" width="120">
            <template #default="{ row }">
              <el-tag
                :type="row.status === 'posted' ? 'success' : 'info'"
                effect="light"
              >
                {{ productionStatusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="Дата" width="110">
            <template #default="{ row }">{{ formatDate(row.occurred_at) }}</template>
          </el-table-column>
        </el-table>
      </section>

      <section v-if="widgets.receipts" class="block">
        <div class="block__title">
          Последние поступления
          <router-link class="block__link" to="/inventory/documents">
            журнал
          </router-link>
        </div>

        <el-table :data="receipts" empty-text="Поступлений пока нет" size="small">
          <el-table-column label="Поставщик" min-width="180">
            <template #default="{ row }">{{ row.supplier_name ?? "—" }}</template>
          </el-table-column>
          <el-table-column label="Дата" width="110">
            <template #default="{ row }">{{ formatDate(row.occurred_at) }}</template>
          </el-table-column>
          <el-table-column label="Сумма" width="130" align="right">
            <template #default="{ row }">
              {{ formatKopecks(row.total_kopecks) }}
            </template>
          </el-table-column>
        </el-table>
      </section>
    </div>

    <el-alert
      v-if="!kpis.length && !actions.length && !visibleBlocks"
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
import {
  quickActions,
  widgetVisible,
  workspaceKind,
  type WorkspaceKind,
  type WorkspacePoint,
} from "~/utils/workspace";

type Order = components["schemas"]["OrderListItemSchema"];
type ProductionOrder = components["schemas"]["ProductionOrderListItemSchema"];
type Balance = components["schemas"]["BalanceSchema"];
type Receipt = components["schemas"]["ReceiptListItemSchema"];
type StopItem = components["schemas"]["StopListItemSchema"];
type OrgUnit = components["schemas"]["OrgUnitSchema"];

const router = useRouter();
const api = useApi();
const { user, can, load } = useCurrentUser();
const { units, load: loadUnits } = useMyUnits();

const points = ref<WorkspacePoint[]>([]);
const selectedId = ref("");
const error = ref("");

const orders = ref<Order[]>([]);
const ordersTotal = ref(0);
const stopItems = ref<StopItem[]>([]);
const balances = ref<Balance[]>([]);
const balancesTotal = ref(0);
const productionOrders = ref<ProductionOrder[]>([]);
const productionTotal = ref(0);
const receipts = ref<Receipt[]>([]);
const receiptsTotal = ref(0);
const nomenclatureTotal = ref(0);
const employeeTotal = ref(0);
const busyStopId = ref("");

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

const subtitle = computed(() => {
  const position = user.value?.position || "Рабочее место";

  return selected.value ? `${position} · ${selected.value.name}` : position;
});

const isCompanyWide = computed(() => (user.value?.scopes?.length ?? 0) === 0);

const selected = computed(
  () => points.value.find((point) => point.id === selectedId.value) ?? null,
);

const kind = computed<WorkspaceKind>(() => workspaceKind(selected.value?.type));

function pointCan(permission: string): boolean {
  if (isCompanyWide.value) {
    return can(permission);
  }

  return selected.value?.permissions.includes(permission) ?? false;
}

const canManageStop = computed(() => pointCan("stop_list.manage"));

const widgets = computed(() => ({
  orders: widgetVisible("orders", kind.value, pointCan),
  stopList: widgetVisible("stopList", kind.value, pointCan),
  balances: widgetVisible("balances", kind.value, pointCan),
  production: widgetVisible("production", kind.value, pointCan),
  receipts: widgetVisible("receipts", kind.value, pointCan),
  office: widgetVisible("office", kind.value, pointCan),
}));

const visibleBlocks = computed(() => Object.values(widgets.value).some(Boolean));

const actions = computed(() =>
  quickActions(kind.value, (permission) =>
    isCompanyWide.value ? can(permission) : pointCan(permission),
  ),
);

const orderStats = computed(() => {
  const result = { new: 0, preparing: 0, ready: 0 };

  for (const order of orders.value) {
    if (order.status === "new") {
      result.new += 1;
    } else if (order.status === "preparing" || order.status === "confirmed") {
      result.preparing += 1;
    } else if (order.status === "ready") {
      result.ready += 1;
    }
  }

  return result;
});

const kpis = computed(() => {
  const items: { title: string; value: string; hint?: string; path?: string }[] = [];

  if (widgets.value.orders) {
    items.push({
      title: "Заказы сегодня",
      value: String(ordersTotal.value),
      hint: `${orderStats.value.new} новых · ${orderStats.value.preparing} в работе · ${orderStats.value.ready} готовы`,
      path: "/orders",
    });
  }

  if (widgets.value.stopList) {
    items.push({
      title: "В стоп-листе",
      value: String(stopItems.value.length),
      hint: "позиций недоступно",
      path: "/catalog/stop-list",
    });
  }

  if (widgets.value.balances) {
    items.push({
      title: "Позиций на складе",
      value: String(balancesTotal.value),
      hint: "по остаткам точки",
      path: "/inventory/balances",
    });
  }

  if (widgets.value.production) {
    items.push({
      title: "Производство",
      value: String(productionTotal.value),
      hint: "заданий всего",
      path: "/production/orders",
    });
  }

  if (widgets.value.office) {
    if (can("nomenclature.read")) {
      items.push({
        title: "Номенклатура",
        value: String(nomenclatureTotal.value),
        path: "/catalog/nomenclatures",
      });
    }
    if (can("staff.employee.read")) {
      items.push({
        title: "Сотрудники",
        value: String(employeeTotal.value),
        path: "/staff/employees",
      });
    }
  }

  if (widgets.value.receipts) {
    items.push({
      title: "Поступления",
      value: String(receiptsTotal.value),
      path: "/inventory/documents",
    });
  }

  return items;
});

function todayIso(): string {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");

  return `${now.getFullYear()}-${month}-${day}`;
}

function formatQuantity(value: string | number): string {
  const number = Number(value);

  if (!Number.isFinite(number)) {
    return String(value);
  }

  return number.toLocaleString("ru-RU", { maximumFractionDigits: 3 });
}

function orderStatusLabel(status: string): string {
  return (
    {
      draft: "Черновик",
      new: "Новый",
      confirmed: "Подтверждён",
      preparing: "Готовится",
      ready: "Готов",
      completed: "Выдан",
      cancelled: "Отменён",
    }[status] ?? status
  );
}

function orderStatusType(status: string): "success" | "warning" | "info" | "danger" | "primary" {
  if (status === "new") {
    return "warning";
  }
  if (status === "preparing" || status === "confirmed") {
    return "primary";
  }
  if (status === "ready" || status === "completed") {
    return "success";
  }
  if (status === "cancelled") {
    return "danger";
  }

  return "info";
}

function productionStatusLabel(status: string): string {
  return (
    {
      draft: "Черновик",
      posted: "Проведено",
      cancelled: "Отменено",
    }[status] ?? status
  );
}

async function loadPoints(): Promise<void> {
  await loadUnits();

  const scoped = units.value
    .filter((unit) => unit.type === "cafe" || unit.type === "shop" || unit.type === "production")
    .map((unit) => ({
      id: unit.id,
      name: unit.title,
      type: unit.type,
      permissions: unit.permissions,
    }));

  if (scoped.length) {
    points.value = scoped.sort((a, b) => a.name.localeCompare(b.name));
    return;
  }

  if (!can("org_unit.read")) {
    return;
  }

  const { data, response } = await api.GET("/api/business/org-units", {});

  if (!response.ok || !data) {
    error.value = "Не удалось загрузить список точек";
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
    .sort((a, b) => a.name.localeCompare(b.name));
}

async function loadOrders(): Promise<void> {
  if (!widgets.value.orders) {
    return;
  }

  const { data, response } = await api.GET("/api/orders", {
    params: {
      query: {
        day: todayIso(),
        limit: 100,
        org_unit_id: selected.value?.id ?? undefined,
      },
    },
  });

  if (!response.ok || !data) {
    return;
  }

  orders.value = data.items;
  ordersTotal.value = data.total;
}

async function loadStopList(): Promise<void> {
  if (!widgets.value.stopList || !selected.value) {
    return;
  }

  const { data, response } = await api.GET(
    "/api/catalog/org-units/{org_unit_id}/stop-list",
    { params: { path: { org_unit_id: selected.value.id } } },
  );

  if (response.ok && data) {
    stopItems.value = data.items;
  }
}

async function loadBalances(): Promise<void> {
  if (!widgets.value.balances || !selected.value) {
    return;
  }

  const { data, response } = await api.GET(
    "/api/inventory/locations/{org_unit_id}/balances",
    {
      params: {
        path: { org_unit_id: selected.value.id },
        query: { limit: 6 },
      },
    },
  );

  if (response.ok && data) {
    balances.value = data.items;
    balancesTotal.value = data.total;
  }
}

async function loadProduction(): Promise<void> {
  if (!widgets.value.production) {
    return;
  }

  const { data, response } = await api.GET("/api/production/orders", {
    params: {
      query: {
        limit: 5,
        org_unit_id: selected.value?.id ?? undefined,
      },
    },
  });

  if (response.ok && data) {
    productionOrders.value = data.items;
    productionTotal.value = data.total;
  }
}

async function loadReceipts(): Promise<void> {
  if (!widgets.value.receipts) {
    return;
  }

  const { data, response } = await api.GET("/api/inventory/receipts", {
    params: {
      query: {
        limit: 5,
        org_unit_id: selected.value?.id ?? undefined,
      },
    },
  });

  if (response.ok && data) {
    receipts.value = data.items;
    receiptsTotal.value = data.total;
  }
}

async function loadOfficeCounts(): Promise<void> {
  if (!widgets.value.office) {
    return;
  }

  if (can("nomenclature.read")) {
    const { data, response } = await api.GET("/api/catalog/nomenclatures", {
      params: { query: { limit: 1 } },
    });
    if (response.ok && data) {
      nomenclatureTotal.value = data.total;
    }
  }

  if (can("staff.employee.read")) {
    const { data, response } = await api.GET("/api/staff/employees", {
      params: { query: { limit: 1 } },
    });
    if (response.ok && data) {
      employeeTotal.value = data.total;
    }
  }
}

async function loadAll(): Promise<void> {
  error.value = "";
  orders.value = [];
  ordersTotal.value = 0;
  stopItems.value = [];
  balances.value = [];
  balancesTotal.value = 0;
  productionOrders.value = [];
  productionTotal.value = 0;
  receipts.value = [];
  receiptsTotal.value = 0;

  await Promise.all([
    loadOrders(),
    loadStopList(),
    loadBalances(),
    loadProduction(),
    loadReceipts(),
    loadOfficeCounts(),
  ]);
}

async function resumeStop(item: StopItem): Promise<void> {
  if (!selected.value) {
    return;
  }

  busyStopId.value = item.nomenclature_id;
  error.value = "";

  try {
    const { response } = await api.DELETE(
      "/api/catalog/org-units/{org_unit_id}/stop-list/{nomenclature_id}",
      {
        params: {
          path: {
            org_unit_id: selected.value.id,
            nomenclature_id: item.nomenclature_id,
          },
        },
      },
    );

    if (!response.ok) {
      error.value = "Не удалось вернуть позицию в меню";
      return;
    }

    await loadAll();
  } finally {
    busyStopId.value = "";
  }
}

onMounted(async () => {
  await load();
  await loadPoints();
  selectedId.value = isCompanyWide.value ? "" : (points.value[0]?.id ?? "");
  await loadAll();
});
</script>

<style scoped>
.workspace-head {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.workspace-head__point {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tiles {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.tile {
  padding: 18px 20px;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 10px;
}

.tile--link {
  cursor: pointer;
  transition:
    border-color 0.2s,
    box-shadow 0.2s;
}

.tile--link:hover {
  border-color: #c6c9cf;
  box-shadow: 0 2px 12px rgb(0 0 0 / 6%);
}

.tile__value {
  font-size: 28px;
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

.workspace-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
  gap: 20px;
}

.block {
  padding: 16px 18px;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 10px;
}

.block__title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  font-weight: 600;
}

.block__link {
  color: #409eff;
  font-size: 13px;
  font-weight: 400;
  text-decoration: none;
}

.block__foot {
  margin-top: 10px;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.stop-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid #f0f2f5;
}

.stop-row:last-child {
  border-bottom: none;
}

.muted {
  color: #909399;
}

.hint {
  font-size: 11px;
}
</style>
