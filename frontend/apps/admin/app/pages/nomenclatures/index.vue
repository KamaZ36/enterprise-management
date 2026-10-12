<template>
  <div class="page">
    <h1 class="page__title">Номенклатура</h1>
    <p class="page__subtitle">Найдено: {{ total }}</p>

    <ViewOnlyNotice view="nomenclature.read" edit="nomenclature.update" />
    <div class="page__toolbar">
      <el-button v-if="canAll(CAN.nomenclatureCreate)" type="primary" @click="openCreate">
        Создать номенклатуру
      </el-button>
      <el-input
        v-model="search"
        placeholder="Название или артикул"
        clearable
        style="max-width: 320px"
        @keyup.enter="applySearch"
        @clear="applySearch"
      />
      <el-button @click="applySearch">Найти</el-button>
      <el-button :loading="pending" @click="load">Обновить</el-button>
    </div>

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

    <el-table v-loading="pending" :data="items" stripe border>
      <el-table-column prop="sku" label="Артикул" width="180" />
      <el-table-column prop="name" label="Название" min-width="260" />
      <el-table-column label="Тип" width="190">
        <template #default="{ row }">
          {{ label(NOMENCLATURE_TYPES, row.type) }}
        </template>
      </el-table-column>
      <el-table-column label="Ед." width="90">
        <template #default="{ row }">{{ label(UNITS, row.unit) }}</template>
      </el-table-column>
      <el-table-column label="Статус" width="120">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" effect="light">
            {{ row.is_active ? "в работе" : "закрыта" }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="category_name" label="Категория" min-width="200" />

      <el-table-column v-if="can('nomenclature.update')" width="130" align="right">
        <template #default="{ row }">
          <el-button text @click="openEdit(row as Nomenclature)">Изменить</el-button>
        </template>
      </el-table-column>

      <template #empty>
        <el-empty :description="search ? 'Ничего не найдено' : 'Номенклатуры пока нет'" />
      </template>
    </el-table>

    <el-pagination
      v-model:current-page="page"
      class="pager"
      layout="prev, pager, next, total"
      :page-size="PAGE_SIZE"
      :total="total"
      :disabled="pending"
    />

    <el-dialog v-model="createOpen" title="Новая номенклатура" width="640">
      <el-form label-position="top">
        <div class="form-grid">
          <el-form-item label="Артикул">
            <el-input v-model="form.sku" placeholder="BEEF-SHOULDER" />
          </el-form-item>
          <el-form-item label="Название">
            <el-input v-model="form.name" placeholder="Говядина лопатка" />
          </el-form-item>
          <el-form-item label="Тип">
            <el-select v-model="form.type" style="width: 100%">
              <el-option
                v-for="(title, code) in NOMENCLATURE_TYPES"
                :key="code"
                :label="title"
                :value="code"
              />
            </el-select>
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
        </div>

        <el-form-item label="Категория">
          <el-select v-model="form.category_id" placeholder="Выберите категорию" style="width: 100%">
            <el-option
              v-for="category in categories"
              :key="category.id"
              :label="category.name"
              :value="category.id"
            />
          </el-select>
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
          :disabled="!form.sku || !form.name || !form.category_id"
          @click="createNomenclature"
        >
          Создать
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editOpen" title="Изменить номенклатуру" width="640">
      <el-form label-position="top">
        <el-form-item label="Название">
          <el-input v-model="editForm.name" />
        </el-form-item>

        <div class="form-grid">
          <el-form-item label="Тип">
            <el-select v-model="editForm.type" style="width: 100%">
              <el-option
                v-for="(title, code) in NOMENCLATURE_TYPES"
                :key="code"
                :label="title"
                :value="code"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="Единица измерения">
            <el-select v-model="editForm.unit" style="width: 100%">
              <el-option
                v-for="(title, code) in UNITS"
                :key="code"
                :label="title"
                :value="code"
              />
            </el-select>
          </el-form-item>
        </div>

        <el-form-item label="Категория">
          <el-select v-model="editForm.category_id" style="width: 100%">
            <el-option
              v-for="category in categories"
              :key="category.id"
              :label="category.name"
              :value="category.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="В работе">
          <el-switch v-model="editForm.is_active" />
          <span class="hint">закрытая позиция остаётся в документах, но её нельзя выбрать в новых</span>
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

import { CAN } from "~/utils/access";

definePageMeta({ permissions: CAN.nomenclaturesOpen });
import type { components } from "@md/api-client";

type Nomenclature = components["schemas"]["NomenclatureSchema"];
type Category = components["schemas"]["CategorySchema"];

const PAGE_SIZE = 20;

const api = useApi();
const { can } = useCurrentUser();

const items = ref<Nomenclature[]>([]);
const categories = ref<Category[]>([]);
const total = ref(0);
const page = ref(1);
const search = ref("");
const applied = ref("");
const pending = ref(false);
const error = ref("");
const notice = ref("");

const createOpen = ref(false);
const editOpen = ref(false);
const editError = ref("");
const editRow = ref<Nomenclature | null>(null);
const editForm = reactive({
  name: "",
  category_id: "",
  unit: "kg" as Nomenclature["unit"],
  type: "raw_material" as Nomenclature["type"],
  is_active: true,
});
const saving = ref(false);
const createError = ref("");

const form = reactive({
  sku: "",
  name: "",
  type: "raw_material",
  unit: "kg",
  category_id: "",
});

function reasonOf(status: number, fallback: string): string {
  if (status === 403) {
    return "Нет прав на это действие";
  }
  if (status === 409) {
    return "Номенклатура с таким артикулом уже есть";
  }
  if (status === 422) {
    return "Проверьте заполненные поля";
  }

  return `${fallback}: ${status}`;
}

async function loadCategories(): Promise<void> {
  if (!can("category.read")) {
    return;
  }

  const { data, response } = await api.GET("/api/categories", {});
  if (response.ok && data) {
    categories.value = data;
  }
}

async function load(): Promise<void> {
  pending.value = true;
  error.value = "";

  try {
    const { data, response } = await api.GET("/api/nomenclatures", {
      params: {
        query: {
          search: applied.value || undefined,
          limit: PAGE_SIZE,
          offset: (page.value - 1) * PAGE_SIZE,
        },
      },
    });

    if (!response.ok || !data) {
      throw new Error(reasonOf(response.status, "Не удалось загрузить"));
    }

    items.value = data.items;
    total.value = data.total;
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Ошибка загрузки";
    items.value = [];
    total.value = 0;
  } finally {
    pending.value = false;
  }
}

function applySearch(): void {
  applied.value = search.value.trim();
  page.value = 1;
  load();
}

function openCreate(): void {
  createError.value = "";
  notice.value = "";
  form.sku = "";
  form.name = "";
  form.type = "raw_material";
  form.unit = "kg";
  form.category_id = categories.value[0]?.id ?? "";
  createOpen.value = true;
}

async function createNomenclature(): Promise<void> {
  saving.value = true;
  createError.value = "";

  try {
    const { response } = await api.POST("/api/nomenclatures", {
      body: {
        sku: form.sku.trim(),
        name: form.name.trim(),
        unit: form.unit as Nomenclature["unit"],
        type: form.type as Nomenclature["type"],
        category_id: form.category_id,
      },
    });

    if (!response.ok) {
      throw new Error(reasonOf(response.status, "Не удалось создать номенклатуру"));
    }

    createOpen.value = false;
    notice.value = `Номенклатура «${form.name.trim()}» создана`;
    await load();
  } catch (cause) {
    createError.value = cause instanceof Error ? cause.message : "Ошибка создания";
  } finally {
    saving.value = false;
  }
}

function openEdit(row: Nomenclature): void {
  editRow.value = row;
  editError.value = "";
  notice.value = "";
  editForm.name = row.name;
  editForm.category_id = row.category_id;
  editForm.unit = row.unit;
  editForm.type = row.type;
  editForm.is_active = row.is_active;
  editOpen.value = true;
}


async function saveEdit(): Promise<void> {
  const row = editRow.value;
  if (!row) {
    return;
  }

  const body: Record<string, unknown> = {};
  if (editForm.name.trim() !== row.name) {
    body.name = editForm.name.trim();
  }
  if (editForm.category_id !== row.category_id) {
    body.category_id = editForm.category_id;
  }
  if (editForm.unit !== row.unit) {
    body.unit = editForm.unit;
  }
  if (editForm.type !== row.type) {
    body.type = editForm.type;
  }
  if (editForm.is_active !== row.is_active) {
    body.is_active = editForm.is_active;
  }

  if (!Object.keys(body).length) {
    editOpen.value = false;
    return;
  }

  saving.value = true;
  editError.value = "";

  try {
    const { response, error } = await api.PATCH(
      "/api/nomenclatures/{nomenclature_id}",
      {
        params: { path: { nomenclature_id: row.id } },
        body: body as never,
      },
    );

    if (!response.ok) {
      const payload = error as { message?: string } | undefined;
      throw new Error(payload?.message ?? `Не удалось сохранить: ${response.status}`);
    }

    editOpen.value = false;
    notice.value = "Изменения сохранены";
    await load();
  } catch (cause) {
    editError.value = cause instanceof Error ? cause.message : "Ошибка сохранения";
  } finally {
    saving.value = false;
  }
}


onMounted(async () => {
  await loadCategories();
  await load();
});
watch(page, load);
</script>

<style scoped>
.page__error {
  margin-bottom: 16px;
}

.pager {
  margin-top: 18px;
  justify-content: flex-end;
}

.hint {
  margin-left: 10px;
  color: #909399;
  font-size: 12px;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 16px;
}
</style>
