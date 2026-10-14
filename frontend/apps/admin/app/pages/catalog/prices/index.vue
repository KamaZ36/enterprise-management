<template>
  <div class="page">
    <h1 class="page__title">Цены</h1>
    <p class="page__subtitle">
      Выберите прайс-лист и задайте цены. Пустое поле означает, что цена не задана.
    </p>

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
        v-model="priceListId"
        placeholder="Прайс-лист"
        style="width: 280px"
        @change="reload"
      >
        <el-option
          v-for="list in priceLists"
          :key="list.id"
          :label="list.name"
          :value="list.id"
        />
      </el-select>

      <el-input
        v-model="search"
        placeholder="Поиск: название или артикул"
        style="width: 280px"
        clearable
        @keyup.enter="reload"
      />

      <el-button :loading="pending" @click="reload">Обновить</el-button>
      <el-button type="primary" @click="openCreateList">Новый прайс-лист</el-button>
      <span style="color: #909399">Позиций: {{ total }}</span>
    </div>

    <el-dialog v-model="createListOpen" title="Новый прайс-лист" width="480">
      <el-alert
        v-if="createListError"
        :title="createListError"
        type="error"
        :closable="false"
        show-icon
        class="page__error"
      />

      <el-form label-position="top" @submit.prevent>
        <el-form-item label="Название">
          <el-input
            v-model="newListName"
            placeholder="Например: Розничные цены или Кафе"
            @keyup.enter="createPriceList"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="createListOpen = false">Отмена</el-button>
        <el-button type="primary" :loading="createListSaving" @click="createPriceList">
          Создать
        </el-button>
      </template>
    </el-dialog>

    <div
      v-if="priceLists.length"
      style="
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        align-items: center;
        margin-bottom: 16px;
        padding: 12px 16px;
        border: 1px solid #e4e7ed;
        border-radius: 8px;
      "
    >
      <span style="font-weight: 600">Прайс-лист для точки:</span>

      <el-select
        v-model="targetUnitId"
        placeholder="Точка"
        style="width: 260px"
        @change="loadBinding"
      >
        <el-option
          v-for="unit in orgUnits"
          :key="unit.id"
          :label="unit.name"
          :value="unit.id"
        />
      </el-select>

      <el-select
        v-model="targetListId"
        placeholder="Прайс-лист"
        style="width: 240px"
      >
        <el-option
          v-for="list in priceLists"
          :key="list.id"
          :label="list.name"
          :value="list.id"
        />
      </el-select>

      <el-button
        type="primary"
        :loading="bindingSaving"
        :disabled="!targetUnitId || !targetListId"
        @click="saveBinding"
      >
        Назначить
      </el-button>

      <span v-if="targetUnitId" style="color: #909399">
        {{ bindingName ? `сейчас: ${bindingName}` : "сейчас не назначен" }}
      </span>
    </div>

    <el-empty
      v-if="!pending && !priceLists.length"
      description="Прайс-листов пока нет. Их можно создать через API — интерфейса для этого ещё нет."
    />

    <el-empty
      v-else-if="!pending && !items.length"
      description="В этом прайс-листе пока нет ни одной позиции"
    />

    <el-table v-if="items.length" v-loading="pending" :data="items" stripe border>
      <el-table-column prop="sku" label="Артикул" width="170" />
      <el-table-column prop="nomenclature_name" label="Название" min-width="240" />

      <el-table-column label="Сейчас" width="140" align="right">
        <template #default="{ row }">
          <span v-if="row.value === null" style="color: #909399">не задана</span>
          <span v-else>{{ formatKopecks(row.value) }}</span>
        </template>
      </el-table-column>

      <el-table-column label="Новая цена, ₽" width="190">
        <template #default="{ row }">
          <el-input
            v-model="inputs[row.nomenclature_id]"
            size="small"
            placeholder="например 450"
          />
        </template>
      </el-table-column>

      <el-table-column width="140" align="right">
        <template #default="{ row }">
          <el-button
            size="small"
            :loading="saving === row.nomenclature_id"
            @click="save(row as { nomenclature_id: string })"
          >
            Сохранить
          </el-button>
        </template>
      </el-table-column>
    </el-table>

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

type PriceListEntry = components["schemas"]["PriceListEntrySchema"];
type PriceListItem = components["schemas"]["PriceListPriceSchema"];

const api = useApi();

const priceLists = ref<PriceListEntry[]>([]);
const priceListId = ref("");
const items = ref<PriceListItem[]>([]);
const total = ref(0);
const search = ref("");
const inputs = reactive<Record<string, string>>({});
const pending = ref(false);
const saving = ref<string | null>(null);
const error = ref("");

async function loadPriceLists(): Promise<void> {
  const { data, response } = await api.GET("/api/catalog/price-lists", {});

  if (!response.ok || !data) {
    error.value = "Не удалось загрузить прайс-листы";
    return;
  }

  priceLists.value = data.items;

  if (!priceListId.value && data.items.length) {
    priceListId.value = data.items[0]!.id;
  }

  await loadPrices();
}

async function loadPrices(): Promise<void> {
  error.value = "";

  if (!priceListId.value) {
    items.value = [];
    total.value = 0;
    return;
  }

  pending.value = true;

  try {
    const { data, response } = await api.GET(
      "/api/catalog/price-lists/{price_list_id}/prices",
      {
        params: {
          path: { price_list_id: priceListId.value },
          query: {
            search: search.value || undefined,
            limit: PAGE_SIZE,
            offset: (page.value - 1) * PAGE_SIZE,
          },
        },
      },
    );

    if (!response.ok || !data) {
      error.value = "Не удалось загрузить позиции прайс-листа";
      return;
    }

    if (!data.items.length && page.value > 1) {
      page.value = Math.min(
        page.value - 1,
        Math.max(1, Math.ceil(data.total / PAGE_SIZE)),
      );
      await loadPrices();
      return;
    }

    items.value = data.items;
    total.value = data.total;

    for (const item of data.items) {
      inputs[item.nomenclature_id] =
        item.value === null ? "" : String(item.value / 100);
    }
  } finally {
    pending.value = false;
  }
}

async function save(row: { nomenclature_id: string }): Promise<void> {
  const raw = (inputs[row.nomenclature_id] ?? "").replace(",", ".").trim();
  const price = Number(raw);

  if (!raw || Number.isNaN(price) || price < 0) {
    error.value = "Введите цену числом, например 450 или 450,50";
    return;
  }

  saving.value = row.nomenclature_id;

  try {
    const { response } = await api.POST("/api/catalog/price-lists/{price_list_id}/prices", {
      params: { path: { price_list_id: priceListId.value } },
      body: { nomenclature_id: row.nomenclature_id, price },
    });

    if (!response.ok) {
      error.value = "Не удалось сохранить цену";
      return;
    }

    await loadPrices();
  } finally {
    saving.value = null;
  }
}

onMounted(async () => {
  await loadOrgUnits();
  await loadPriceLists();
});
const createListOpen = ref(false);
const createListSaving = ref(false);
const createListError = ref("");
const newListName = ref("");

function openCreateList(): void {
  createListError.value = "";
  newListName.value = "";
  createListOpen.value = true;
}

async function createPriceList(): Promise<void> {
  const name = newListName.value.trim();

  if (!name) {
    createListError.value = "Введите название прайс-листа";
    return;
  }

  createListSaving.value = true;

  try {
    const { data, response } = await api.POST("/api/catalog/price-lists", {
      body: { name },
    });

    if (!response.ok || !data) {
      createListError.value = "Не удалось создать прайс-лист";
      return;
    }

    createListOpen.value = false;
    priceListId.value = (data as { price_list_id: string }).price_list_id;
    await loadPriceLists();
  } finally {
    createListSaving.value = false;
  }
}

const orgUnits = ref<{ id: string; name: string }[]>([]);
const targetUnitId = ref("");
const targetListId = ref("");
const bindingName = ref<string | null>(null);
const bindingSaving = ref(false);

async function loadOrgUnits(): Promise<void> {
  const { data, response } = await api.GET("/api/business/org-units", {});

  if (!response.ok || !data) {
    error.value = "Не удалось загрузить список подразделений";
    return;
  }

  const raw = data as unknown;
  const list = Array.isArray(raw)
    ? raw
    : ((raw as { items?: { id: string; name: string }[] }).items ?? []);

  orgUnits.value = list as { id: string; name: string }[];
}

async function loadBinding(): Promise<void> {
  bindingName.value = null;
  targetListId.value = "";

  if (!targetUnitId.value) {
    return;
  }

  const { data, response } = await api.GET(
    "/api/catalog/org-units/{org_unit_id}/price-list",
    { params: { path: { org_unit_id: targetUnitId.value } } },
  );

  if (!response.ok || !data) {
    return;
  }

  targetListId.value = data.price_list_id;
  bindingName.value =
    priceLists.value.find((item) => item.id === data.price_list_id)?.name ?? null;
}

async function saveBinding(): Promise<void> {
  if (!targetUnitId.value || !targetListId.value) {
    error.value = "Выберите точку и прайс-лист";
    return;
  }

  bindingSaving.value = true;
  error.value = "";

  try {
    const { response } = await api.PUT("/api/catalog/org-units/{org_unit_id}/price-list", {
      params: { path: { org_unit_id: targetUnitId.value } },
      body: { price_list_id: targetListId.value },
    });

    if (!response.ok) {
      error.value = "Не удалось назначить прайс-лист точке";
      return;
    }

    await loadBinding();
  } finally {
    bindingSaving.value = false;
  }
}

const page = ref(1);
const PAGE_SIZE = 50;

const totalPages = computed(() =>
  Math.max(1, Math.ceil(total.value / PAGE_SIZE)),
);

async function reload(): Promise<void> {
  page.value = 1;
  await loadPrices();
}

async function goToPage(target: number): Promise<void> {
  page.value = target;
  await loadPrices();
}
</script>
