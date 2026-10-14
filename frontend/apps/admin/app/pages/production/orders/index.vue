<template>
  <div class="page">
    <h1 class="page__title">Производственные задания</h1>

    <el-alert
      v-if="error"
      :title="error"
      type="error"
      :closable="false"
      show-icon
      class="page__error"
    />

    <div class="toolbar">
      <el-select
        v-model="warehouseId"
        clearable
        placeholder="Цех"
        style="width: 220px"
        @change="reload"
      >
        <el-option
          v-for="warehouse in warehouses"
          :key="warehouse.id"
          :label="warehouse.name"
          :value="warehouse.id"
        />
      </el-select>

      <el-select
        v-model="statuses"
        multiple
        collapse-tags
        placeholder="Статусы"
        style="width: 260px"
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
      <el-button
        v-if="can('production.order.manage')"
        type="primary"
        @click="openCreate"
      >
        Новое задание
      </el-button>
      <span class="muted">Всего: {{ total }}</span>
    </div>

    <el-table
      v-if="items.length"
      v-loading="pending"
      :data="items"
      stripe
      border
      @row-click="openOrder"
    >
      <el-table-column label="Дата" width="130">
        <template #default="{ row }">{{ formatDay(row.occurred_at) }}</template>
      </el-table-column>
      <el-table-column label="Цех">
        <template #default="{ row }">{{ row.warehouse_name ?? "—" }}</template>
      </el-table-column>
      <el-table-column label="Техкарта" width="240">
        <template #default="{ row }">
          {{ row.tech_card_code }} v{{ row.tech_card_version }}
        </template>
      </el-table-column>
      <el-table-column label="Закладок" width="120" align="right">
        <template #default="{ row }">{{ formatQuantity(row.batch_count) }}</template>
      </el-table-column>
      <el-table-column label="Статус" width="150">
        <template #default="{ row }">
          <el-tag :type="STATUS_TYPES[row.status] ?? 'info'" effect="light">
            {{ STATUS_TITLES[row.status] ?? row.status }}
          </el-tag>
        </template>
      </el-table-column>
    </el-table>

    <el-empty
      v-else-if="!pending"
      description="Заданий пока нет — создайте первое"
    />

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

    <el-dialog v-model="createOpen" title="Новое задание" width="640">
      <el-form label-position="top">
        <el-form-item label="Цех">
          <el-select v-model="form.warehouse_id" style="width: 100%">
            <el-option
              v-for="warehouse in warehouses"
              :key="warehouse.id"
              :label="warehouse.name"
              :value="warehouse.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="Техкарта">
          <el-select v-model="form.tech_card_id" filterable style="width: 100%">
            <el-option
              v-for="card in techCards"
              :key="card.id"
              :label="`${card.code} v${card.version} — ${card.name}`"
              :value="card.id"
            />
          </el-select>
        </el-form-item>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="Закладок">
              <el-input-number
                v-model="form.batch_count"
                :min="0.001"
                :step="1"
                :precision="3"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="Дата">
              <el-date-picker
                v-model="form.occurred_at"
                type="datetime"
                value-format="YYYY-MM-DDTHH:mm:ssZ"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="Комментарий">
          <el-input v-model="form.comment" placeholder="не обязательно" />
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
          :disabled="!form.warehouse_id || !form.tech_card_id"
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

import { CAN } from "~/utils/access";

definePageMeta({ permissions: CAN.productionOrdersOpen });

type ProductionOrderListItem =
  components["schemas"]["ProductionOrderListItemSchema"];
type TechCardListItem = components["schemas"]["TechCardListItemSchema"];
type Warehouse = components["schemas"]["WarehouseSchema"];

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

const PAGE_SIZE = 50;

const api = useApi();
const { can } = useCurrentUser();
const { scopeId } = useCurrentScope();

const items = ref<ProductionOrderListItem[]>([]);
const warehouses = ref<Warehouse[]>([]);
const techCards = ref<TechCardListItem[]>([]);
const total = ref(0);
const page = ref(1);
const warehouseId = ref<string | null>(null);
const statuses = ref<string[]>([]);
const pending = ref(false);
const error = ref("");

const createOpen = ref(false);
const createError = ref("");
const saving = ref(false);
const form = reactive({
  warehouse_id: "",
  tech_card_id: "",
  batch_count: 1,
  occurred_at: "",
  comment: "",
});

function formatDay(value: string): string {
  return new Date(value).toLocaleDateString("ru-RU");
}


function localNow(): string {
  const now = new Date();
  const pad = (value: number): string => String(value).padStart(2, "0");
  const offsetMinutes = -now.getTimezoneOffset();
  const sign = offsetMinutes >= 0 ? "+" : "-";
  const absolute = Math.abs(offsetMinutes);
  const offset = `${sign}${pad(Math.floor(absolute / 60))}:${pad(absolute % 60)}`;

  return [
    `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`,
    `T${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`,
    offset,
  ].join("");
}

function formatQuantity(value: string): string {
  const numeric = Number(value);

  return Number.isNaN(numeric)
    ? value
    : numeric.toLocaleString("ru-RU", { maximumFractionDigits: 3 });
}

async function loadOrders(): Promise<void> {
  error.value = "";
  pending.value = true;

  try {
    const { data, response } = await api.GET("/api/production/orders", {
      params: {
        query: {
          warehouse_id: warehouseId.value ?? undefined,
          statuses: statuses.value.length ? statuses.value.join(",") : undefined,
          limit: PAGE_SIZE,
          offset: (page.value - 1) * PAGE_SIZE,
        },
      },
    });

    if (!response.ok || !data) {
      error.value =
        response.status === 403
          ? "Нет доступа к заданиям этой точки"
          : "Не удалось загрузить задания";
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

async function loadDictionaries(): Promise<void> {
  const [warehouseResponse, cardResponse] = await Promise.all([
    api.GET("/api/inventory/warehouses", {}),
    api.GET("/api/production/tech-cards", {
      params: { query: { limit: 100 } },
    }),
  ]);

  if (warehouseResponse.response.ok && warehouseResponse.data) {
    warehouses.value = warehouseResponse.data;
  }
  if (cardResponse.response.ok && cardResponse.data) {
    techCards.value = cardResponse.data.items;
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

async function openOrder(row: ProductionOrderListItem): Promise<void> {
  await navigateTo(`/production/orders/${row.id}`);
}

function openCreate(): void {
  createError.value = "";
  form.warehouse_id = warehouseId.value ?? warehouses.value[0]?.id ?? "";
  form.tech_card_id = techCards.value[0]?.id ?? "";
  form.batch_count = 1;
  form.occurred_at = localNow();
  form.comment = "";
  createOpen.value = true;
}

async function createOrder(): Promise<void> {
  createError.value = "";
  saving.value = true;

  try {
    const { data, response, error: failure } = await api.POST(
      "/api/production/orders",
      {
        body: {
          warehouse_id: form.warehouse_id,
          tech_card_id: form.tech_card_id,
          batch_count: String(form.batch_count),
          occurred_at: form.occurred_at || localNow(),
          comment: form.comment.trim() || null,
        },
      },
    );

    if (!response.ok || !data) {
      const payload = failure as { message?: string } | undefined;
      createError.value =
        payload?.message ?? `Не удалось создать задание: ${response.status}`;
      return;
    }

    createOpen.value = false;
    await navigateTo(`/production/orders/${data.id}`);
  } finally {
    saving.value = false;
  }
}

watch(scopeId, () => {
  void reload();
});

onMounted(async () => {
  await loadDictionaries();
  await loadOrders();
});
</script>

<style scoped>
.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  margin: 16px 0;
}

.pager {
  margin-top: 16px;
  justify-content: flex-end;
}
</style>
