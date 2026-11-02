<template>
  <div class="page">
    <h1 class="page__title">Стоп-лист</h1>
    <p class="page__subtitle">
      Товары, недоступные к заказу на сайте и в онлайн-продажах точки.
    </p>

    <el-alert
      v-if="error"
      :title="error"
      type="error"
      :closable="false"
      show-icon
      class="page__error"
    />
    <el-alert
      v-if="notice"
      :title="notice"
      type="success"
      :closable="false"
      show-icon
      class="page__error"
    />

    <div class="page__toolbar">
      <el-select
        v-model="pointId"
        placeholder="Точка"
        style="width: 280px"
        :disabled="!points.length"
        @change="loadMenu"
      >
        <el-option
          v-for="point in points"
          :key="point.id"
          :label="point.name"
          :value="point.id"
        />
      </el-select>

      <el-input
        v-model="search"
        placeholder="Поиск: название или SKU"
        style="width: 280px"
        clearable
      />

      <el-button :loading="pending" :disabled="!pointId" @click="loadMenu">
        Обновить
      </el-button>

      <el-tag v-if="stoppedCount" type="danger" effect="light">
        в стопе: {{ stoppedCount }}
      </el-tag>
    </div>

    <el-empty
      v-if="!points.length && !pending"
      description="Нет доступных точек"
    />

    <el-table
      v-else
      v-loading="pending"
      :data="visible"
      empty-text="В меню точки пока нет товаров"
      class="page__table"
    >
      <el-table-column prop="name" label="Товар" min-width="260">
        <template #default="{ row }">
          <div>{{ row.name }}</div>
          <div class="muted hint">{{ row.sku }}</div>
        </template>
      </el-table-column>

      <el-table-column label="Цена" width="140" align="right">
        <template #default="{ row }">{{ formatPrice(row.value) }}</template>
      </el-table-column>

      <el-table-column label="Доступность" width="180" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.stopped" type="danger" effect="light">
            в стоп-листе
          </el-tag>
          <el-tag v-else type="success" effect="light">в продаже</el-tag>
        </template>
      </el-table-column>

      <el-table-column label="В стопе с" width="180">
        <template #default="{ row }">
          {{ row.stoppedAt ? formatDate(row.stoppedAt) : "—" }}
        </template>
      </el-table-column>

      <el-table-column v-if="canManage" width="180" align="right">
        <template #default="{ row }">
          <el-button
            v-if="row.stopped"
            text
            type="success"
            :loading="busyId === row.nomenclature_id"
            @click="resume(row as MenuRow)"
          >
            Вернуть в меню
          </el-button>
          <el-button
            v-else
            text
            type="danger"
            :loading="busyId === row.nomenclature_id"
            @click="stop(row as MenuRow)"
          >
            В стоп-лист
          </el-button>
        </template>
      </el-table-column>

      <template #empty>
        <el-empty description="В меню точки пока нет товаров" />
      </template>
    </el-table>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ permissions: ["stop_list.read"] });

const api = useApi();
const { can } = useCurrentUser();
const { units, load: loadUnits } = useMyUnits();

type Point = { id: string; name: string };
type MenuRow = {
  nomenclature_id: string;
  name: string;
  sku: string;
  value: number;
  stopped: boolean;
  stoppedAt: string | null;
};

const points = ref<Point[]>([]);
const pointId = ref("");
const rows = ref<MenuRow[]>([]);
const search = ref("");
const pending = ref(false);
const busyId = ref("");
const error = ref("");
const notice = ref("");

const canManage = computed(() => can("stop_list.manage"));

const stoppedCount = computed(
  () => rows.value.filter((row) => row.stopped).length,
);

const visible = computed(() => {
  const needle = search.value.trim().toLowerCase();
  if (!needle) {
    return rows.value;
  }

  return rows.value.filter(
    (row) =>
      row.name.toLowerCase().includes(needle) ||
      row.sku.toLowerCase().includes(needle),
  );
});

function formatPrice(value: number): string {
  return `${(value / 100).toLocaleString("ru-RU", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })} ₽`;
}

function formatDate(value: string): string {
  return new Date(value).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

async function loadPoints(): Promise<void> {
  await loadUnits();

  const allowed = units.value.filter(
    (unit) =>
      unit.permissions.includes("stop_list.read") ||
      unit.permissions.includes("stop_list.manage"),
  );

  if (allowed.length) {
    points.value = allowed.map((unit) => ({ id: unit.id, name: unit.title }));
    return;
  }

  if (!can("org_unit.read")) {
    return;
  }

  const { data, response } = await api.GET("/api/business/org-units", {});

  if (!response.ok || !data) {
    error.value = "Не удалось загрузить список точек";
    return;
  }

  const list = data as unknown as {
    id: string;
    name: string;
    type: string;
  }[];

  points.value = list
    .filter((unit) => unit.type === "cafe" || unit.type === "shop")
    .map((unit) => ({ id: unit.id, name: unit.name }));
}

async function loadMenu(): Promise<void> {
  if (!pointId.value) {
    rows.value = [];
    return;
  }

  pending.value = true;
  error.value = "";
  notice.value = "";

  try {
    const [assortment, stopList] = await Promise.all([
      api.GET("/api/catalog/org-units/{org_unit_id}/assortment", {
        params: { path: { org_unit_id: pointId.value } },
      }),
      api.GET("/api/catalog/org-units/{org_unit_id}/stop-list", {
        params: { path: { org_unit_id: pointId.value } },
      }),
    ]);

    if (!assortment.response.ok || !assortment.data) {
      throw new Error("Не удалось загрузить меню точки");
    }
    if (!stopList.response.ok || !stopList.data) {
      throw new Error("Не удалось загрузить стоп-лист");
    }

    const stopped = new Map(
      stopList.data.items.map((item) => [item.nomenclature_id, item.created_at]),
    );
    const menuIds = new Set(
      assortment.data.items.map((item) => item.nomenclature_id),
    );

    rows.value = assortment.data.items.map((item) => ({
      nomenclature_id: item.nomenclature_id,
      name: item.name,
      sku: item.sku,
      value: item.value,
      stopped: stopped.has(item.nomenclature_id),
      stoppedAt: stopped.get(item.nomenclature_id) ?? null,
    }));

    for (const item of stopList.data.items) {
      if (menuIds.has(item.nomenclature_id)) {
        continue;
      }

      rows.value.push({
        nomenclature_id: item.nomenclature_id,
        name: item.nomenclature_name,
        sku: item.sku,
        value: 0,
        stopped: true,
        stoppedAt: item.created_at,
      });
    }
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Ошибка загрузки";
  } finally {
    pending.value = false;
  }
}

async function stop(row: MenuRow): Promise<void> {
  busyId.value = row.nomenclature_id;
  error.value = "";
  notice.value = "";

  try {
    const { response } = await api.POST(
      "/api/catalog/org-units/{org_unit_id}/stop-list",
      {
        params: { path: { org_unit_id: pointId.value } },
        body: { nomenclature_id: row.nomenclature_id },
      },
    );

    if (!response.ok) {
      error.value = "Не удалось добавить товар в стоп-лист";
      return;
    }

    await loadMenu();
    notice.value = `«${row.name}» добавлен в стоп-лист`;
  } finally {
    busyId.value = "";
  }
}

async function resume(row: MenuRow): Promise<void> {
  busyId.value = row.nomenclature_id;
  error.value = "";
  notice.value = "";

  try {
    const { response } = await api.DELETE(
      "/api/catalog/org-units/{org_unit_id}/stop-list/{nomenclature_id}",
      {
        params: {
          path: {
            org_unit_id: pointId.value,
            nomenclature_id: row.nomenclature_id,
          },
        },
      },
    );

    if (!response.ok) {
      error.value = "Не удалось убрать товар из стоп-листа";
      return;
    }

    await loadMenu();
    notice.value = `«${row.name}» возвращён в меню`;
  } finally {
    busyId.value = "";
  }
}

onMounted(async () => {
  await loadPoints();
  pointId.value = points.value[0]?.id ?? "";
  await loadMenu();
});
</script>

<style scoped>
.hint {
  font-size: 11px;
}

.muted {
  color: #909399;
}
</style>
