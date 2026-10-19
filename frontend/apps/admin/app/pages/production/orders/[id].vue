<template>
  <div class="page">
    <NuxtLink to="/production/orders" class="back">← Задания</NuxtLink>

    <el-skeleton v-if="pending" :rows="5" animated />

    <template v-else-if="order">
      <h1 class="page__title">
        Задание {{ order.tech_card_code }} v{{ order.tech_card_version }}
        <el-tag :type="STATUS_TYPES[order.status] ?? 'info'" effect="light">
          {{ STATUS_TITLES[order.status] ?? order.status }}
        </el-tag>
      </h1>

      <p class="muted">
        {{ order.location_name ?? "Цех" }}
        · {{ formatTime(order.occurred_at) }}
        · закладок {{ formatQuantity(order.batch_count) }}
        <template v-if="order.posted_at">
          · проведено {{ formatTime(order.posted_at) }}
        </template>
      </p>

      <p v-if="order.comment" class="muted">{{ order.comment }}</p>

      <h3 class="group">Входы</h3>
      <el-table :data="components" border>
        <el-table-column label="Позиция">
          <template #default="{ row }">
            {{ row.nomenclature_name ?? "—" }}
          </template>
        </el-table-column>
        <el-table-column label="Норма" width="140" align="right">
          <template #default="{ row }">{{ formatQuantity(row.planned_quantity) }}</template>
        </el-table-column>
        <el-table-column label="Факт" width="200">
          <template #default="{ row }">
            <el-input-number
              v-if="editable"
              :model-value="actuals[row.id]"
              :min="0"
              :step="1"
              :precision="3"
              size="small"
              style="width: 100%"
              @update:model-value="setActual(row.id, $event)"
            />
            <span v-else>{{ formatQuantity(row.actual_quantity) }}</span>
          </template>
        </el-table-column>
      </el-table>

      <h3 class="group">Выходы</h3>
      <el-table :data="outputs" border>
        <el-table-column label="Позиция">
          <template #default="{ row }">
            {{ row.nomenclature_name ?? "—" }}
            <el-tag
              v-if="row.output_kind === 'by_product'"
              size="small"
              type="info"
              effect="plain"
            >
              попутный
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Норма" width="140" align="right">
          <template #default="{ row }">{{ formatQuantity(row.planned_quantity) }}</template>
        </el-table-column>
        <el-table-column label="Факт" width="200">
          <template #default="{ row }">
            <el-input-number
              v-if="editable"
              :model-value="actuals[row.id]"
              :min="0"
              :step="1"
              :precision="3"
              size="small"
              style="width: 100%"
              @update:model-value="setActual(row.id, $event)"
            />
            <span v-else>{{ formatQuantity(row.actual_quantity) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="Себестоимость" width="170" align="right">
          <template #default="{ row }">
            {{ row.cost === null ? "—" : formatKopecks(row.cost) }}
          </template>
        </el-table-column>
      </el-table>

      <h3 class="group">Потери</h3>
      <p v-if="!losses.length" class="muted">
        Потери посчитаются при проведении как разница «вход минус выход».
      </p>
      <el-table v-else :data="losses" border>
        <el-table-column label="Вид">
          <template #default="{ row }">
            {{ LOSS_TITLES[row.loss_kind] ?? "Не классифицировано" }}
          </template>
        </el-table-column>
        <el-table-column label="Норма" width="140" align="right">
          <template #default="{ row }">{{ formatQuantity(row.planned_quantity) }}</template>
        </el-table-column>
        <el-table-column label="Факт" width="140" align="right">
          <template #default="{ row }">{{ formatQuantity(row.actual_quantity) }}</template>
        </el-table-column>
      </el-table>

      <el-alert
        v-if="error"
        :title="error"
        type="error"
        :closable="false"
        show-icon
        class="alert"
      />

      <div class="actions">
        <el-button
          v-if="editable && can('production.order.manage')"
          :loading="saving"
          @click="saveActuals"
        >
          Сохранить факт
        </el-button>
        <el-button
          v-if="editable && can('production.order.post')"
          type="primary"
          :loading="posting"
          @click="askPostOrder"
        >
          Провести
        </el-button>
        <el-button
          v-if="editable && can('production.order.manage')"
          type="danger"
          plain
          :loading="cancelling"
          @click="cancelOrder"
        >
          Отменить
        </el-button>
      </div>
    </template>

    <el-empty v-else description="Задание не найдено" />
  </div>
</template>

<script setup lang="ts">
import type { components } from "@md/api-client";
import { formatKopecks } from "@md/money";

import { CAN } from "~/utils/access";

definePageMeta({ permissions: CAN.productionOrdersOpen });

type ProductionOrderDetail =
  components["schemas"]["ProductionOrderDetailSchema"];
type ProductionOrderLine =
  components["schemas"]["ProductionOrderLineSchema"];

const STATUS_TITLES: Record<string, string> = {
  draft: "Черновик",
  posted: "Проведено",
  cancelled: "Отменено",
};

const STATUS_TYPES: Record<string, "success" | "warning" | "info" | "danger"> = {
  draft: "info",
  posted: "success",
  cancelled: "danger",
};

const LOSS_TITLES: Record<string, string> = {
  shrinkage: "Усушка",
  cooking: "Ужарка и уварка",
  trimming: "Зачистка, жиловка",
  defrost: "Дефростация",
  defect: "Брак",
};

const api = useApi();
const route = useRoute();
const { can } = useCurrentUser();
const { confirm } = useConfirm();

const orderId = String(route.params.id);
const order = ref<ProductionOrderDetail | null>(null);
const pending = ref(false);
const saving = ref(false);
const posting = ref(false);
const cancelling = ref(false);
const error = ref("");
const actuals = reactive<Record<string, number>>({});

const editable = computed(() => order.value?.status === "draft");
const components = computed(() => byRole("component"));
const outputs = computed(() => byRole("output"));
const losses = computed(() => byRole("loss"));

function byRole(role: string): ProductionOrderLine[] {
  return order.value?.lines.filter((line) => line.role === role) ?? [];
}

function formatQuantity(value: string): string {
  const numeric = Number(value);

  return Number.isNaN(numeric)
    ? value
    : numeric.toLocaleString("ru-RU", { maximumFractionDigits: 3 });
}

function formatTime(value: string): string {
  return new Date(value).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function setActual(lineId: string, value: number | undefined): void {
  actuals[lineId] = Number(value ?? 0);
}

function fillActuals(): void {
  for (const line of order.value?.lines ?? []) {
    actuals[line.id] = Number(line.actual_quantity);
  }
}

function messageOf(failure: unknown, fallback: string): string {
  const payload = failure as { message?: string } | undefined;

  return payload?.message ?? fallback;
}

async function load(): Promise<void> {
  pending.value = true;
  error.value = "";

  try {
    const { data, response } = await api.GET(
      "/api/production/orders/{order_id}",
      { params: { path: { order_id: orderId } } },
    );

    order.value = response.ok && data ? data : null;
    fillActuals();
  } finally {
    pending.value = false;
  }
}

async function saveActuals(): Promise<void> {
  error.value = "";
  saving.value = true;

  try {
    const editableLines = [...components.value, ...outputs.value];
    const { response, error: failure } = await api.PATCH(
      "/api/production/orders/{order_id}",
      {
        params: { path: { order_id: orderId } },
        body: {
          actuals: editableLines.map((line) => ({
            line_id: line.id,
            quantity: String(actuals[line.id] ?? 0),
          })),
        },
      },
    );

    if (!response.ok) {
      error.value = messageOf(failure, `Не удалось сохранить факт: ${response.status}`);
      return;
    }

    await load();
  } finally {
    saving.value = false;
  }
}

async function askPostOrder(): Promise<void> {
  if (await confirm({ title: "Провести задание?" })) {
    await postOrder();
  }
}

async function postOrder(): Promise<void> {
  error.value = "";
  posting.value = true;

  try {
    const { response, error: failure } = await api.POST(
      "/api/production/orders/{order_id}/post",
      { params: { path: { order_id: orderId } } },
    );

    if (!response.ok) {
      error.value = messageOf(failure, `Не удалось провести: ${response.status}`);
      await load();
      return;
    }

    await load();
  } finally {
    posting.value = false;
  }
}

async function cancelOrder(): Promise<void> {
  error.value = "";
  cancelling.value = true;

  try {
    const { response, error: failure } = await api.POST(
      "/api/production/orders/{order_id}/cancel",
      { params: { path: { order_id: orderId } } },
    );

    if (!response.ok) {
      error.value = messageOf(failure, `Не удалось отменить: ${response.status}`);
      return;
    }

    await load();
  } finally {
    cancelling.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
.back {
  display: inline-block;
  margin-bottom: 12px;
  color: #909399;
  text-decoration: none;
}

.group {
  margin: 24px 0 12px;
  font-size: 16px;
}

.alert {
  margin-top: 20px;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  margin-top: 24px;
}
</style>
