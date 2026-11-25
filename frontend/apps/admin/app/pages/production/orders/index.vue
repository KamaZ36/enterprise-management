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
        v-model="locationId"
        clearable
        placeholder="Цех"
        style="width: 220px"
        @change="reload"
      >
        <LocationOptions :locations="productionLocations" />
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
      <el-table-column label="Дата производства" width="170">
        <template #default="{ row }">{{ formatDay(row.occurred_at) }}</template>
      </el-table-column>
      <el-table-column label="Цех">
        <template #default="{ row }">{{ row.location_name ?? "—" }}</template>
      </el-table-column>
      <el-table-column label="Техкарта" width="240">
        <template #default="{ row }">
          <span v-if="row.tech_card_code" class="muted">
            {{ row.tech_card_code }} v{{ row.tech_card_version }}
          </span>
          <span v-else class="muted">вручную</span>
        </template>
      </el-table-column>
      <el-table-column label="Закладок" width="120" align="right">
        <template #default="{ row }">
          {{ row.tech_card_id ? formatQuantity(row.batch_count) : "—" }}
        </template>
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
          <el-select
            v-model="form.org_unit_id"
            placeholder="Выберите цех"
            style="width: 100%"
          >
            <LocationOptions :locations="productionLocations" />
          </el-select>
          <p v-if="!productionLocations.length" class="muted">
            Нет подразделений типа «Производство». Создайте цех в
            «Подразделениях».
          </p>
        </el-form-item>

        <el-form-item label="Способ">
          <el-radio-group v-model="form.mode">
            <el-radio-button value="card">По техкарте</el-radio-button>
            <el-radio-button value="manual">Вручную</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <template v-if="form.mode === 'card'">
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
        </template>

        <template v-else>
          <h3 class="group">Сырьё</h3>
          <div
            v-for="(line, index) in form.components"
            :key="`c-${index}`"
            class="line"
          >
            <el-select
              v-model="line.nomenclature_id"
              filterable
              placeholder="Сырьё"
              class="line__name"
            >
              <el-option
                v-for="item in nomenclatures"
                :key="item.id"
                :label="item.name"
                :value="item.id"
              />
            </el-select>
            <el-input
              v-model="line.quantity"
              placeholder="Кол-во"
              class="line__qty"
            />
            <el-button
              text
              type="danger"
              :disabled="form.components.length === 1"
              @click="form.components.splice(index, 1)"
            >
              Убрать
            </el-button>
          </div>
          <el-button text type="primary" @click="addComponent">
            + Сырьё
          </el-button>
          <p v-if="nomenclaturesError" class="hint">{{ nomenclaturesError }}</p>
          <p v-else-if="!nomenclatures.length" class="hint">
            Номенклатуры пока нет — заведите её в «Справочниках».
          </p>

          <h3 class="group">Выход</h3>
          <div
            v-for="(line, index) in form.outputs"
            :key="`o-${index}`"
            class="line"
          >
            <el-select
              v-model="line.nomenclature_id"
              filterable
              placeholder="Готовая продукция"
              class="line__name"
            >
              <el-option
                v-for="item in nomenclatures"
                :key="item.id"
                :label="item.name"
                :value="item.id"
              />
            </el-select>
            <el-button
              text
              type="danger"
              :disabled="form.outputs.length === 1"
              @click="form.outputs.splice(index, 1)"
            >
              Убрать
            </el-button>
          </div>
          <el-button text type="primary" @click="addOutput">
            + Выход
          </el-button>

          <p class="hint">
            Количество выхода вводится при проведении. Разница между сырьём и
            выходом станет потерями.
          </p>
        </template>

        <el-row :gutter="16">
          <el-col v-if="form.mode === 'card'" :span="12">
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
          <el-col :span="form.mode === 'card' ? 12 : 24">
            <el-form-item label="Дата производства">
              <el-date-picker
                v-model="form.occurred_at"
                type="datetime"
                value-format="YYYY-MM-DDTHH:mm:ssZ"
                style="width: 100%"
              />
              <span class="hint">
                На эту дату спишется сырьё и оприходуется продукция.
              </span>
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
          :disabled="!canSubmit"
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
type Location = components["schemas"]["LocationSchema"];
type Nomenclature = components["schemas"]["NomenclatureSchema"];

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

const items = ref<ProductionOrderListItem[]>([]);
const locations = ref<Location[]>([]);
const productionLocations = computed(() =>
  locations.value.filter((location) => location.type === "production"),
);
const techCards = ref<TechCardListItem[]>([]);
const nomenclatures = ref<Nomenclature[]>([]);
const nomenclaturesError = ref("");
const total = ref(0);
const page = ref(1);
const locationId = ref<string | null>(null);
const statuses = ref<string[]>([]);
const pending = ref(false);
const error = ref("");

const createOpen = ref(false);
const createError = ref("");
const saving = ref(false);
const form = reactive({
  mode: "card" as "card" | "manual",
  org_unit_id: "",
  tech_card_id: "",
  batch_count: 1,
  components: [{ nomenclature_id: "", quantity: "" }],
  outputs: [{ nomenclature_id: "" }],
  occurred_at: "",
  comment: "",
});

const canSubmit = computed(() => {
  if (!form.org_unit_id) {
    return false;
  }

  if (form.mode === "card") {
    return Boolean(form.tech_card_id) && form.batch_count > 0;
  }

  const componentsOk = form.components.some(
    (line) => line.nomenclature_id && Number(line.quantity) > 0,
  );
  const outputsOk = form.outputs.some((line) => line.nomenclature_id);

  return componentsOk && outputsOk;
});

function addComponent(): void {
  form.components.push({ nomenclature_id: "", quantity: "" });
}

function addOutput(): void {
  form.outputs.push({ nomenclature_id: "" });
}

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
          org_unit_id: locationId.value ?? undefined,
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
  const cardResponse = await api.GET("/api/production/tech-cards", {
    params: { query: { limit: 100 } },
  });

  if (cardResponse.response.ok && cardResponse.data) {
    techCards.value = cardResponse.data.items;
  }

  const nomenclatureResponse = await api.GET("/api/catalog/nomenclatures", {
    params: { query: { limit: 100 } },
  });

  if (nomenclatureResponse.response.ok && nomenclatureResponse.data) {
    nomenclatures.value = nomenclatureResponse.data.items;
    nomenclaturesError.value = "";
  } else {
    nomenclatures.value = [];
    nomenclaturesError.value = "Не удалось загрузить номенклатуру";
  }

  if (can("production.order.read")) {
    const { data, response } = await api.GET("/api/inventory/locations", {});
    if (response.ok && data) {
      locations.value = data;
    }
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
  form.mode = techCards.value.length ? "card" : "manual";
  form.org_unit_id =
    locationId.value ?? productionLocations.value[0]?.id ?? "";
  form.tech_card_id = techCards.value[0]?.id ?? "";
  form.batch_count = 1;
  form.components = [{ nomenclature_id: "", quantity: "" }];
  form.outputs = [{ nomenclature_id: "" }];
  form.occurred_at = localNow();
  form.comment = "";
  createOpen.value = true;
}

async function createOrder(): Promise<void> {
  createError.value = "";
  saving.value = true;

  try {
    const body: components["schemas"]["CreateProductionOrderSchema"] =
      form.mode === "card"
        ? {
            org_unit_id: form.org_unit_id,
            occurred_at: form.occurred_at || localNow(),
            tech_card_id: form.tech_card_id,
            batch_count: String(form.batch_count),
            comment: form.comment.trim() || null,
          }
        : {
            org_unit_id: form.org_unit_id,
            occurred_at: form.occurred_at || localNow(),
            components: form.components
              .filter(
                (line) => line.nomenclature_id && Number(line.quantity) > 0,
              )
              .map((line) => ({
                nomenclature_id: line.nomenclature_id,
                quantity: String(Number(line.quantity)),
              })),
            outputs: form.outputs
              .filter((line) => line.nomenclature_id)
              .map((line) => ({
                nomenclature_id: line.nomenclature_id,
                quantity: "0",
              })),
            comment: form.comment.trim() || null,
          };

    const { data, response, error: failure } = await api.POST(
      "/api/production/orders",
      { body },
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

.group {
  margin: 24px 0 12px;
  font-size: 16px;
}

.line {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}

.line__name {
  flex: 1;
  min-width: 220px;
}

.line__qty {
  width: 140px;
}

.hint {
  display: block;
  margin-top: 8px;
  color: #909399;
  font-size: 12px;
}
</style>
