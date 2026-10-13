<template>
  <div class="page">
    <h1 class="page__title">Организация</h1>
    <p class="page__subtitle">
      Структура компании в виде папок. Склады и права привязываются к подразделению.
    </p>

    <ViewOnlyNotice view="org_unit.read" edit="org_unit.update" />

    <el-alert
      v-if="notice"
      :title="notice"
      type="success"
      :closable="false"
      show-icon
      class="notice"
    />
    <el-alert
      v-if="error"
      :title="error"
      type="error"
      :closable="false"
      show-icon
      class="notice"
    />

    <div class="layout">
      <el-card class="panel" shadow="never">
        <div class="panel__head">
          <el-input
            v-model="filter"
            placeholder="Поиск подразделения"
            clearable
            size="small"
          />
        </div>

        <div class="panel__actions">
          <el-button
            v-if="can('org_unit.create')"
            type="primary"
            size="small"
            @click="openCreate"
          >
            Добавить
          </el-button>
          <el-button size="small" @click="toggleExpand">{{ expandAll ? "Свернуть" : "Развернуть" }}</el-button>
          <el-button size="small" :loading="pending" @click="load">Обновить</el-button>
        </div>

        <el-tree
          :key="treeKey"
          ref="treeRef"
          v-loading="pending"
          class="tree"
          :data="tree"
          node-key="id"
          :props="{ label: 'name', children: 'children' }"
          :default-expand-all="expandAll"
          :expand-on-click-node="false"
          highlight-current
          :filter-node-method="filterNode as never"
          @node-click="select"
        >
          <template #default="{ node, data }">
            <span class="node">
              <el-icon class="node__icon">
                <FolderOpened v-if="node.expanded && data.children.length" />
                <Folder v-else />
              </el-icon>
              <span class="node__name">{{ data.name }}</span>
              <span class="node__code mono">{{ data.code }}</span>
              <el-tag size="small" effect="plain">{{ typeLabel(data.type) }}</el-tag>
              <el-tag v-if="!data.is_active" size="small" type="info" effect="light">
                закрыто
              </el-tag>
            </span>
          </template>
        </el-tree>

        <el-empty v-if="!tree.length && !pending" description="Структура пуста" :image-size="80" />
      </el-card>

      <el-card class="panel" shadow="never">
        <template v-if="selected">
          <div class="panel__head">
            <div class="panel__title">{{ selected.name }}</div>
            <el-button v-if="can('org_unit.update')" text @click="openEdit">
              Изменить
            </el-button>
          </div>

          <el-descriptions :column="1" border>
            <el-descriptions-item label="Код">
              <span class="mono">{{ selected.code }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="Тип">{{ typeLabel(selected.type) }}</el-descriptions-item>
            <el-descriptions-item label="Родитель">
              {{ parentName(selected.parent_id) }}
            </el-descriptions-item>
            <el-descriptions-item label="Адрес">{{ selected.address ?? "—" }}</el-descriptions-item>
            <el-descriptions-item label="Телефон">
              {{ selected.phone_number ?? "—" }}
            </el-descriptions-item>
            <el-descriptions-item label="Статус">
              <el-tag :type="selected.is_active ? 'success' : 'info'" effect="light">
                {{ selected.is_active ? "активно" : "закрыто" }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="Вложено">
              {{ childrenOf(selected.id).length }}
            </el-descriptions-item>
          </el-descriptions>

          <div class="warehouses">
            <div class="warehouses__title">Склады подразделения</div>
            <div v-if="warehousesOf(selected.id).length" class="warehouses__list">
              <el-tag
                v-for="warehouse in warehousesOf(selected.id)"
                :key="warehouse.id"
                effect="light"
              >
                {{ warehouse.name }} · {{ label(WAREHOUSE_TYPES, warehouse.type) }}
              </el-tag>
            </div>
            <div v-else class="muted">Складов нет</div>
          </div>
        </template>

        <el-empty v-else description="Выберите подразделение в дереве" :image-size="80" />
      </el-card>
    </div>

    <el-dialog v-model="editOpen" title="Изменить подразделение" width="640">
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="Название">
          <el-input v-model="editForm.name" />
        </el-form-item>

        <el-form-item label="Адрес">
          <el-input v-model="editForm.address" />
        </el-form-item>

        <el-form-item label="Телефон">
          <el-input v-model="editForm.phone_number" />
        </el-form-item>

        <el-form-item label="Статус">
          <el-switch v-model="editForm.is_active" />
          <span class="hint">закрытое подразделение остаётся в структуре, но новые склады в нём не заводят</span>
        </el-form-item>

        <el-alert v-if="editError" :title="editError" type="error" :closable="false" show-icon />
      </el-form>

      <template #footer>
        <el-button @click="editOpen = false">Отмена</el-button>
        <el-button type="primary" :loading="saving" @click="saveEdit">Сохранить</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="createOpen" title="Новое подразделение" width="640">
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="Родительская папка">
          <el-select v-model="form.parent_id" placeholder="Выберите родителя" style="width: 100%">
            <el-option
              v-for="unit in units"
              :key="unit.id"
              :label="unit.name"
              :value="unit.id"
            />
          </el-select>
        </el-form-item>

        <div class="form-grid">
          <el-form-item label="Тип">
            <el-select v-model="form.type" style="width: 100%">
              <el-option
                v-for="(title, code) in ORG_UNIT_TYPES"
                :key="code"
                :label="title"
                :value="code"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="Код">
            <el-input v-model="form.code" placeholder="SHOP-01" />
          </el-form-item>
          <el-form-item label="Название">
            <el-input v-model="form.name" placeholder="Магазин на Ленина" />
          </el-form-item>
          <el-form-item label="Телефон">
            <el-input v-model="form.phone_number" />
          </el-form-item>
        </div>

        <el-form-item label="Адрес">
          <el-input v-model="form.address" />
        </el-form-item>

        <el-alert v-if="createError" :title="createError" type="error" :closable="false" show-icon />
      </el-form>

      <template #footer>
        <el-button @click="createOpen = false">Отмена</el-button>
        <el-button
          type="primary"
          :loading="saving"
          :disabled="!form.parent_id || !form.code || !form.name"
          @click="createUnit"
        >
          Создать
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">

import { CAN } from "~/utils/access";

definePageMeta({ permissions: CAN.orgUnitsOpen });
import { Folder, FolderOpened } from "@element-plus/icons-vue";
import type { components } from "@md/api-client";

type OrgUnit = components["schemas"]["OrgUnitSchema"];
type Warehouse = components["schemas"]["WarehouseSchema"];
type OrgUnitNode = OrgUnit & { children: OrgUnitNode[] };

const ORG_UNIT_TYPES: Record<string, string> = {
  root: "Компания",
  production: "Производство",
  group: "Группа",
  cafe: "Кафе",
  shop: "Магазин",
};

const api = useApi();
const { can } = useCurrentUser();

const units = ref<OrgUnit[]>([]);
const warehouses = ref<Warehouse[]>([]);
const selected = ref<OrgUnit | null>(null);
const pending = ref(false);
const error = ref("");
const notice = ref("");

const filter = ref("");
const expandAll = ref(true);
const treeKey = ref(0);
const treeRef = ref();

const createOpen = ref(false);
const editOpen = ref(false);
const editError = ref("");
const editForm = reactive({
  name: "",
  address: "",
  phone_number: "",
  is_active: true,
});
const saving = ref(false);
const createError = ref("");

const form = reactive({
  parent_id: "",
  type: "group",
  code: "",
  name: "",
  address: "",
  phone_number: "",
});

const tree = computed<OrgUnitNode[]>(() => {
  const nodes = new Map<string, OrgUnitNode>();
  for (const unit of units.value) {
    nodes.set(unit.id, { ...unit, children: [] });
  }

  const roots: OrgUnitNode[] = [];
  for (const node of nodes.values()) {
    const parent = node.parent_id ? nodes.get(node.parent_id) : undefined;
    if (parent) {
      parent.children.push(node);
    } else {
      roots.push(node);
    }
  }

  return roots;
});

function typeLabel(code: string): string {
  return ORG_UNIT_TYPES[code] ?? code;
}

function parentName(parentId: string | null): string {
  if (!parentId) {
    return "—";
  }

  return units.value.find((unit) => unit.id === parentId)?.name ?? "—";
}

function childrenOf(unitId: string): OrgUnit[] {
  return units.value.filter((unit) => unit.parent_id === unitId);
}

function warehousesOf(unitId: string): Warehouse[] {
  return warehouses.value.filter((warehouse) => warehouse.org_unit_id === unitId);
}

function filterNode(value: string, data: OrgUnitNode): boolean {
  if (!value) {
    return true;
  }

  const needle = value.toLowerCase();

  return (
    data.name.toLowerCase().includes(needle) ||
    data.code.toLowerCase().includes(needle)
  );
}

function toggleExpand(): void {
  expandAll.value = !expandAll.value;
  treeKey.value += 1;
}

function select(data: OrgUnit): void {
  selected.value = data;
}

function reasonOf(status: number, fallback: string): string {
  if (status === 403) {
    return "Нет прав на это действие";
  }
  if (status === 409) {
    return "Подразделение с таким кодом уже есть";
  }
  if (status === 422) {
    return "Проверьте заполненные поля";
  }

  return `${fallback}: ${status}`;
}

async function load(): Promise<void> {
  pending.value = true;
  error.value = "";

  try {
    const { data, response } = await api.GET("/api/business/org-units", {});
    if (!response.ok || !data) {
      throw new Error(reasonOf(response.status, "Не удалось загрузить структуру"));
    }

    units.value = data;

    if (selected.value) {
      selected.value = data.find((unit) => unit.id === selected.value?.id) ?? null;
    }
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Ошибка загрузки";
    units.value = [];
  } finally {
    pending.value = false;
  }
}

async function loadWarehouses(): Promise<void> {
  if (!canAll(CAN.warehouseRead)) {
    return;
  }

  const { data, response } = await api.GET("/api/inventory/warehouses", {});
  if (response.ok && data) {
    warehouses.value = data;
  }
}

function openCreate(): void {
  createError.value = "";
  notice.value = "";
  form.parent_id = selected.value?.id ?? tree.value[0]?.id ?? "";
  form.type = "group";
  form.code = "";
  form.name = "";
  form.address = "";
  form.phone_number = "";
  createOpen.value = true;
}

async function createUnit(): Promise<void> {
  saving.value = true;
  createError.value = "";

  try {
    const { response } = await api.POST("/api/business/org-units", {
      body: {
        parent_id: form.parent_id,
        type: form.type as OrgUnit["type"],
        code: form.code.trim(),
        name: form.name.trim(),
        address: form.address.trim() || null,
        phone_number: form.phone_number.trim() || null,
      },
    });

    if (!response.ok) {
      throw new Error(reasonOf(response.status, "Не удалось создать подразделение"));
    }

    createOpen.value = false;
    notice.value = `Подразделение «${form.name.trim()}» создано`;
    await load();
    treeRef.value?.setCurrentKey(form.parent_id);
  } catch (cause) {
    createError.value = cause instanceof Error ? cause.message : "Ошибка создания";
  } finally {
    saving.value = false;
  }
}

watch(filter, (value) => {
  treeRef.value?.filter(value);
});

function openEdit(): void {
  const current = selected.value;
  if (!current) {
    return;
  }

  editError.value = "";
  notice.value = "";
  editForm.name = current.name;
  editForm.address = current.address ?? "";
  editForm.phone_number = current.phone_number ?? "";
  editForm.is_active = current.is_active;
  editOpen.value = true;
}


async function saveEdit(): Promise<void> {
  const current = selected.value;
  if (!current) {
    return;
  }

  const body: Record<string, unknown> = {};
  if (editForm.name.trim() !== current.name) {
    body.name = editForm.name.trim();
  }
  if (editForm.address.trim() !== (current.address ?? "")) {
    body.address = editForm.address.trim() || null;
  }
  if (editForm.phone_number.trim() !== (current.phone_number ?? "")) {
    body.phone_number = editForm.phone_number.trim() || null;
  }
  if (editForm.is_active !== current.is_active) {
    body.is_active = editForm.is_active;
  }

  if (!Object.keys(body).length) {
    editOpen.value = false;
    return;
  }

  saving.value = true;
  editError.value = "";

  try {
    const { response, error: failure } = await api.PATCH(
      "/api/business/org-units/{org_unit_id}",
      {
        params: { path: { org_unit_id: current.id } },
        body: body as never,
      },
    );

    if (!response.ok) {
      const payload = failure as { message?: string } | undefined;
      throw new Error(
        payload?.message ?? `Не удалось сохранить: ${response.status}`,
      );
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
  await load();
  await loadWarehouses();
});
</script>

<style scoped>
.notice {
  margin-bottom: 16px;
}

.layout {
  display: grid;
  grid-template-columns: minmax(420px, 1fr) minmax(320px, 420px);
  gap: 16px;
  align-items: start;
}

.panel {
  border-radius: 10px;
}

.panel__head {
  margin-bottom: 10px;
}

.panel__actions {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.panel__title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 12px;
}

.tree {
  background: transparent;
}

.node {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding-right: 8px;
}

.node__icon {
  color: #b8860b;
}

.node__name {
  font-weight: 500;
}

.node__code {
  color: #909399;
}

.warehouses {
  margin-top: 18px;
}

.warehouses__title {
  font-weight: 600;
  font-size: 13px;
  margin-bottom: 8px;
}

.warehouses__list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 16px;
}
</style>
