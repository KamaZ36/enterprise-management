<template>
  <div class="page">
    <el-button text @click="router.push('/customers')">← К списку клиентов</el-button>

    <h1 class="page__title">{{ customer?.first_name ?? "Клиент" }}</h1>

    <el-alert
      v-if="error"
      :title="error"
      type="error"
      :closable="false"
      show-icon
      class="page__error"
    />

    <el-descriptions v-if="customer" :column="2" border style="margin-top: 16px">
      <el-descriptions-item label="Телефон">
        {{ customer.contact_phone ?? "не указан" }}
      </el-descriptions-item>
      <el-descriptions-item label="Статус">
        <el-tag
          :type="customer.status === 'active' ? 'success' : 'danger'"
          effect="light"
        >
          {{ customer.status === "active" ? "Активен" : "Заблокирован" }}
        </el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="Зарегистрирован">
        {{ formatTime(customer.created_at) }}
      </el-descriptions-item>
      <el-descriptions-item label="Заказов">
        {{ ordersTotal }}
      </el-descriptions-item>
    </el-descriptions>

    <template v-if="can('order.read')">
      <h2 style="margin: 28px 0 12px">История заказов</h2>

      <el-table v-if="orders.length" v-loading="ordersPending" :data="orders" stripe border>
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
          <template #default="{ row }">
            {{ CHANNEL_TITLES[row.channel] ?? row.channel }}
          </template>
        </el-table-column>
        <el-table-column label="Итог" width="140" align="right">
          <template #default="{ row }">{{ formatKopecks(row.total) }}</template>
        </el-table-column>
      </el-table>

      <el-empty v-else-if="!ordersPending" description="Заказов нет" />
    </template>

    <p v-else style="color: #909399; margin-top: 24px">
      История заказов недоступна: нет права на просмотр заказов.
    </p>
  </div>
</template>

<script setup lang="ts">
import type { components } from "@md/api-client";
import { formatKopecks } from "@md/money";

import { CAN } from "~/utils/access";

definePageMeta({ permissions: CAN.customersOpen });

type CustomerDetail = components["schemas"]["CustomerDetailSchema"];
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

const api = useApi();
const route = useRoute();
const router = useRouter();
const { can } = useCurrentUser();

const customerId = String(route.params.id);
const customer = ref<CustomerDetail | null>(null);
const orders = ref<OrderListItem[]>([]);
const ordersTotal = ref(0);
const ordersPending = ref(false);
const error = ref("");

function formatTime(value: string): string {
  return new Date(value).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

async function loadCustomer(): Promise<void> {
  const { data, response } = await api.GET("/api/customers/{customer_id}", {
    params: { path: { customer_id: customerId } },
  });

  if (!response.ok || !data) {
    error.value =
      response.status === 404
        ? "Клиент не найден"
        : "Не удалось загрузить профиль клиента";
    return;
  }

  customer.value = data;
}

async function loadOrders(): Promise<void> {
  if (!can("order.read")) {
    return;
  }

  ordersPending.value = true;

  try {
    const { data } = await api.GET("/api/sales/orders", {
      params: {
        query: { customer_id: customerId, limit: 20, offset: 0 },
      },
    });

    orders.value = data?.items ?? [];
    ordersTotal.value = data?.total ?? 0;
  } finally {
    ordersPending.value = false;
  }
}

onMounted(async () => {
  await loadCustomer();
  await loadOrders();
});
</script>
