<template>
  <div class="page">
    <el-button text @click="router.push('/sales/orders')">← К списку заказов</el-button>

    <h1 class="page__title">
      Заказ {{ order?.number ?? "—" }}
      <el-tag
        v-if="order"
        :type="STATUS_TYPES[order.status] ?? 'info'"
        effect="light"
        style="margin-left: 12px"
      >
        {{ STATUS_TITLES[order.status] ?? order.status }}
      </el-tag>
    </h1>

    <el-alert
      v-if="error"
      :title="error"
      type="error"
      :closable="false"
      show-icon
      class="page__error"
    />

    <el-descriptions v-if="order" :column="2" border style="margin-top: 16px">
      <el-descriptions-item label="Создан">
        {{ formatTime(order.created_at) }}
      </el-descriptions-item>
      <el-descriptions-item label="Канал">
        {{ CHANNEL_TITLES[order.channel] ?? order.channel }}
      </el-descriptions-item>
      <el-descriptions-item label="К выдаче">
        {{ order.planned_at ? formatTime(order.planned_at) : "как можно скорее" }}
      </el-descriptions-item>
      <el-descriptions-item label="Телефон">
        {{ order.contact_phone ?? "не указан" }}
      </el-descriptions-item>
      <el-descriptions-item v-if="order.comment" label="Комментарий" :span="2">
        {{ order.comment }}
      </el-descriptions-item>
    </el-descriptions>

    <el-table v-if="order?.lines?.length" :data="order.lines" stripe border style="margin-top: 16px">
      <el-table-column label="Позиция" min-width="240">
        <template #default="{ row }">
          {{ row.nomenclature_name ?? row.nomenclature_id }}
        </template>
      </el-table-column>
      <el-table-column label="Количество" width="140" align="right">
        <template #default="{ row }">{{ Number(row.quantity) }}</template>
      </el-table-column>
      <el-table-column label="Цена" width="140" align="right">
        <template #default="{ row }">{{ formatKopecks(row.unit_price) }}</template>
      </el-table-column>
      <el-table-column label="Сумма" width="140" align="right">
        <template #default="{ row }">{{ formatKopecks(row.total) }}</template>
      </el-table-column>
    </el-table>

    <div v-if="order" style="margin-top: 16px; font-size: 18px">
      Итого: <strong>{{ formatKopecks(order.total) }}</strong>
    </div>

    <div v-if="order" style="display: flex; gap: 12px; margin-top: 24px">
      <el-button
        v-if="order.status === 'draft' && can('order.update')"
        type="primary"
        :loading="acting"
        @click="confirmOrder"
      >
        Подтвердить
      </el-button>

      <el-button
        v-if="isOpen && can('order.cancel')"
        type="danger"
        plain
        :loading="acting"
        @click="cancelOrder"
      >
        Отменить
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { components } from "@md/api-client";
import { formatKopecks } from "@md/money";

import { CAN } from "~/utils/access";

definePageMeta({ permissions: CAN.ordersOpen });

type OrderDetail = components["schemas"]["OrderDetailSchema"];

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

const OPEN_STATUSES = ["draft", "confirmed", "preparing", "ready"];

const api = useApi();
const route = useRoute();
const router = useRouter();
const { can } = useCurrentUser();

const orderId = String(route.params.id);
const order = ref<OrderDetail | null>(null);
const pending = ref(false);
const acting = ref(false);
const error = ref("");

const isOpen = computed(
  () => order.value !== null && OPEN_STATUSES.includes(order.value.status),
);

function formatTime(value: string): string {
  return new Date(value).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

async function loadOrder(): Promise<void> {
  error.value = "";
  pending.value = true;

  try {
    const { data, response } = await api.GET("/api/sales/orders/{order_id}", {
      params: { path: { order_id: orderId } },
    });

    if (!response.ok || !data) {
      error.value =
        response.status === 404
          ? "Заказ не найден"
          : response.status === 403
            ? "Нет доступа к этому заказу"
            : "Не удалось загрузить заказ";
      return;
    }

    order.value = data;
  } finally {
    pending.value = false;
  }
}

async function act(action: "confirm" | "cancel"): Promise<void> {
  acting.value = true;
  error.value = "";

  try {
    const path =
      action === "confirm"
        ? "/api/sales/orders/{order_id}/confirm"
        : "/api/sales/orders/{order_id}/cancel";

    const { response } = await api.POST(path, {
      params: { path: { order_id: orderId } },
    });

    if (!response.ok) {
      error.value =
        response.status === 409
          ? "Так уже нельзя: заказ в другом статусе"
          : "Не удалось изменить заказ";
      await loadOrder();
      return;
    }

    await loadOrder();
  } finally {
    acting.value = false;
  }
}

async function confirmOrder(): Promise<void> {
  await act("confirm");
}

async function cancelOrder(): Promise<void> {
  await act("cancel");
}

onMounted(loadOrder);
</script>
