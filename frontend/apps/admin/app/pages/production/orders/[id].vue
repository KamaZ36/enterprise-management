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
        <el-table-column label="Партия" width="240">
          <template #default="{ row }">
            <el-select
              v-if="editable"
              :model-value="selectedLots[row.id]"
              clearable
              filterable
              size="small"
              placeholder="Не указана"
              style="width: 100%"
              @update:model-value="setLot(row.id, $event)"
            >
              <el-option
                v-for="lot in row.available_lots ?? []"
                :key="lot.id"
                :label="lotLabel(lot)"
                :value="lot.id"
              />
            </el-select>
            <span v-else>{{ row.lot_code ?? "—" }}</span>
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
        <el-table-column label="Годен до" width="180">
          <template #default="{ row }">
            <el-date-picker
              v-if="editable"
              :model-value="expiries[row.id]"
              type="date"
              value-format="YYYY-MM-DD"
              size="small"
              placeholder="Не указан"
              style="width: 100%"
              @update:model-value="setExpiry(row.id, $event)"
            />
            <span v-else>{{ row.expires_at ? formatDate(row.expires_at) : "—" }}</span>
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

      <h3 class="group">ВетИС</h3>
      <el-form label-position="top">
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="Статус">
              <el-select v-model="vetis.status" style="width: 100%">
                <el-option label="Не указано" value="not_specified" />
                <el-option
                  label="ВСД нет (домашний производитель)"
                  value="no_vsd"
                />
                <el-option label="Введено вручную" value="manual" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col v-if="vetis.status === 'manual'" :span="16">
            <el-form-item label="Идентификатор производственной операции">
              <el-input
                v-model="vetis.operation_id"
                placeholder="GUID операции в Меркурии"
              />
            </el-form-item>
          </el-col>
          <el-col v-if="vetis.status === 'no_vsd'" :span="16">
            <el-form-item label="Причина отсутствия ВСД">
              <el-input
                v-model="vetis.no_vsd_reason"
                placeholder="например, домашний производитель"
              />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <el-table
        v-if="vetis.status === 'manual' && outputs.length"
        :data="outputs"
        border
        size="small"
      >
        <el-table-column label="Выход">
          <template #default="{ row }">
            {{ row.nomenclature_name ?? "—" }}
          </template>
        </el-table-column>
        <el-table-column label="Номер производственного ВСД">
          <template #default="{ row }">
            <el-input
              v-model="outputVetisLine(row.id).vsd_number"
              placeholder="ВСД-..."
            />
          </template>
        </el-table-column>
        <el-table-column label="GUID производственного ВСД">
          <template #default="{ row }">
            <el-input
              v-model="outputVetisLine(row.id).vsd_guid"
              placeholder="GUID"
            />
          </template>
        </el-table-column>
        <el-table-column label="Номер партии (batchID)">
          <template #default="{ row }">
            <el-input
              v-model="outputVetisLine(row.id).batch_id"
              placeholder="BATCH-..."
            />
          </template>
        </el-table-column>
      </el-table>

      <div class="actions">
        <el-button
          v-if="can('production.order.manage')"
          :loading="savingVetis"
          @click="saveVetis"
        >
          Сохранить ВетИС
        </el-button>
        <el-tag v-if="order.vetis_entered_at" type="info" effect="plain">
          введено {{ formatTime(order.vetis_entered_at) }}
        </el-tag>
      </div>

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
type ProductionOrderLot =
  components["schemas"]["ProductionOrderLotSchema"];
type ProductionVetisStatus = components["schemas"]["VetisStatus"];

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
const selectedLots = reactive<Record<string, string | null>>({});
const expiries = reactive<Record<string, string | null>>({});
const savingVetis = ref(false);
const vetis = reactive({
  status: "not_specified" as ProductionVetisStatus,
  operation_id: "",
  no_vsd_reason: "",
});
const outputVetis = reactive<
  Record<string, { vsd_number: string; vsd_guid: string; batch_id: string }>
>({});

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

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function lotLabel(lot: ProductionOrderLot): string {
  const expiry = lot.expires_at ? ` · до ${formatDate(lot.expires_at)}` : "";

  return `${lot.code} · ${formatQuantity(lot.quantity)}${expiry}`;
}

function setLot(lineId: string, value: string | null | undefined): void {
  selectedLots[lineId] = value || null;
}

function setExpiry(lineId: string, value: string | null | undefined): void {
  expiries[lineId] = value || null;
}

function setActual(lineId: string, value: number | undefined): void {
  actuals[lineId] = Number(value ?? 0);
}

function fillActuals(): void {
  for (const line of order.value?.lines ?? []) {
    actuals[line.id] = Number(line.actual_quantity);
    selectedLots[line.id] = line.lot_id ?? null;
    expiries[line.id] = line.expires_at ?? null;
  }
}

function outputVetisLine(lineId: string): {
  vsd_number: string;
  vsd_guid: string;
  batch_id: string;
} {
  let line = outputVetis[lineId];

  if (!line) {
    line = { vsd_number: "", vsd_guid: "", batch_id: "" };
    outputVetis[lineId] = line;
  }

  return line;
}

function fillVetis(): void {
  vetis.status = order.value?.vetis_status ?? "not_specified";
  vetis.operation_id = order.value?.vetis_operation_id ?? "";
  vetis.no_vsd_reason = order.value?.vetis_no_vsd_reason ?? "";

  for (const line of order.value?.lines ?? []) {
    outputVetis[line.id] = {
      vsd_number: line.vetis_production_vsd_number ?? "",
      vsd_guid: line.vetis_production_vsd_guid ?? "",
      batch_id: line.vetis_batch_id ?? "",
    };
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
    fillVetis();
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
            lot_id: line.role === "component" ? selectedLots[line.id] ?? null : null,
            expires_at: line.role === "output" ? expiries[line.id] ?? null : null,
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

async function saveVetis(): Promise<void> {
  error.value = "";
  savingVetis.value = true;

  try {
    const { response, error: failure } = await api.PATCH(
      "/api/production/orders/{order_id}/vetis",
      {
        params: { path: { order_id: orderId } },
        body: {
          status: vetis.status,
          operation_id: vetis.operation_id.trim() || null,
          no_vsd_reason: vetis.no_vsd_reason.trim() || null,
          outputs: outputs.value.map((line) => ({
            line_id: line.id,
            production_vsd_number:
              outputVetis[line.id]?.vsd_number.trim() || null,
            production_vsd_guid: outputVetis[line.id]?.vsd_guid.trim() || null,
            batch_id: outputVetis[line.id]?.batch_id.trim() || null,
          })),
        },
      },
    );

    if (!response.ok) {
      error.value = messageOf(
        failure,
        `Не удалось сохранить ВетИС: ${response.status}`,
      );
      return;
    }

    await load();
  } finally {
    savingVetis.value = false;
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
