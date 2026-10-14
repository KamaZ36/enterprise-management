<template>
  <div class="page">
    <h1 class="page__title">Категории</h1>
    <p class="page__subtitle">Группы номенклатуры: мясо, птица, специи, упаковка</p>

    <ViewOnlyNotice view="category.read" edit="category.update" />

    <div class="page__toolbar">
      <el-button v-if="can('category.create')" type="primary" @click="openCreate">
        Новая категория
      </el-button>
      <el-input
        v-model="filter"
        placeholder="Фильтр по названию"
        style="width: 280px"
        clearable
      />
    </div>

    <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon class="page__error" />
    <el-alert v-if="notice" :title="notice" type="success" :closable="false" show-icon class="page__error" />

    <el-table v-loading="pending" :data="visible" empty-text="Категорий пока нет" class="page__table">
      <el-table-column prop="name" label="Название" min-width="280" />
      <el-table-column prop="sort_order" label="Порядок" width="110" align="center" />
      <el-table-column label="Родитель" min-width="220">
        <template #default="{ row }">{{ parentName(row.parent_id) }}</template>
      </el-table-column>
      <el-table-column v-if="can('category.update')" width="140" align="right">
        <template #default="{ row }">
          <el-button text @click="openEdit(row as Category)">Изменить</el-button>
        </template>
      </el-table-column>

      <template #empty>
        <el-empty description="Категорий пока нет" />
      </template>
    </el-table>

    <el-dialog v-model="createOpen" title="Новая категория" width="520">
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="Название">
          <el-input v-model="form.name" placeholder="Мясо и птица" />
        </el-form-item>
        <el-form-item label="Порядок">
          <el-input-number v-model="form.sort_order" :min="0" :max="9999" style="width: 100%" />
          <span class="hint">меньше — выше: и в справочнике, и в меню кафе</span>
        </el-form-item>
        <el-alert v-if="createError" :title="createError" type="error" :closable="false" show-icon />
      </el-form>

      <template #footer>
        <el-button @click="createOpen = false">Отмена</el-button>
        <el-button type="primary" :loading="saving" :disabled="!form.name.trim()" @click="save">
          Создать
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editOpen" title="Изменить категорию" width="520">
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="Название">
          <el-input v-model="editName" />
        </el-form-item>
        <el-form-item label="Порядок">
          <el-input-number v-model="editSortOrder" :min="0" :max="9999" style="width: 100%" />
          <span class="hint">меньше — выше: и в справочнике, и в меню кафе</span>
        </el-form-item>
        <el-alert v-if="editError" :title="editError" type="error" :closable="false" show-icon />
      </el-form>

      <template #footer>
        <el-button @click="editOpen = false">Отмена</el-button>
        <el-button type="primary" :loading="saving" @click="saveEdit">Сохранить</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">

definePageMeta({ permissions: ["category.read"] });
import type { components } from "@md/api-client";

type Category = components["schemas"]["CategorySchema"];

const api = useApi();
const { can } = useCurrentUser();

const categories = ref<Category[]>([]);
const pending = ref(false);
const saving = ref(false);
const error = ref("");
const notice = ref("");
const filter = ref("");
const createOpen = ref(false);
const createError = ref("");
const editOpen = ref(false);
const editError = ref("");
const editRow = ref<Category | null>(null);
const editName = ref("");
const editSortOrder = ref(0);

const form = reactive({ name: "", sort_order: 0 });

const visible = computed(() => {
  const needle = filter.value.trim().toLowerCase();
  if (!needle) {
    return categories.value;
  }

  return categories.value.filter((item) => item.name.toLowerCase().includes(needle));
});

function parentName(parentId: string | null): string {
  if (!parentId) {
    return "—";
  }

  return categories.value.find((item) => item.id === parentId)?.name ?? "—";
}

async function load(): Promise<void> {
  pending.value = true;
  error.value = "";

  try {
    const { data, response } = await api.GET("/api/catalog/categories", {});

    if (!response.ok || !data) {
      throw new Error(`Не удалось загрузить категории: ${response.status}`);
    }

    categories.value = data;
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Ошибка загрузки";
  } finally {
    pending.value = false;
  }
}

function openCreate(): void {
  createError.value = "";
  notice.value = "";
  form.name = "";

  form.sort_order =
    categories.value.reduce((max, item) => Math.max(max, item.sort_order), 0) + 10;
  createOpen.value = true;
}

async function save(): Promise<void> {
  saving.value = true;
  createError.value = "";

  try {
    const { response, error: failure } = await api.POST("/api/catalog/categories", {
      body: {
        name: form.name.trim(),
        parent_id: null,
        sort_order: form.sort_order,
      },
    });

    if (!response.ok) {
      const payload = failure as { message?: string } | undefined;
      throw new Error(payload?.message ?? `Не удалось создать: ${response.status}`);
    }

    createOpen.value = false;
    notice.value = "Категория создана";
    await load();
  } catch (cause) {
    createError.value = cause instanceof Error ? cause.message : "Ошибка сохранения";
  } finally {
    saving.value = false;
  }
}

function openEdit(row: Category): void {
  editError.value = "";
  notice.value = "";
  editRow.value = row;
  editName.value = row.name;
  editSortOrder.value = row.sort_order;
  editOpen.value = true;
}

async function saveEdit(): Promise<void> {
  const row = editRow.value;
  if (!row) {
    return;
  }

  saving.value = true;
  editError.value = "";

  try {
    const { response, error: failure } = await api.PATCH("/api/catalog/categories/{category_id}", {
      params: { path: { category_id: row.id } },
      body: { name: editName.value.trim(), sort_order: editSortOrder.value },
    });

    if (!response.ok) {
      const payload = failure as { message?: string } | undefined;
      throw new Error(payload?.message ?? `Не удалось сохранить: ${response.status}`);
    }

    editOpen.value = false;
    notice.value = "Категория переименована";
    await load();
  } catch (cause) {
    editError.value = cause instanceof Error ? cause.message : "Ошибка сохранения";
  } finally {
    saving.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
.page__error {
  margin-bottom: 12px;
}

.page__table {
  margin-top: 4px;
}

.hint {
  margin-left: 10px;
  color: #909399;
  font-size: 12px;
}
</style>
