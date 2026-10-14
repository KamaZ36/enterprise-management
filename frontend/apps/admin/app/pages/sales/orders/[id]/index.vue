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
        :loading="acting"
        @click="openEdit"
      >
        Изменить
      </el-button>

      <el-button
        v-if="order.status === 'draft' && can('order.update')"
        type="primary"
        :loading="acting"
        @click="confirmOrder"
      >
        Подтвердить
      </el-button>

      <el-button
        v-if="order.status === 'confirmed' && can('order.update')"
        type="primary"
        :loading="acting"
        @click="startPreparing"
      >
        Готовится
      </el-button>

      <el-button
        v-if="order.status === 'preparing' && can('order.update')"
        type="success"
        :loading="acting"
        @click="markReady"
      >
        Готов
      </el-button>

      <el-button
        v-if="order.status === 'ready' && can('order.update')"
        type="success"
        :loading="acting"
        @click="completeOrder"
      >
        Выдан
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

    <el-dialog v-model="editOpen" title="Изменить черновик" width="720">
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="Позиции">
          <OrderLinesEditor
            v-model="editLines"
            :org-unit-id="order?.org_unit_id"
            :extra-options="knownLineOptions"
          />
        </el-form-item>

        <el-form-item label="К выдаче">
          <el-date-picker
            v-model="editPlannedAt"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ssZ"
            placeholder="Как можно скорее"
            style="width: 100%"
          />
        </el-form-item>

        <el-form-item label="Комментарий">
          <el-input v-model="editComment" type="textarea" :rows="2" />
        </el-form-item>

        <el-alert
          v-if="editError"
          :title="editError"
          type="error"
          :closable="false"
          show-icon
        />
      </el-form>

      <template #footer>
        <el-button @click="editOpen = false">Отмена</el-button>
        <el-button type="primary" :loading="saving" @click="saveEdit">
          Сохранить
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

const ACTION_PATHS = {
  confirm: "/api/sales/orders/{order_id}/confirm",
  preparing: "/api/sales/orders/{order_id}/preparing",
  ready: "/api/sales/orders/{order_id}/ready",
  completed: "/api/sales/orders/{order_id}/completed",
  cancel: "/api/sales/orders/{order_id}/cancel",
} as const;

type OrderAction = keyof typeof ACTION_PATHS;

async function act(action: OrderAction): Promise<void> {
  acting.value = true;
  error.value = "";

  try {
    const { response } = await api.POST(ACTION_PATHS[action], {
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

async function startPreparing(): Promise<void> {
  await act("preparing");
}

async function markReady(): Promise<void> {
  await act("ready");
}

async function cancelOrder(): Promise<void> {
  await act("cancel");
}

async function completeOrder(): Promise<void> {
  await act("completed");
}

const editOpen = ref(false);
const editError = ref("");
const saving = ref(false);
const editLines = ref<OrderLineDraft[]>([]);
const editPlannedAt = ref<string | null>(null);
const editComment = ref("");

const knownLineOptions = computed(() =>
  (order.value?.lines ?? []).map((line) => ({
    id: line.nomenclature_id,
    name: line.nomenclature_name ?? line.nomenclature_id,
  })),
);

function openEdit(): void {
  const current = order.value;
  if (!current) return;

  editError.value = "";
  editLines.value = current.lines.map((line) => ({
    nomenclature_id: line.nomenclature_id,
    quantity: String(line.quantity),
  }));
  editPlannedAt.value = current.planned_at ?? null;
  editComment.value = current.comment ?? "";
  editOpen.value = true;
}

async function saveEdit(): Promise<void> {
  const current = order.value;
  if (!current) return;

  saving.value = true;
  editError.value = "";

  try {
    const { response, error: failure } = await api.PATCH(
      "/api/sales/orders/{order_id}",
      {
        params: { path: { order_id: orderId } },
        body: {
          planned_at: editPlannedAt.value || null,
          comment: editComment.value.trim() || null,
          lines: editLines.value
            .filter((line) => line.nomenclature_id)
            .map((line) => ({
              nomenclature_id: line.nomenclature_id,
              quantity: line.quantity,
            })),
        },
      },
    );

    if (!response.ok) {
      const payload = failure as { message?: string } | undefined;
      editError.value =
        payload?.message ??
        (response.status === 409
          ? "Менять можно только черновик заказа"
          : `Не удалось сохранить: ${response.status}`);
      return;
    }

    editOpen.value = false;
    await loadOrder();
  } finally {
    saving.value = false;
  }
}

onMounted(loadOrder);
</script>
