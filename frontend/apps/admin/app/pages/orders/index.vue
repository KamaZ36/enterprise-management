<template>
  <div class="page">
    <div class="orders-head">
      <div>
        <h1 class="page__title">Заказы</h1>
        <p class="page__subtitle">
          {{ isCompanyWide ? "Все точки" : selectedPoint?.name ?? "Рабочее место" }}
          · обновлено {{ refreshedAt || "—" }}
        </p>
      </div>

      <div class="orders-head__controls">
        <el-select
          v-if="points.length > 1"
          v-model="selectedPointId"
          placeholder="Точка"
          style="width: 240px"
          @change="onPointChange"
        >
          <el-option v-if="isCompanyWide" label="Все точки" value="" />
          <el-option
            v-for="point in points"
            :key="point.id"
            :label="point.name"
            :value="point.id"
          />
        </el-select>
        <el-tag v-else-if="selectedPoint" type="info" effect="light" size="large">
          {{ selectedPoint.name }}
        </el-tag>

        <el-button :loading="pending" @click="manualRefresh">Обновить</el-button>
        <el-button v-if="canCreate" type="primary" @click="openCreate">
          Новый заказ
        </el-button>
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

    <el-tabs v-model="tab" @tab-change="onTabChange">
      <el-tab-pane label="Очередь" name="queue">
        <div class="queue-summary">
          <el-tag type="warning" effect="light">
            Новые: {{ queueCounts.new }}
          </el-tag>
          <el-tag type="primary" effect="light">
            В работе: {{ queueCounts.inProgress }}
          </el-tag>
          <el-tag type="success" effect="light">
            Готовы: {{ queueCounts.ready }}
          </el-tag>
          <el-tag v-if="newArrived" type="danger" effect="dark" class="pulse">
            Новый заказ
          </el-tag>
        </div>

        <div v-loading="pending" class="board">
          <section
            v-for="column in queueColumns"
            :key="column.code"
            class="column"
            :class="`column--${column.code}`"
          >
            <header class="column__head">
              <span>{{ column.title }}</span>
              <span class="column__count">{{ column.items.length }}</span>
            </header>

            <div v-if="!column.items.length" class="column__empty">
              Пока пусто
            </div>

            <article
              v-for="order in column.items"
              :key="order.id"
              class="card"
              :class="{ 'card--urgent': waitingMinutes(order.created_at) >= 30 }"
              @click="openDetail(order)"
            >
              <div class="card__top">
                <strong class="card__number">№{{ order.number ?? "—" }}</strong>
                <span
                  class="card__age"
                  :class="{ 'card__age--urgent': waitingMinutes(order.created_at) >= 30 }"
                >
                  {{ elapsed(order.created_at) }}
                </span>
              </div>

              <div class="card__meta">
                <el-tag size="small" effect="plain">
                  {{ CHANNEL_TITLES[order.channel] ?? order.channel }}
                </el-tag>
                <el-tag size="small" effect="plain">
                  {{ FULFILLMENT_TITLES[order.fulfillment_type] ?? order.fulfillment_type }}
                </el-tag>
                <el-tag
                  size="small"
                  :type="order.payment_status === 'paid' ? 'success' : 'info'"
                  effect="plain"
                >
                  {{ paymentLabel(order) }}
                </el-tag>
              </div>

              <div class="card__row">
                <span>{{ order.line_count }} поз.</span>
                <strong>{{ formatKopecks(order.total) }}</strong>
              </div>

              <div v-if="order.planned_at" class="card__planned">
                К {{ formatTime(order.planned_at) }}
              </div>

              <div v-if="canUpdate || canCancel" class="card__actions">
                <el-button
                  v-if="nextAction(order.status) && canUpdate"
                  type="primary"
                  size="small"
                  :loading="busyId === order.id"
                  @click.stop="runAction(order.id, nextAction(order.status)!.action)"
                >
                  {{ nextAction(order.status)!.label }}
                </el-button>
                <el-button
                  v-if="canCancel && isActive(order.status)"
                  text
                  type="danger"
                  size="small"
                  :loading="busyId === order.id"
                  @click.stop="cancelOrder(order)"
                >
                  Отменить
                </el-button>
              </div>
            </article>
          </section>
        </div>

        <el-empty
          v-if="!pending && !queue.length"
          description="Активных заказов нет"
        />
      </el-tab-pane>

      <el-tab-pane label="История" name="history">
        <div class="history-filters">
          <el-date-picker
            v-model="historyDay"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="Все даты"
            clearable
            style="width: 180px"
            @change="reloadHistory"
          />
          <el-select
            v-model="historyStatuses"
            multiple
            collapse-tags
            placeholder="Все статусы"
            style="width: 280px"
            @change="reloadHistory"
          >
            <el-option
              v-for="(title, code) in STATUS_TITLES"
              :key="code"
              :label="title"
              :value="code"
            />
          </el-select>
          <el-input
            v-model="historySearch"
            placeholder="Поиск по номеру или телефону"
            style="width: 260px"
            clearable
            @keyup.enter="reloadHistory"
          />
          <el-button :loading="historyPending" @click="reloadHistory">
            Найти
          </el-button>
        </div>

        <el-table
          v-loading="historyPending"
          :data="historyItems"
          stripe
          border
          empty-text="Заказов нет"
          @row-click="openDetail"
        >
          <el-table-column label="Номер" width="90">
            <template #default="{ row }">{{ row.number ?? "—" }}</template>
          </el-table-column>
          <el-table-column label="Создан" width="160">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="Статус" width="140">
            <template #default="{ row }">
              <el-tag :type="STATUS_TYPES[row.status] ?? 'info'" effect="light">
                {{ STATUS_TITLES[row.status] ?? row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="Канал" width="110">
            <template #default="{ row }">
              {{ CHANNEL_TITLES[row.channel] ?? row.channel }}
            </template>
          </el-table-column>
          <el-table-column label="Получение" width="120">
            <template #default="{ row }">
              {{ FULFILLMENT_TITLES[row.fulfillment_type] ?? row.fulfillment_type }}
            </template>
          </el-table-column>
          <el-table-column label="Позиций" width="100" align="right">
            <template #default="{ row }">{{ row.line_count }}</template>
          </el-table-column>
          <el-table-column label="Итог" width="130" align="right">
            <template #default="{ row }">{{ formatKopecks(row.total) }}</template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-if="historyTotal > PAGE_SIZE"
          :current-page="historyPage"
          :page-size="PAGE_SIZE"
          :total="historyTotal"
          :disabled="historyPending"
          class="pager"
          layout="prev, pager, next, total"
          @current-change="goToHistoryPage"
        />
      </el-tab-pane>
    </el-tabs>

    <el-drawer v-model="drawerOpen" title="Заказ" size="520px">
      <div v-loading="detailLoading">
        <el-alert
          v-if="detailError"
          :title="detailError"
          type="error"
          :closable="false"
          show-icon
        />

        <template v-if="detail">
          <div class="detail-head">
            <div>
              <div class="detail-number">№{{ detail.number ?? "—" }}</div>
              <div class="muted">
                {{ formatTime(detail.created_at) }} · {{ CHANNEL_TITLES[detail.channel] ?? detail.channel }}
              </div>
            </div>
            <el-tag :type="STATUS_TYPES[detail.status] ?? 'info'" effect="light">
              {{ STATUS_TITLES[detail.status] ?? detail.status }}
            </el-tag>
          </div>

          <el-descriptions :column="1" border size="small" class="detail-info">
            <el-descriptions-item label="Получение">
              {{ FULFILLMENT_TITLES[detail.fulfillment_type] ?? detail.fulfillment_type }}
            </el-descriptions-item>
            <el-descriptions-item label="Оплата">
              {{ paymentLabel(detail) }}
            </el-descriptions-item>
            <el-descriptions-item label="К выдаче">
              {{ detail.planned_at ? formatTime(detail.planned_at) : "Как можно скорее" }}
            </el-descriptions-item>
            <el-descriptions-item v-if="detail.contact_phone" label="Телефон клиента">
              {{ detail.contact_phone }}
            </el-descriptions-item>
            <el-descriptions-item v-if="detail.comment" label="Комментарий">
              {{ detail.comment }}
            </el-descriptions-item>
          </el-descriptions>

          <div class="detail-total">
            <span>Итого</span>
            <strong>{{ formatKopecks(detail.total) }}</strong>
          </div>

          <el-table :data="detail.lines" size="small" class="detail-lines">
            <el-table-column label="Позиция" min-width="180">
              <template #default="{ row }">
                {{ row.nomenclature_name ?? "—" }}
              </template>
            </el-table-column>
            <el-table-column label="Кол-во" width="80" align="right">
              <template #default="{ row }">{{ formatQuantity(row.quantity) }}</template>
            </el-table-column>
            <el-table-column label="Сумма" width="110" align="right">
              <template #default="{ row }">{{ formatKopecks(row.total) }}</template>
            </el-table-column>
          </el-table>

          <div v-if="canUpdate || canCancel" class="detail-actions">
            <el-button
              v-if="nextAction(detail.status) && canUpdate"
              type="primary"
              :loading="busyId === detail.id"
              @click="runAction(detail.id, nextAction(detail.status)!.action)"
            >
              {{ nextAction(detail.status)!.label }}
            </el-button>
            <el-button
              v-if="canCancel && isActive(detail.status)"
              type="danger"
              plain
              :loading="busyId === detail.id"
              @click="cancelOrder(detail)"
            >
              Отменить заказ
            </el-button>
          </div>
        </template>
      </div>
    </el-drawer>

    <el-dialog v-model="createOpen" title="Новый заказ" width="720">
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="Точка">
          <el-select
            v-model="form.org_unit_id"
            placeholder="Подразделение"
            style="width: 100%"
          >
            <el-option
              v-for="point in points"
              :key="point.id"
              :label="point.name"
              :value="point.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="Позиции">
          <OrderLinesEditor
            v-model="form.lines"
            :org-unit-id="form.org_unit_id"
          />
        </el-form-item>

        <el-form-item label="К выдаче">
          <el-date-picker
            v-model="form.planned_at"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ssZ"
            placeholder="Как можно скорее"
            style="width: 100%"
          />
        </el-form-item>

        <el-form-item label="Комментарий">
          <el-input v-model="form.comment" type="textarea" :rows="2" />
        </el-form-item>

        <el-alert
          v-if="createError"
          :title="createError"
          type="error"
          :closable="false"
          show-icon
        />
      </el-form>

      <template #footer>
        <el-button @click="createOpen = false">Отмена</el-button>
        <el-button
          type="primary"
          :loading="saving"
          :disabled="!form.org_unit_id || !form.lines.some((line) => line.nomenclature_id)"
          @click="createOrder"
        >
          Создать
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import type { components } from "@md/api-client";
import { formatKopecks } from "@md/money";
import { ElMessage, ElMessageBox } from "element-plus";

import { CAN } from "~/utils/access";
import type { OrderLineDraft } from "~/utils/orderLines";
import type { WorkspacePoint } from "~/utils/workspace";

definePageMeta({ permissions: CAN.ordersOpen });

type OrderListItem = components["schemas"]["OrderListItemSchema"];
type OrderDetail = components["schemas"]["OrderDetailSchema"];
type OrderAction = "confirm" | "preparing" | "ready" | "completed" | "cancel";

const STATUS_TITLES: Record<string, string> = {
  draft: "Черновик",
  new: "Новый",
  confirmed: "Подтверждён",
  preparing: "Готовится",
  ready: "Готов",
  completed: "Выдан",
  cancelled: "Отменён",
};

const STATUS_TYPES: Record<string, "success" | "warning" | "info" | "danger" | "primary"> = {
  draft: "info",
  new: "warning",
  confirmed: "primary",
  preparing: "primary",
  ready: "success",
  completed: "success",
  cancelled: "danger",
};

const CHANNEL_TITLES: Record<string, string> = {
  site: "Сайт",
  pos: "Касса",
  phone: "Телефон",
};

const FULFILLMENT_TITLES: Record<string, string> = {
  pickup: "Самовывоз",
  delivery: "Доставка",
};

const PAGE_SIZE = 50;
const ACTIVE_STATUSES = "new,confirmed,preparing,ready";
const REFRESH_MS = 20_000;

const api = useApi();
const { user, can, load } = useCurrentUser();
const { units, load: loadUnits } = useMyUnits();

const points = ref<WorkspacePoint[]>([]);
const selectedPointId = ref("");
const tab = ref<"queue" | "history">("queue");
const error = ref("");

const queue = ref<OrderListItem[]>([]);
const pending = ref(false);
const refreshedAt = ref("");
const busyId = ref("");
const newArrived = ref(false);

const historyItems = ref<OrderListItem[]>([]);
const historyTotal = ref(0);
const historyPage = ref(1);
const historyPending = ref(false);
const historyDay = ref<string | null>(todayIso());
const historyStatuses = ref<string[]>([]);
const historySearch = ref("");

const drawerOpen = ref(false);
const detail = ref<OrderDetail | null>(null);
const detailLoading = ref(false);
const detailError = ref("");

const createOpen = ref(false);
const saving = ref(false);
const createError = ref("");
const form = reactive({
  org_unit_id: "",
  channel: "site" as "site" | "pos" | "phone",
  planned_at: null as string | null,
  comment: "",
  lines: [] as OrderLineDraft[],
});

let refreshTimer: ReturnType<typeof setInterval> | undefined;
let noticeTimer: ReturnType<typeof setTimeout> | undefined;
let previousNewCount = 0;

const isCompanyWide = computed(() => (user.value?.scopes?.length ?? 0) === 0);

const selectedPoint = computed(
  () => points.value.find((point) => point.id === selectedPointId.value) ?? null,
);

function pointCan(permission: string): boolean {
  if (isCompanyWide.value) {
    return can(permission);
  }

  return selectedPoint.value?.permissions.includes(permission) ?? false;
}

const canCreate = computed(() => pointCan("order.create"));
const canUpdate = computed(() => pointCan("order.update"));
const canCancel = computed(() => pointCan("order.cancel"));

const queueCounts = computed(() => ({
  new: queue.value.filter((order) => order.status === "new").length,
  inProgress: queue.value.filter((order) =>
    ["confirmed", "preparing"].includes(order.status),
  ).length,
  ready: queue.value.filter((order) => order.status === "ready").length,
}));

const queueColumns = computed(() => [
  {
    code: "new",
    title: "Новые",
    items: sortOrders(queue.value.filter((order) => order.status === "new")),
  },
  {
    code: "in_progress",
    title: "В работе",
    items: sortOrders(
      queue.value.filter((order) =>
        ["confirmed", "preparing"].includes(order.status),
      ),
    ),
  },
  {
    code: "ready",
    title: "Готовы",
    items: sortOrders(queue.value.filter((order) => order.status === "ready")),
  },
]);

function todayIso(): string {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");

  return `${now.getFullYear()}-${month}-${day}`;
}

function sortOrders(items: OrderListItem[]): OrderListItem[] {
  return [...items].sort(
    (left, right) =>
      new Date(left.created_at).getTime() - new Date(right.created_at).getTime(),
  );
}

function formatTime(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }

  return new Date(value).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatQuantity(value: string | number): string {
  const number = Number(value);

  return Number.isFinite(number)
    ? number.toLocaleString("ru-RU", { maximumFractionDigits: 3 })
    : String(value);
}

function waitingMinutes(createdAt: string): number {
  return Math.max(
    0,
    Math.floor((Date.now() - new Date(createdAt).getTime()) / 60_000),
  );
}

function elapsed(createdAt: string): string {
  const minutes = waitingMinutes(createdAt);

  if (minutes < 60) {
    return `${minutes} мин`;
  }

  return `${Math.floor(minutes / 60)} ч ${minutes % 60} мин`;
}

function isActive(status: string): boolean {
  return ["new", "confirmed", "preparing", "ready"].includes(status);
}

function nextAction(
  status: string,
): { action: OrderAction; label: string } | null {
  if (status === "new") {
    return { action: "confirm", label: "Принять" };
  }
  if (status === "confirmed") {
    return { action: "preparing", label: "Готовить" };
  }
  if (status === "preparing") {
    return { action: "ready", label: "Готов" };
  }
  if (status === "ready") {
    return { action: "completed", label: "Выдать" };
  }

  return null;
}

function paymentLabel(order: {
  payment_status: string;
  payment_method: string;
}): string {
  if (order.payment_status === "paid") {
    return "Оплачен";
  }
  if (order.payment_method === "online") {
    return "Ожидает оплаты";
  }

  return "При получении";
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

  points.value = data
    .filter((unit) => ["cafe", "shop", "production"].includes(unit.type))
    .map((unit) => ({
      id: unit.id,
      name: unit.name,
      type: unit.type,
      permissions: [],
    }))
    .sort((left, right) => left.name.localeCompare(right.name));
}

async function loadQueue(silent = false): Promise<void> {
  if (!silent) {
    pending.value = true;
    error.value = "";
    newArrived.value = false;
  }

  try {
    const { data, response } = await api.GET("/api/orders", {
      params: {
        query: {
          statuses: ACTIVE_STATUSES,
          org_unit_id: selectedPoint.value?.id,
          limit: 200,
          offset: 0,
        },
      },
    });

    if (!response.ok || !data) {
      if (!silent) {
        error.value =
          response.status === 403
            ? "Нет доступа к заказам этой точки"
            : "Не удалось загрузить очередь заказов";
      }
      return;
    }

    const newCount = data.items.filter((order) => order.status === "new").length;

    if (silent && newCount > previousNewCount) {
      newArrived.value = true;
      if (noticeTimer) {
        clearTimeout(noticeTimer);
      }
      noticeTimer = setTimeout(() => {
        newArrived.value = false;
      }, 15_000);
    }

    previousNewCount = newCount;
    queue.value = data.items;
    refreshedAt.value = new Date().toLocaleTimeString("ru-RU", {
      hour: "2-digit",
      minute: "2-digit",
    });
  } finally {
    if (!silent) {
      pending.value = false;
    }
  }
}

async function loadHistory(): Promise<void> {
  historyPending.value = true;
  error.value = "";

  try {
    const { data, response } = await api.GET("/api/orders", {
      params: {
        query: {
          day: historyDay.value ?? undefined,
          statuses: historyStatuses.value.length
            ? historyStatuses.value.join(",")
            : undefined,
          search: historySearch.value.trim() || undefined,
          org_unit_id: selectedPoint.value?.id,
          limit: PAGE_SIZE,
          offset: (historyPage.value - 1) * PAGE_SIZE,
        },
      },
    });

    if (!response.ok || !data) {
      error.value =
        response.status === 403
          ? "Нет доступа к заказам этой точки"
          : "Не удалось загрузить историю заказов";
      return;
    }

    historyItems.value = data.items;
    historyTotal.value = data.total;
  } finally {
    historyPending.value = false;
  }
}

async function manualRefresh(): Promise<void> {
  if (tab.value === "queue") {
    await loadQueue();
  } else {
    await loadHistory();
  }
}

async function onPointChange(): Promise<void> {
  previousNewCount = 0;
  newArrived.value = false;

  if (form.org_unit_id && !points.value.some((point) => point.id === form.org_unit_id)) {
    form.org_unit_id = "";
  }

  if (tab.value === "queue") {
    await loadQueue();
  } else {
    await loadHistory();
  }
}

async function onTabChange(name: string | number): Promise<void> {
  if (name === "history") {
    historyPage.value = 1;
    await loadHistory();
    return;
  }

  await loadQueue();
}

async function reloadHistory(): Promise<void> {
  historyPage.value = 1;
  await loadHistory();
}

async function goToHistoryPage(page: number): Promise<void> {
  historyPage.value = page;
  await loadHistory();
}

async function runAction(orderId: string, action: OrderAction): Promise<void> {
  busyId.value = orderId;
  error.value = "";

  try {
    const path = {
      confirm: "/api/orders/{order_id}/confirm",
      preparing: "/api/orders/{order_id}/preparing",
      ready: "/api/orders/{order_id}/ready",
      completed: "/api/orders/{order_id}/completed",
      cancel: "/api/orders/{order_id}/cancel",
    }[action] as "/api/orders/{order_id}/confirm";

    const { response } = await api.POST(path, {
      params: { path: { order_id: orderId } },
    });

    if (!response.ok) {
      const payload = (await response.json().catch(() => null)) as {
        message?: string;
      } | null;
      error.value = payload?.message ?? "Не удалось изменить статус заказа";
      return;
    }

    ElMessage.success("Статус заказа обновлён");

    await loadQueue(true);

    if (drawerOpen.value && detail.value?.id === orderId) {
      await loadDetail(orderId);
    }
  } finally {
    busyId.value = "";
  }
}

async function cancelOrder(order: { id: string; number: number | null }): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `Отменить заказ №${order.number ?? "—"}?`,
      "Отмена заказа",
      {
        confirmButtonText: "Отменить заказ",
        cancelButtonText: "Оставить",
        type: "warning",
      },
    );
  } catch {
    return;
  }

  await runAction(order.id, "cancel");
}

async function openDetail(order: { id: string }): Promise<void> {
  drawerOpen.value = true;
  await loadDetail(order.id);
}

async function loadDetail(orderId: string): Promise<void> {
  detailLoading.value = true;
  detailError.value = "";
  detail.value = null;

  try {
    const { data, response } = await api.GET("/api/orders/{order_id}", {
      params: { path: { order_id: orderId } },
    });

    if (!response.ok || !data) {
      detailError.value =
        response.status === 403
          ? "Нет доступа к этому заказу"
          : "Не удалось загрузить заказ";
      return;
    }

    detail.value = data;
  } finally {
    detailLoading.value = false;
  }
}

function openCreate(): void {
  createError.value = "";

  if (!form.org_unit_id) {
    form.org_unit_id =
      selectedPoint.value?.id ??
      (points.value.length === 1 ? points.value[0]!.id : "");
  }
  if (!form.lines.length) {
    form.lines = [{ nomenclature_id: "", quantity: "1" }];
  }

  createOpen.value = true;
}

async function createOrder(): Promise<void> {
  saving.value = true;
  createError.value = "";

  try {
    const { data, response, error: failure } = await api.POST("/api/orders", {
      body: {
        org_unit_id: form.org_unit_id,
        channel: form.channel,
        planned_at: form.planned_at,
        comment: form.comment.trim() || null,
        lines: form.lines
          .filter((line) => line.nomenclature_id)
          .map((line) => ({
            nomenclature_id: line.nomenclature_id,
            quantity: line.quantity,
          })),
      },
    });

    if (!response.ok || !data) {
      const payload = failure as { message?: string } | undefined;
      createError.value =
        payload?.message ?? `Не удалось создать заказ: ${response.status}`;
      return;
    }

    createOpen.value = false;
    form.planned_at = null;
    form.comment = "";
    form.lines = [];
    form.org_unit_id = "";

    await loadQueue(true);
    await openDetail({ id: data.order_id });
  } finally {
    saving.value = false;
  }
}

onMounted(async () => {
  await load();
  await loadPoints();
  selectedPointId.value = isCompanyWide.value
    ? ""
    : (points.value[0]?.id ?? "");
  await loadQueue();

  refreshTimer = setInterval(() => {
    if (tab.value === "queue") {
      void loadQueue(true);
    }
  }, REFRESH_MS);
});

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer);
  }
  if (noticeTimer) {
    clearTimeout(noticeTimer);
  }
});
</script>

<style scoped>
.orders-head {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.orders-head__controls {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.queue-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-bottom: 14px;
}

.pulse {
  animation: pulse 1.2s ease-in-out infinite;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.55;
  }
}

.board {
  display: grid;
  grid-template-columns: repeat(3, minmax(280px, 1fr));
  gap: 16px;
  align-items: start;
}

.column {
  padding: 12px;
  background: #f6f7f9;
  border: 1px solid #e4e7ed;
  border-radius: 10px;
  min-height: 180px;
}

.column--new {
  background: #fff8e8;
  border-color: #f3d19e;
}

.column--ready {
  background: #f0f9eb;
  border-color: #c2e7b0;
}

.column__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  font-weight: 600;
}

.column__count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  height: 24px;
  padding: 0 7px;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 12px;
  font-size: 12px;
}

.column__empty {
  padding: 24px 0;
  color: #a8abb2;
  text-align: center;
  font-size: 13px;
}

.card {
  padding: 12px;
  margin-bottom: 10px;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  cursor: pointer;
  transition:
    border-color 0.2s,
    box-shadow 0.2s;
}

.card:hover {
  border-color: #c6c9cf;
  box-shadow: 0 2px 10px rgb(0 0 0 / 6%);
}

.card--urgent {
  border-left: 3px solid #f56c6c;
}

.card:last-child {
  margin-bottom: 0;
}

.card__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.card__number {
  font-size: 15px;
}

.card__age {
  color: #909399;
  font-size: 12px;
}

.card__age--urgent {
  color: #f56c6c;
  font-weight: 600;
}

.card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-bottom: 9px;
}

.card__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
}

.card__planned {
  margin-top: 6px;
  color: #606266;
  font-size: 12px;
}

.card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.history-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  margin: 4px 0 14px;
}

.detail-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 14px;
}

.detail-number {
  font-size: 20px;
  font-weight: 600;
}

.detail-info {
  margin-bottom: 14px;
}

.detail-total {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0;
  font-size: 16px;
}

.detail-lines {
  margin-bottom: 14px;
}

.detail-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.muted {
  color: #909399;
}

.pager {
  margin-top: 18px;
  justify-content: flex-end;
}

@media (max-width: 1100px) {
  .board {
    grid-template-columns: 1fr;
  }
}
</style>
