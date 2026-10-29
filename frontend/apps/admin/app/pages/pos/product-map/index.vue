<template>
  <div class="page">
    <h1 class="page__title">Разметка товаров DoKa</h1>
    <p class="page__subtitle">
      Товары из чеков DoKa сопоставляются с номенклатурой. Пока товар не
      сопоставлен, чек ждёт в статусе «Нужно сопоставить». Коэффициент
      пересчёта переводит единицы DoKa в единицы номенклатуры.
    </p>

    <el-alert
      v-if="notice"
      :title="notice"
      type="success"
      :closable="false"
      show-icon
      class="page__error"
    />
    <el-alert
      v-if="error"
      :title="error"
      type="error"
      :closable="false"
      show-icon
      class="page__error"
    />

    <el-alert
      v-if="sourcesReady && !sources.length"
      title="Сначала зарегистрируйте кассу DoKa"
      type="info"
      :closable="false"
      show-icon
      class="page__error"
    >
      <NuxtLink to="/pos/sources">Перейти к кассам DoKa</NuxtLink>
    </el-alert>

    <div v-if="sources.length" class="page__toolbar">
      <el-select
        v-model="sourceId"
        placeholder="Выберите кассу"
        style="width: 260px"
        @change="loadAll"
      >
        <el-option
          v-for="source in sources"
          :key="source.id"
          :label="source.name"
          :value="source.id"
        />
      </el-select>

      <el-input
        v-model="search"
        placeholder="Поиск по товару, GUID или номенклатуре"
        clearable
        style="width: 320px"
      />

      <el-button :loading="pending" @click="loadAll">Обновить</el-button>
    </div>

    <template v-if="sources.length">
      <el-card shadow="never" class="block">
        <template #header>
          <div class="card-header">
            <span>Не сопоставлены</span>
            <el-tag type="warning" effect="plain">
              {{ filteredUnmapped.length }}
            </el-tag>
          </div>
        </template>

        <el-table
          :data="filteredUnmapped"
          v-loading="pending"
          empty-text="Все товары из чеков сопоставлены"
        >
          <el-table-column label="Товар в DoKa" min-width="220">
            <template #default="{ row }">
              <div>{{ (row as PosUnmapped).product_name ?? "Без названия" }}</div>
              <div class="muted mono">
                {{ shortGuid((row as PosUnmapped).product_guid) }}
              </div>
            </template>
          </el-table-column>

          <el-table-column label="Единица" width="100">
            <template #default="{ row }">
              {{ (row as PosUnmapped).unit ?? "—" }}
            </template>
          </el-table-column>

          <el-table-column label="Чеков" width="90" align="center">
            <template #default="{ row }">
              {{ (row as PosUnmapped).receipts_count }}
            </template>
          </el-table-column>

          <el-table-column label="Последний раз" width="165">
            <template #default="{ row }">
              {{ formatDate((row as PosUnmapped).last_seen_at) }}
            </template>
          </el-table-column>

          <el-table-column label="" width="140" align="right">
            <template #default="{ row }">
              <el-button
                v-if="can('pos.receipt_manage')"
                type="primary"
                text
                @click="openMap(row as PosUnmapped)"
              >
                Сопоставить
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card shadow="never" class="block">
        <template #header>
          <div class="card-header">
            <span>Сопоставления</span>
            <el-tag type="success" effect="plain">
              {{ filteredMappings.length }}
            </el-tag>
          </div>
        </template>

        <el-table
          :data="filteredMappings"
          v-loading="pending"
          empty-text="Сопоставлений пока нет"
        >
          <el-table-column label="Товар DoKa" min-width="220">
            <template #default="{ row }">
              <span class="mono">{{ shortGuid((row as PosMapping).doka_product_guid) }}</span>
            </template>
          </el-table-column>

          <el-table-column label="Номенклатура" min-width="240">
            <template #default="{ row }">
              <span v-if="(row as PosMapping).nomenclature_name">
                {{ (row as PosMapping).nomenclature_name }}
              </span>
              <span v-else class="muted">
                {{ shortGuid((row as PosMapping).nomenclature_id) }}
              </span>
            </template>
          </el-table-column>

          <el-table-column label="Коэффициент" width="130" align="right">
            <template #default="{ row }">
              {{ formatQuantity((row as PosMapping).unit_factor, 6) }}
            </template>
          </el-table-column>

          <el-table-column label="Статус" width="110">
            <template #default="{ row }">
              <el-tag
                :type="(row as PosMapping).is_active ? 'success' : 'info'"
                size="small"
              >
                {{ (row as PosMapping).is_active ? "Действует" : "Отключено" }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column label="Обновлено" width="165">
            <template #default="{ row }">
              {{ formatDate((row as PosMapping).updated_at) }}
            </template>
          </el-table-column>

          <el-table-column label="" width="110" align="right">
            <template #default="{ row }">
              <el-button
                v-if="can('pos.receipt_manage')"
                text
                type="danger"
                @click="removeMapping(row as PosMapping)"
              >
                Удалить
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <p class="hint">
          Удаление сопоставления не меняет уже проведённые чеки — оно влияет
          только на новые поступления и чеки, ожидающие разметки.
        </p>
      </el-card>
    </template>

    <PosMapDialog
      v-if="sourceId && mapTarget"
      v-model="mapOpen"
      :source-id="sourceId"
      :product-guid="mapTarget.product_guid"
      :product-name="mapTarget.product_name"
      :product-unit="mapTarget.unit"
      @mapped="onMapped"
    />
  </div>
</template>

<script setup lang="ts">
import { formatQuantity } from "@md/money";
import type { components } from "@md/api-client";
import { ElMessage, ElMessageBox } from "element-plus";

import { CAN } from "~/utils/access";

definePageMeta({ permissions: CAN.posProductMapOpen });

type PosSource = components["schemas"]["PosSourceSchema"];
type PosUnmapped = components["schemas"]["PosUnmappedProductSchema"];
type PosMapping = components["schemas"]["PosProductMappingSchema"];

const api = useApi();
const { can } = useCurrentUser();

const sources = ref<PosSource[]>([]);
const sourcesReady = ref(false);
const sourceId = ref("");
const unmapped = ref<PosUnmapped[]>([]);
const mappings = ref<PosMapping[]>([]);
const pending = ref(false);
const error = ref("");
const notice = ref("");
const search = ref("");

const mapOpen = ref(false);
const mapTarget = ref<PosUnmapped | null>(null);

const filteredUnmapped = computed(() => {
  const needle = search.value.trim().toLowerCase();
  if (!needle) return unmapped.value;

  return unmapped.value.filter((item) => {
    return (
      (item.product_name ?? "").toLowerCase().includes(needle) ||
      item.product_guid.toLowerCase().includes(needle)
    );
  });
});

const filteredMappings = computed(() => {
  const needle = search.value.trim().toLowerCase();
  if (!needle) return mappings.value;

  return mappings.value.filter((item) => {
    return (
      item.doka_product_guid.toLowerCase().includes(needle) ||
      (item.nomenclature_name ?? "").toLowerCase().includes(needle)
    );
  });
});

function shortGuid(value: string | null | undefined): string {
  if (!value) return "—";
  return value.length > 20 ? `${value.slice(0, 8)}…${value.slice(-4)}` : value;
}

function formatDate(value: string): string {
  return new Date(value).toLocaleString("ru-RU", {
    dateStyle: "short",
    timeStyle: "short",
  });
}

function reasonOf(status: number, body: unknown, fallback: string): string {
  const message = (body as { message?: string } | undefined)?.message;
  if (message) return message;
  if (status === 403) return "Нет прав на это действие";
  if (status === 404) return "Источник или сопоставление не найдены";
  return `${fallback}: ${status}`;
}

async function loadSources(): Promise<void> {
  try {
    const { data, response } = await api.GET("/api/pos/sources", {});

    if (!response.ok || !data) {
      throw new Error(
        reasonOf(response.status, null, "Не удалось загрузить кассы DoKa"),
      );
    }

    sources.value = data;
    if (!sourceId.value && data.length) {
      sourceId.value = data[0]!.id;
    }
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Ошибка загрузки";
    sources.value = [];
  } finally {
    sourcesReady.value = true;
  }
}

async function loadAll(): Promise<void> {
  if (!sourceId.value) {
    unmapped.value = [];
    mappings.value = [];
    return;
  }

  pending.value = true;
  error.value = "";

  try {
    const [unmappedResponse, mappingsResponse] = await Promise.all([
      api.GET("/api/pos/sources/{source_id}/unmapped-products", {
        params: { path: { source_id: sourceId.value }, query: { limit: 200 } },
      }),
      api.GET("/api/pos/sources/{source_id}/product-map", {
        params: { path: { source_id: sourceId.value } },
      }),
    ]);

    if (!unmappedResponse.response.ok || !unmappedResponse.data) {
      throw new Error(
        reasonOf(
          unmappedResponse.response.status,
          null,
          "Не удалось загрузить несопоставленные товары",
        ),
      );
    }
    if (!mappingsResponse.response.ok || !mappingsResponse.data) {
      throw new Error(
        reasonOf(
          mappingsResponse.response.status,
          null,
          "Не удалось загрузить сопоставления",
        ),
      );
    }

    unmapped.value = unmappedResponse.data;
    mappings.value = mappingsResponse.data;
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Ошибка загрузки";
    unmapped.value = [];
    mappings.value = [];
  } finally {
    pending.value = false;
  }
}

function openMap(item: PosUnmapped): void {
  mapTarget.value = item;
  mapOpen.value = true;
}

async function onMapped(): Promise<void> {
  notice.value = "";
  await loadAll();
  notice.value = "Товар сопоставлен. Чеки, ждавшие разметку, готовы к проведению.";
}

async function removeMapping(mapping: PosMapping): Promise<void> {
  try {
    await ElMessageBox.confirm(
      "Удалить сопоставление? Новые чеки с этим товаром снова попадут в разметку.",
      "Удалить сопоставление",
      {
        confirmButtonText: "Удалить",
        cancelButtonText: "Отмена",
        type: "warning",
      },
    );
  } catch {
    return;
  }

  try {
    const { response, error: failure } = await api.DELETE(
      "/api/pos/product-map/{mapping_id}",
      { params: { path: { mapping_id: mapping.id } } },
    );

    if (!response.ok) {
      throw new Error(
        reasonOf(response.status, failure, "Не удалось удалить сопоставление"),
      );
    }

    ElMessage.success("Сопоставление удалено");
    await loadAll();
  } catch (cause) {
    error.value =
      cause instanceof Error ? cause.message : "Ошибка удаления";
  }
}

onMounted(async () => {
  await loadSources();
  await loadAll();
});
</script>

<style scoped>
.muted {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.mono {
  font-family: monospace;
}

.block {
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.hint {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  margin: 12px 0 0;
}
</style>
