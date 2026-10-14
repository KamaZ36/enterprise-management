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
  </div>
</template>

<script setup lang="ts">
import type { components } from "@md/api-client";
import { formatKopecks } from "@md/money";

import { CAN } from "~/utils/access";

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

const items = ref<OrderListItem[]>([]);
const total = ref(0);
const page = ref(1);
const statuses = ref<string[]>([...ACTIVE_STATUSES]);
const { scopeId, load: loadScope } = useCurrentScope();
const pending = ref(false);
const error = ref("");

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
          org_unit_id: scopeId.value ?? undefined,
          statuses: statuses.value.length ? statuses.value.join(",") : undefined,
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

watch(scopeId, () => {
  void reload();
});

onMounted(async () => {
  await loadScope();
  await loadOrders();
});
</script>
