<template>
  <div class="page">
    <h1 class="page__title">Склады</h1>
    <p class="page__subtitle">Показаны склады, на которые есть право просмотра</p>

    <ViewOnlyNotice view="inventory.warehouse.read" edit="inventory.warehouse.manage" />
    <div class="page__toolbar">
      <el-button
        v-if="canAll(CAN.warehouseCreate)"
        type="primary" @click="openCreate">
        Создать склад
      </el-button>
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
      <el-table-column prop="code" label="Код" width="180" />
      <el-table-column prop="name" label="Название" min-width="240" />
      <el-table-column label="Тип" width="200">
        <template #default="{ row }">{{ label(WAREHOUSE_TYPES, row.type) }}</template>
      </el-table-column>
      <el-table-column label="Организация" min-width="220">
        <template #default="{ row }">{{ orgUnitName(row.org_unit_id) }}</template>
      </el-table-column>
      <el-table-column label="Статус" width="130">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" effect="light">
            {{ row.is_active ? "активен" : "закрыт" }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column v-if="can('inventory.warehouse.manage')" width="130" align="right">
        <template #default="{ row }">
          <el-button text @click="openEdit(row as Warehouse)">Изменить</el-button>
        </template>
      </el-table-column>

      <template #empty>
        <el-empty description="Складов пока нет" />
      </template>
    </el-table>

    <el-dialog v-model="createOpen" title="Новый склад" width="640">
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="Подразделение">
          <el-select v-model="form.org_unit_id" placeholder="Выберите подразделение" style="width: 100%">
            <el-option
              v-for="unit in orgUnits"
              :key="unit.id"
              :label="unit.name"
              :value="unit.id"
            />
          </el-select>
        </el-form-item>

        <div class="form-grid">
          <el-form-item label="Код">
            <el-input v-model="form.code" placeholder="RAW-01" />
          </el-form-item>
          <el-form-item label="Название">
            <el-input v-model="form.name" placeholder="Склад сырья" />
          </el-form-item>
        </div>

        <el-form-item label="Назначение">
          <el-select v-model="form.type" style="width: 100%">
            <el-option
              v-for="(title, code) in WAREHOUSE_TYPES"
              :key="code"
              :label="title"
              :value="code"
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
          :disabled="!form.org_unit_id || !form.code || !form.name"
          @click="createWarehouse"
        >
          Создать
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editOpen" title="Изменить склад" width="560">
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="Название">
          <el-input v-model="editForm.name" />
        </el-form-item>

        <el-form-item label="Назначение">
          <el-select v-model="editForm.type" style="width: 100%">
            <el-option
              v-for="(title, code) in WAREHOUSE_TYPES"
              :key="code"
              :label="title"
              :value="code"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="В работе">
          <el-switch v-model="editForm.is_active" />
          <span class="hint">закрытый склад нельзя выбрать в новых документах</span>
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

import { CAN } from "~/utils/access";

definePageMeta({ permissions: CAN.warehouseCreate });
import type { components } from "@md/api-client";

type Warehouse = components["schemas"]["WarehouseSchema"];
type OrgUnit = components["schemas"]["OrgUnitSchema"];

const api = useApi();
const { can } = useCurrentUser();

const items = ref<Warehouse[]>([]);
const orgUnits = ref<OrgUnit[]>([]);
const pending = ref(false);
const error = ref("");
const notice = ref("");

const createOpen = ref(false);
const editOpen = ref(false);
const editError = ref("");
const editRow = ref<Warehouse | null>(null);
const editForm = reactive({
  name: "",
  type: "raw" as Warehouse["type"],
  is_active: true,
});
const saving = ref(false);
const createError = ref("");

const form = reactive({
  org_unit_id: "",
  code: "",
  name: "",
  type: "raw",
});

function orgUnitName(orgUnitId: string): string {
  return orgUnits.value.find((unit) => unit.id === orgUnitId)?.name ?? "—";
}

function reasonOf(status: number, fallback: string): string {
  if (status === 403) {
    return "Нет прав на это действие";
  }
  if (status === 409) {
    return "Склад с таким кодом уже есть";
  }
  if (status === 422) {
    return "Проверьте заполненные поля";
  }

  return `${fallback}: ${status}`;
}

async function loadOrgUnits(): Promise<void> {
  if (!can("org_unit.read")) {
    return;
  }

  const { data, response } = await api.GET("/api/business/org-units", {});
  if (response.ok && data) {
    orgUnits.value = data;
  }
}

async function load(): Promise<void> {
  pending.value = true;
  error.value = "";

  try {
    const { data, response } = await api.GET("/api/inventory/warehouses", {});
    if (!response.ok || !data) {
      throw new Error(reasonOf(response.status, "Не удалось загрузить"));
    }

    items.value = data;
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Ошибка загрузки";
    items.value = [];
  } finally {
    pending.value = false;
  }
}

function openCreate(): void {
  createError.value = "";
  notice.value = "";
  form.org_unit_id = orgUnits.value.find((unit) => unit.parent_id === null)?.id
    ?? orgUnits.value[0]?.id
    ?? "";
  form.code = "";
  form.name = "";
  form.type = "raw";
  createOpen.value = true;
}

async function createWarehouse(): Promise<void> {
  saving.value = true;
  createError.value = "";

  try {
    const { response } = await api.POST("/api/inventory/warehouses", {
      body: {
        org_unit_id: form.org_unit_id,
        code: form.code.trim(),
        name: form.name.trim(),
        type: form.type as Warehouse["type"],
      },
    });

    if (!response.ok) {
      throw new Error(reasonOf(response.status, "Не удалось создать склад"));
    }

    createOpen.value = false;
    notice.value = `Склад «${form.name.trim()}» создан`;
    await load();
  } catch (cause) {
    createError.value = cause instanceof Error ? cause.message : "Ошибка создания";
  } finally {
    saving.value = false;
  }
}

function openEdit(row: Warehouse): void {
  editRow.value = row;
  editError.value = "";
  notice.value = "";
  editForm.name = row.name;
  editForm.type = row.type;
  editForm.is_active = row.is_active;
  editOpen.value = true;
}


async function saveEdit(): Promise<void> {
  const row = editRow.value;
  if (!row) return;

  const body: Record<string, unknown> = {};
  if (editForm.name.trim() !== row.name) body.name = editForm.name.trim();
  if (editForm.type !== row.type) body.type = editForm.type;
  if (editForm.is_active !== row.is_active) body.is_active = editForm.is_active;

  if (!Object.keys(body).length) {
    editOpen.value = false;
    return;
  }

  saving.value = true;
  editError.value = "";

  try {
    const { response, error } = await api.PATCH(
      "/api/inventory/warehouses/{warehouse_id}",
      {
        params: { path: { warehouse_id: row.id } },
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
  await loadOrgUnits();
  await load();
});

const { scopeId } = useCurrentScope();
watch(scopeId, () => {
  void load();
});
</script>

<style scoped>
.page__error {
  margin-bottom: 16px;
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
