<template>
  <div class="page">
    <h1 class="page__title">Заказы</h1>

    <el-alert
      v-if="error"
      :title="error"
      type="error"
      :closable="false"
      show-icon
      class="page__error"
    />

    <div style="display: flex; flex-wrap: wrap; gap: 12px; align-items: center; margin: 16px 0">
      <el-select
        v-if="orgUnitOptions.length > 1"
        v-model="unitFilter"
        clearable
        placeholder="Все точки"
        style="width: 240px"
        @change="reload"
      >
        <el-option
          v-for="unit in orgUnitOptions"
          :key="unit.id"
          :label="unit.name"
          :value="unit.id"
        />
      </el-select>
      <el-select
        v-model="statuses"
        multiple
        collapse-tags
        placeholder="Статусы"
        style="width: 300px"
        @change="reload"
      >
        <el-option
          v-for="(title, code) in STATUS_TITLES"
          :key="code"
          :label="title"
          :value="code"
        />
      </el-select>

      <el-button v-if="can('order.create')" type="primary" @click="openCreate">
        Новый заказ
      </el-button>
      <el-button :loading="pending" @click="reload">Обновить</el-button>
      <span style="color: #909399">Заказов: {{ total }}</span>
    </div>

    <el-table
      v-if="items.length"
      v-loading="pending"
      :data="items"
      stripe
      border
      @row-click="openOrder"
    >
      <el-table-column label="Номер" width="90">
        <template #default="{ row }">{{ row.number ?? "—" }}</template>
      </el-table-column>
      <el-table-column label="Создан" width="170">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="Статус" width="150">
        <template #default="{ row }">
          <el-tag :type="STATUS_TYPES[row.status] ?? 'info'" effect="light">
            {{ STATUS_TITLES[row.status] ?? row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="Канал" width="120">
        <template #default="{ row }">{{ CHANNEL_TITLES[row.channel] ?? row.channel }}</template>
      </el-table-column>
      <el-table-column label="Позиций" width="100" align="right">
        <template #default="{ row }">{{ row.line_count }}</template>
      </el-table-column>
      <el-table-column label="Итог" width="140" align="right">
        <template #default="{ row }">{{ formatKopecks(row.total) }}</template>
      </el-table-column>
    </el-table>

    <el-empty v-else-if="!pending" description="Заказов пока нет" />

    <el-pagination
      v-if="total > PAGE_SIZE"
      :current-page="page"
      :page-size="PAGE_SIZE"
      :total="total"
      :disabled="pending"
      class="pager"
      layout="prev, pager, next, total"
      @current-change="goToPage"
    />

    <el-dialog v-model="createOpen" title="Новый заказ" width="720">
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="Точка">
          <el-select
            v-model="form.org_unit_id"
            placeholder="Подразделение"
            style="width: 100%"
          >
            <el-option
              v-for="unit in orgUnitOptions"
              :key="unit.id"
              :label="unit.name"
              :value="unit.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="Канал">
          <el-select v-model="form.channel" style="width: 100%">
            <el-option
              v-for="(title, code) in CHANNEL_TITLES"
              :key="code"
              :label="title"
              :value="code"
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

import { CAN } from "~/utils/access";
import type { OrderLineDraft } from "~/utils/orderLines";

definePageMeta({ permissions: CAN.ordersOpen });

type OrderListItem = components["schemas"]["OrderListItemSchema"];

const STATUS_TITLES: Record<string, string> = {
  draft: "Черновик",
  confirmed: "Подтверждён",
  preparing: "Готовится",
  ready: "Готов",
  completed: "Выдан",
  cancelled: "Отменён",
};

const STATUS_TYPES: Record<string, "success" | "warning" | "info" | "danger"> = {
  draft: "info",
  confirmed: "warning",
  preparing: "warning",
  ready: "success",
  completed: "success",
  cancelled: "danger",
};

const CHANNEL_TITLES: Record<string, string> = {
  site: "Сайт",
  pos: "Касса",
  phone: "Телефон",
};

const PAGE_SIZE = 50;
const ACTIVE_STATUSES = ["draft", "confirmed", "preparing", "ready"];

const api = useApi();
const { can } = useCurrentUser();

const items = ref<OrderListItem[]>([]);
const total = ref(0);
const page = ref(1);
const statuses = ref<string[]>([...ACTIVE_STATUSES]);
const unitFilter = ref<string | null>(null);
const { units, load: loadUnits } = useMyUnits();
const pending = ref(false);
const error = ref("");

const createOpen = ref(false);
const saving = ref(false);
const createError = ref("");
const orgUnitOptions = ref<{ id: string; name: string }[]>([]);
const form = reactive({
  org_unit_id: "",
  channel: "pos" as "site" | "pos" | "phone",
  planned_at: null as string | null,
  comment: "",
  lines: [] as OrderLineDraft[],
});

function formatTime(value: string): string {
  const date = new Date(value);

  return date.toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

async function loadOrders(): Promise<void> {
  error.value = "";
  pending.value = true;

  try {
    const { data, response } = await api.GET("/api/sales/orders", {
      params: {
        query: {
          statuses: statuses.value.length ? statuses.value.join(",") : undefined,
          org_unit_id: unitFilter.value ?? undefined,
          limit: PAGE_SIZE,
          offset: (page.value - 1) * PAGE_SIZE,
        },
      },
    });

    if (!response.ok || !data) {
      error.value =
        response.status === 403
          ? "Нет доступа к заказам этой точки"
          : "Не удалось загрузить заказы";
      items.value = [];
      total.value = 0;
      return;
    }

    items.value = data.items;
    total.value = data.total;
  } finally {
    pending.value = false;
  }
}

async function reload(): Promise<void> {
  page.value = 1;
  await loadOrders();
}

async function goToPage(target: number): Promise<void> {
  page.value = target;
  await loadOrders();
}

async function openOrder(row: OrderListItem): Promise<void> {
  await navigateTo(`/sales/orders/${row.id}`);
}

async function loadOrgUnits(): Promise<void> {
  const options = new Map<string, string>();

  for (const unit of units.value) {
    options.set(unit.id, unit.title);
  }

  if (can("org_unit.read")) {
    const { data, response } = await api.GET("/api/business/org-units", {});
    if (response.ok && data) {
      for (const unit of data) {
        if (!options.has(unit.id)) {
          options.set(unit.id, unit.name);
        }
      }
    }
  }

  orgUnitOptions.value = [...options].map(([id, name]) => ({ id, name }));

  if (!form.org_unit_id) {
    form.org_unit_id =
      orgUnitOptions.value.length === 1 ? orgUnitOptions.value[0]!.id : "";
  }
}

function openCreate(): void {
  createError.value = "";

  if (!form.org_unit_id) {
    form.org_unit_id =
      orgUnitOptions.value.length === 1 ? orgUnitOptions.value[0]!.id : "";
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
    const { data, response, error: failure } = await api.POST(
      "/api/sales/orders",
      {
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
      },
    );

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

    await navigateTo(`/sales/orders/${data.order_id}`);
  } finally {
    saving.value = false;
  }
}

onMounted(async () => {
  await loadUnits();
  await loadOrgUnits();
  await loadOrders();
});
</script>
