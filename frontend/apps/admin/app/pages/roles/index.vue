<template>
  <div class="page">
    <h1 class="page__title">Роли</h1>
    <p class="page__subtitle">
      Роль — это набор прав. Сотруднику роль выдаётся в его карточке.
    </p>

    <div class="page__toolbar">
      <el-button v-if="can('staff.role.manage')" type="primary" @click="openCreate">
        Создать роль
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
      <el-table-column label="Название" min-width="240">
        <template #default="{ row }">
          <div>{{ row.name }}</div>
          <div v-if="row.description" class="hint">{{ row.description }}</div>
        </template>
      </el-table-column>
      <el-table-column prop="code" label="Код" width="200">
        <template #default="{ row }">
          <span class="mono">{{ row.code }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="level" label="Уровень" width="100" />
      <el-table-column label="Права" width="110">
        <template #default="{ row }">
          <el-tag v-if="row.is_wildcard" type="danger" effect="light">все</el-tag>
          <span v-else>{{ row.permission_codes.length }}</span>
        </template>
      </el-table-column>
      <el-table-column label="Назначаемая" width="140">
        <template #default="{ row }">
          <el-tag :type="row.is_assignable ? 'success' : 'info'" effect="light">
            {{ row.is_assignable ? "да" : "нет" }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="Системная" width="130">
        <template #default="{ row }">{{ row.is_system ? "да" : "—" }}</template>
      </el-table-column>
      <el-table-column v-if="can('staff.role.manage')" width="130" align="right">
        <template #default="{ row }">
          <el-button
            v-if="!row.is_system"
            text
            :disabled="busy"
            @click="openEdit(row as Role)"
          >
            Изменить
          </el-button>
          <el-popconfirm
            title="Удалить роль?"
            confirm-button-text="Удалить"
            cancel-button-text="Отмена"
            @confirm="removeRole(row as Role)"
          >
            <template #reference>
              <el-button type="danger" text :disabled="row.is_system || busy">
                Удалить
              </el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>

      <template #empty>
        <el-empty description="Ролей пока нет" />
      </template>
    </el-table>

    <el-dialog
      v-model="createOpen"
      :title="editId ? 'Изменить роль' : 'Новая роль'"
      width="720"
    >
      <el-form label-position="top">
        <div class="form-grid">
          <el-form-item label="Название">
            <el-input v-model="form.name" placeholder="Заведующий складом" />
          </el-form-item>
          <el-form-item label="Код">
            <el-input
              v-model="form.code"
              placeholder="WAREHOUSE_MANAGER"
              :disabled="Boolean(editId)"
            />
          </el-form-item>
          <el-form-item label="Уровень">
            <el-input-number v-model="form.level" :min="0" :max="1000" style="width: 100%" />
          </el-form-item>
          <el-form-item label="Назначаемая">
            <el-switch v-model="form.is_assignable" />
          </el-form-item>
        </div>

        <el-form-item label="Описание">
          <el-input v-model="form.description" />
        </el-form-item>

        <el-form-item label="Все права сразу">
          <el-switch v-model="form.is_wildcard" :disabled="Boolean(editId)" />
          <span class="hint">
            wildcard-роль получает и те права, которые появятся в системе позже
          </span>
        </el-form-item>

        <div v-if="!form.is_wildcard" class="permissions">
          <div class="permissions__title">Права ({{ selected.length }})</div>

          <div v-for="group in groups" :key="group.title" class="group">
            <div class="group__head">
              <span class="group__title">{{ group.title }}</span>
              <el-button text size="small" @click="toggleGroup(group)">
                {{ groupSelected(group) ? "снять все" : "выбрать все" }}
              </el-button>
            </div>

            <el-checkbox-group v-model="selected">
              <el-checkbox
                v-for="permission in group.items"
                :key="permission.code"
                :value="permission.code"
                class="group__item"
              >
                {{ permission.description }}
                <span class="mono hint">{{ permission.code }}</span>
              </el-checkbox>
            </el-checkbox-group>
          </div>
        </div>

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
        <el-button type="primary" :loading="saving" @click="saveRole">
          {{ editId ? "Сохранить" : "Создать" }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">

import { CAN } from "~/utils/access";

definePageMeta({ permissions: CAN.rolesOpen });
import type { components } from "@md/api-client";

type Role = components["schemas"]["RoleSchema"];
type Permission = components["schemas"]["PermissionSchema"];

const GROUP_TITLES: Record<string, string> = {
  staff: "Сотрудники и доступы",
  inventory: "Склад",
  nomenclature: "Номенклатура",
  category: "Категории",
  price: "Цены",
  price_list: "Прайс-листы",
  org_unit: "Организация",
};

const GROUP_ORDER = [
  "Сотрудники и доступы",
  "Склад",
  "Номенклатура",
  "Категории",
  "Цены",
  "Прайс-листы",
  "Организация",
  "Прочее",
];

const api = useApi();
const { can } = useCurrentUser();

const items = ref<Role[]>([]);
const permissions = ref<Permission[]>([]);
const pending = ref(false);
const error = ref("");
const notice = ref("");

const createOpen = ref(false);
const editId = ref("");
const busy = ref(false);
const saving = ref(false);
const createError = ref("");
const selected = ref<string[]>([]);

const form = reactive({
  name: "",
  code: "",
  description: "",
  level: 10,
  is_assignable: true,
  is_wildcard: false,
});

const groups = computed(() => {
  const byTitle = new Map<string, Permission[]>();

  for (const permission of permissions.value) {
    const prefix = permission.code.split(".")[0] ?? "";
    const title = GROUP_TITLES[prefix] ?? "Прочее";
    byTitle.set(title, [...(byTitle.get(title) ?? []), permission]);
  }

  return [...byTitle.entries()]
    .map(([title, items]) => ({ title, items }))
    .sort((left, right) => {
      const leftIndex = GROUP_ORDER.indexOf(left.title);
      const rightIndex = GROUP_ORDER.indexOf(right.title);

      return (leftIndex < 0 ? 99 : leftIndex) - (rightIndex < 0 ? 99 : rightIndex);
    });
});

function groupSelected(group: { items: Permission[] }): boolean {
  return group.items.every((permission) => selected.value.includes(permission.code));
}

function toggleGroup(group: { items: Permission[] }): void {
  const codes = group.items.map((permission) => permission.code);

  selected.value = groupSelected(group)
    ? selected.value.filter((code) => !codes.includes(code))
    : [...new Set([...selected.value, ...codes])];
}

function openEdit(role: Role): void {
  createError.value = "";
  notice.value = "";
  editId.value = role.id;
  form.name = role.name;
  form.code = role.code;
  form.description = role.description ?? "";
  form.level = role.level;
  form.is_assignable = role.is_assignable;
  form.is_wildcard = role.is_wildcard;
  selected.value = [...role.permission_codes];
  createOpen.value = true;
}


watch(createOpen, (open) => {
  if (!open) {
    editId.value = "";
    return;
  }

  if (editId.value) {
    return;
  }

  form.name = "";
  form.code = "";
  form.description = "";
  form.level = 10;
  form.is_assignable = true;
  form.is_wildcard = false;
  selected.value = [];
});


async function saveRole(): Promise<void> {
  if (!editId.value) {
    await createRole();
    return;
  }

  saving.value = true;
  createError.value = "";

  try {
    const { response, error: failure } = await api.PATCH(
      "/api/employees/roles/{role_id}",
      {
        params: { path: { role_id: editId.value } },
        body: {
          name: form.name.trim(),
          description: form.description.trim() || null,
          level: form.level,
          ...(form.is_wildcard ? {} : { permission_codes: selected.value }),
        },
      },
    );

    if (!response.ok) {
      const payload = failure as { message?: string } | undefined;
      throw new Error(
        payload?.message ?? `Не удалось сохранить: ${response.status}`,
      );
    }

    createOpen.value = false;
    notice.value = "Роль изменена";
    await load();
  } catch (cause) {
    createError.value = cause instanceof Error ? cause.message : "Ошибка сохранения";
  } finally {
    saving.value = false;
  }
}


function reasonOf(status: number, fallback: string): string {
  if (status === 403) {
    return "Нет прав на это действие";
  }
  if (status === 409) {
    return "Роль с таким кодом уже есть, либо её нельзя удалить: она системная или выдана сотрудникам";
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
    const [rolesResponse, permissionsResponse] = await Promise.all([
      api.GET("/api/employees/roles", {}),
      api.GET("/api/permissions", {}),
    ]);

    if (!rolesResponse.response.ok || !rolesResponse.data) {
      throw new Error(reasonOf(rolesResponse.response.status, "Не удалось загрузить роли"));
    }

    items.value = rolesResponse.data;

    if (permissionsResponse.response.ok && permissionsResponse.data) {
      permissions.value = permissionsResponse.data;
    }
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
  selected.value = [];
  form.name = "";
  form.code = "";
  form.description = "";
  form.level = 10;
  form.is_assignable = true;
  form.is_wildcard = false;
  createOpen.value = true;
}

async function removeRole(role: Role): Promise<void> {
  busy.value = true;
  error.value = "";
  notice.value = "";

  try {
    const { response } = await api.DELETE("/api/employees/roles/{role_id}", {
      params: { path: { role_id: role.id } },
    });

    if (!response.ok) {
      throw new Error(reasonOf(response.status, "Не удалось удалить роль"));
    }

    notice.value = `Роль «${role.name}» удалена`;
    await load();
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Ошибка удаления";
  } finally {
    busy.value = false;
  }
}


async function createRole(): Promise<void> {
  saving.value = true;
  createError.value = "";

  try {
    const { response } = await api.POST("/api/employees/roles", {
      body: {
        name: form.name.trim(),
        code: form.code.trim(),
        description: form.description.trim() || null,
        level: form.level,
        is_system: false,
        is_assignable: form.is_assignable,
        is_wildcard: form.is_wildcard,
        permission_codes: form.is_wildcard ? [] : selected.value,
        grantable_role_ids: [],
      },
    });

    if (!response.ok) {
      throw new Error(reasonOf(response.status, "Не удалось создать роль"));
    }

    createOpen.value = false;
    notice.value = `Роль «${form.name.trim()}» создана — её можно назначить в карточке сотрудника`;
    await load();
  } catch (cause) {
    createError.value = cause instanceof Error ? cause.message : "Ошибка создания роли";
  } finally {
    saving.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
.page__error {
  margin-bottom: 16px;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 16px;
}

.hint {
  margin-left: 10px;
  color: #909399;
  font-size: 12px;
}

.permissions {
  border: 1px solid var(--md-border);
  border-radius: 8px;
  padding: 12px 16px 16px;
  max-height: 380px;
  overflow-y: auto;
}

.permissions__title {
  font-weight: 600;
  margin-bottom: 12px;
}

.group {
  margin-bottom: 14px;
}

.group__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--md-border);
  margin-bottom: 8px;
}

.group__title {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #7f1d1d;
  font-weight: 600;
}

.group__item {
  display: flex;
  align-items: center;
  width: 100%;
  margin-right: 0;
  height: 26px;
}
</style>
