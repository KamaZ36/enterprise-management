<template>
  <el-dialog
    v-model="open"
    title="Сопоставить товар DoKa"
    width="640"
    @open="prepare"
  >
    <el-alert
      v-if="error"
      :title="error"
      type="error"
      :closable="false"
      show-icon
      class="form-error"
    />

    <div class="product">
      <div class="product__name">{{ productName || "Товар без названия" }}</div>
      <div class="product__meta">
        <span class="mono">{{ productGuid }}</span>
        <span v-if="productUnit"> · {{ productUnit }}</span>
      </div>
    </div>

    <el-form label-position="top" @submit.prevent>
      <el-form-item label="Номенклатура">
        <div class="search">
          <el-input
            v-model="search"
            placeholder="Название или артикул"
            clearable
            @keyup.enter="findNomenclatures"
            @clear="findNomenclatures"
          />
          <el-button :loading="searching" @click="findNomenclatures">
            Найти
          </el-button>
        </div>

        <el-select
          v-model="nomenclatureId"
          filterable
          placeholder="Выберите номенклатуру"
          style="width: 100%"
        >
          <el-option
            v-for="item in options"
            :key="item.id"
            :label="`${item.name} · ${item.sku}`"
            :value="item.id"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="Коэффициент пересчёта">
        <el-input-number
          v-model="unitFactor"
          :min="0.000001"
          :step="1"
          :precision="6"
          controls-position="right"
        />
        <div class="hint">
          1 единица DoKa = коэффициент единиц номенклатуры. Для «кг → кг»
          оставьте 1; если 1 шт весит 0,2 кг — укажите 0,2.
        </div>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="open = false">Отмена</el-button>
      <el-button
        type="primary"
        :loading="saving"
        :disabled="!nomenclatureId"
        @click="save"
      >
        Сопоставить
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import type { components } from "@md/api-client";
import { ElMessage } from "element-plus";

type Nomenclature = components["schemas"]["NomenclatureSchema"];

const props = defineProps<{
  sourceId: string;
  productGuid: string;
  productName?: string | null;
  productUnit?: string | null;
  unitFactor?: string | number | null;
}>();

const emit = defineEmits<{ mapped: [] }>();

const open = defineModel<boolean>({ required: true });

const api = useApi();

const search = ref("");
const searching = ref(false);
const saving = ref(false);
const error = ref("");
const options = ref<Nomenclature[]>([]);
const nomenclatureId = ref("");
const unitFactor = ref(1);

function prepare(): void {
  error.value = "";
  search.value = props.productName ?? "";
  nomenclatureId.value = "";
  unitFactor.value = props.unitFactor ? Number(props.unitFactor) : 1;
  options.value = [];
  void findNomenclatures();
}

async function findNomenclatures(): Promise<void> {
  searching.value = true;
  error.value = "";

  try {
    const { data, response } = await api.GET("/api/catalog/nomenclatures", {
      params: {
        query: {
          search: search.value.trim() || undefined,
          limit: 30,
          offset: 0,
        },
      },
    });

    if (!response.ok || !data) {
      throw new Error(messageOf(response.status, "Не удалось найти товары"));
    }

    options.value = data.items;
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Ошибка поиска";
    options.value = [];
  } finally {
    searching.value = false;
  }
}

async function save(): Promise<void> {
  if (!nomenclatureId.value) {
    return;
  }

  saving.value = true;
  error.value = "";

  try {
    const { response, error: failure } = await api.PUT(
      "/api/pos/sources/{source_id}/product-map",
      {
        params: { path: { source_id: props.sourceId } },
        body: {
          doka_product_guid: props.productGuid,
          nomenclature_id: nomenclatureId.value,
          unit_factor: String(unitFactor.value),
        },
      },
    );

    if (!response.ok) {
      const message = (failure as { message?: string } | undefined)?.message;
      throw new Error(
        message ?? messageOf(response.status, "Не удалось сопоставить товар"),
      );
    }

    ElMessage.success("Товар сопоставлен. Чеки, ждавшие разметку, готовы.");
    emit("mapped");
    open.value = false;
  } catch (cause) {
    error.value =
      cause instanceof Error ? cause.message : "Ошибка сопоставления";
  } finally {
    saving.value = false;
  }
}

function messageOf(status: number, fallback: string): string {
  if (status === 403) return "Нет прав на это действие";
  if (status === 404) return "Товар или номенклатура не найдены";
  if (status === 422) return "Проверьте выбранные значения";

  return `${fallback}: ${status}`;
}
</script>

<style scoped>
.product {
  margin-bottom: 16px;
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--el-fill-color-light);
}

.product__name {
  font-weight: 600;
}

.product__meta {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  word-break: break-all;
}

.mono {
  font-family: monospace;
}

.search {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
  width: 100%;
}

.hint {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.4;
  margin-top: 4px;
}

.form-error {
  margin-bottom: 12px;
}
</style>
