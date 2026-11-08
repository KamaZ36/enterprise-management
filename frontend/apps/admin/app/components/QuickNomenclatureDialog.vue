<template>
  <el-dialog v-model="open" title="Новая номенклатура" width="560">
    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="Позиция создастся и сразу подставится в строку"
      description="Артикул можно не заполнять — сгенерируем автоматически. Штрихкод поможет находить товар сканером."
      class="dialog-alert"
    />

    <el-alert
      v-if="error"
      :title="error"
      type="error"
      :closable="false"
      show-icon
      class="dialog-alert"
    />

    <el-alert
      v-if="matches.length"
      type="warning"
      :closable="false"
      show-icon
      title="Похожие позиции уже есть"
      description="Проверьте, не создаёте ли дубль. Можно выбрать существующую строку."
      class="dialog-alert"
    />
    <div v-if="matches.length" class="quick-matches">
      <div v-for="match in matches" :key="match.id" class="quick-match">
        <span>{{ match.name }} · {{ match.sku }}</span>
        <el-button text type="primary" size="small" @click="choose(match)">
          Выбрать
        </el-button>
      </div>
    </div>

    <el-form label-position="top" @submit.prevent>
      <el-form-item label="Название">
        <el-input v-model="form.name" placeholder="Например: Говядина лопатка" @change="loadMatches" />
      </el-form-item>

      <div class="form-grid">
        <el-form-item label="Артикул">
          <el-input v-model="form.sku" placeholder="необязательно" />
        </el-form-item>
        <el-form-item label="Штрихкод (GTIN)">
          <el-input v-model="form.gtin" placeholder="4600000000017" maxlength="14" />
        </el-form-item>
        <el-form-item label="Единица измерения">
          <el-select v-model="form.unit" style="width: 100%">
            <el-option
              v-for="(title, code) in UNITS"
              :key="code"
              :label="title"
              :value="code"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="Категория">
          <el-select
            v-model="form.category_id"
            placeholder="Выберите категорию"
            style="width: 100%"
          >
            <el-option
              v-for="category in categories"
              :key="category.id"
              :label="category.name"
              :value="category.id"
            />
          </el-select>
        </el-form-item>
      </div>

      <el-form-item label="ВетИС">
        <el-select v-model="form.requires_vetis" style="width: 100%">
          <el-option label="Не требуется" :value="false" />
          <el-option label="Требуется ВСД" :value="true" />
        </el-select>
        <span class="hint">включайте для мяса, молочки и рыбы</span>
      </el-form-item>

      <el-alert
        v-if="!categories.length"
        type="warning"
        :closable="false"
        show-icon
        title="Нет доступных категорий"
        description="Создайте категорию в справочнике, иначе номенклатуру сохранить не получится."
      />
    </el-form>

    <template #footer>
      <el-button @click="open = false">Отмена</el-button>
      <el-button
        type="primary"
        :loading="saving"
        :disabled="!form.name.trim() || !form.category_id"
        @click="create"
      >
        Создать и выбрать
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import type { components } from "@md/api-client";

import { UNITS } from "~/utils/labels";

type NomenclatureOption = {
  id: string;
  name: string;
  sku: string;
  requires_vetis?: boolean;
};
type NomenclatureCategory = components["schemas"]["CategorySchema"];
type NomenclatureUnit = components["schemas"]["CreateNomenclatureSchema"]["unit"];

const emit = defineEmits<{ selected: [option: NomenclatureOption] }>();

const api = useApi();
const { can } = useCurrentUser();

const open = ref(false);
const saving = ref(false);
const error = ref("");
const categories = ref<NomenclatureCategory[]>([]);
const matches = ref<NomenclatureOption[]>([]);
const form = reactive({
  name: "",
  sku: "",
  gtin: "",
  unit: "kg" as NomenclatureUnit,
  category_id: "",
  requires_vetis: false,
});

function serverMessage(failure: unknown, fallback: string): string {
  const payload = failure as { message?: string } | undefined;

  return payload?.message ?? fallback;
}

async function loadCategories(): Promise<void> {
  if (categories.value.length || !can("category.read")) {
    return;
  }

  const { data, response } = await api.GET("/api/catalog/categories", {});
  if (response.ok && data) {
    categories.value = data;
  }
}

async function loadMatches(): Promise<void> {
  const name = form.name.trim();
  if (name.length < 2) {
    matches.value = [];
    return;
  }

  const { data, response } = await api.GET("/api/catalog/nomenclatures", {
    params: { query: { search: name, limit: 5 } },
  });

  if (response.ok && data) {
    matches.value = data.items;
  }
}

function show(prefillName = ""): void {
  error.value = "";
  form.name = prefillName.trim();
  form.sku = "";
  form.gtin = "";
  form.unit = "kg";
  form.requires_vetis = false;
  form.category_id = categories.value[0]?.id ?? "";
  matches.value = [];
  open.value = true;

  void loadCategories().then(() => {
    if (!form.category_id) {
      form.category_id = categories.value[0]?.id ?? "";
    }
  });
  void loadMatches();
}

function choose(option: NomenclatureOption): void {
  emit("selected", option);
  open.value = false;
}

async function create(): Promise<void> {
  saving.value = true;
  error.value = "";

  try {
    const name = form.name.trim();
    const created = await api.POST("/api/catalog/nomenclatures", {
      body: {
        name,
        sku: form.sku.trim() || null,
        gtin: form.gtin.trim() || null,
        unit: form.unit,
        category_id: form.category_id,
        requires_vetis: form.requires_vetis,
      },
    });

    if (!created.response.ok || !created.data) {
      throw new Error(
        serverMessage(
          created.error,
          `Не удалось создать номенклатуру: ${created.response.status}`,
        ),
      );
    }

    const createdId = (
      created.data as unknown as { nomenclature_id: string }
    ).nomenclature_id;
    const listed = await api.GET("/api/catalog/nomenclatures", {
      params: { query: { search: name, limit: 20 } },
    });
    const items: NomenclatureOption[] = listed.data?.items ?? [];
    const found = items.find((item) => item.id === createdId);

    emit(
      "selected",
      found ?? {
        id: createdId,
        name,
        sku: form.sku.trim(),
        requires_vetis: form.requires_vetis,
      },
    );
    matches.value = [];
    open.value = false;
  } catch (cause) {
    error.value =
      cause instanceof Error ? cause.message : "Ошибка создания номенклатуры";
  } finally {
    saving.value = false;
  }
}

defineExpose({ show });
</script>

<style scoped>
.dialog-alert {
  margin-bottom: 12px;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 16px;
}

.hint {
  font-size: 11px;
}

.quick-matches {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin: 0 0 12px;
}

.quick-match {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  padding: 4px 8px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
}
</style>
