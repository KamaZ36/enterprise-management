<template>
  <div class="page">
    <NuxtLink to="/staff/employees" class="back">← К списку сотрудников</NuxtLink>

    <el-skeleton v-if="pending" :rows="8" animated class="card" />

    <el-alert
      v-else-if="error"
      :title="error"
      type="error"
      :closable="false"
      show-icon
    />

    <template v-else-if="employee">
      <h1 class="page__title">{{ fullName(employee) }}</h1>
      <p class="page__subtitle">{{ employee.position }}</p>

    <ViewOnlyNotice view="staff.employee.read" edit="staff.employee.manage" />

      <div class="card-actions">
        <el-button v-if="can('staff.employee.manage')" @click="openEdit">Изменить</el-button>
        <el-popconfirm
          v-if="can('staff.employee.manage')"
          title="Выдать сотруднику новый пароль? Текущий перестанет работать сразу."
          confirm-button-text="Выдать"
          cancel-button-text="Отмена"
          @confirm="resetPassword"
        >
          <template #reference>
            <el-button text :disabled="busy">Сбросить пароль</el-button>
          </template>
        </el-popconfirm>
        <el-button
          v-if="can('staff.employee.manage')"
          :type="employee.is_active ? 'danger' : 'success'"
          text
          :disabled="busy"
          @click="toggleActive"
        >
          {{ employee.is_active ? "Уволить" : "Вернуть в работу" }}
        </el-button>
      </div>

      <el-descriptions :column="2" border class="card">
        <el-descriptions-item label="Статус">
          <el-tag :type="employee.is_active ? 'success' : 'info'" effect="light">
            {{ employee.is_active ? "работает" : "уволен" }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="Работает в">
          {{ employee.org_unit_name ?? orgUnitName(employee.org_unit_id) }}
        </el-descriptions-item>
        <el-descriptions-item label="Телефон">
          {{ employee.phone_number ?? "—" }}
        </el-descriptions-item>
        <el-descriptions-item label="Принят">
          {{ formatDate(employee.hired_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="Уволен">
          {{ formatDate(employee.dismissed_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="Идентификатор пользователя">
          <span class="mono">{{ employee.user_id }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="Идентификатор сотрудника">
          <span class="mono">{{ employee.id }}</span>
        </el-descriptions-item>
      </el-descriptions>

      <h2 class="section__title">Роли и доступы</h2>

      <el-alert
        v-if="notice"
        :title="notice"
        type="success"
        :closable="false"
        show-icon
        class="card"
      />
      <el-alert
        v-if="failure"
        :title="failure"
        type="error"
        :closable="false"
        show-icon
        class="card"
      />

      <el-table v-loading="rolesPending" :data="roles" stripe border>
        <el-table-column prop="role_name" label="Роль" min-width="220" />
        <el-table-column label="Где действует" min-width="200">
          <template #default="{ row }">
            {{ orgUnitName(row.org_unit_id) }}
          </template>
        </el-table-column>
        <el-table-column label="С подчинёнными" width="160">
          <template #default="{ row }">
            {{ row.include_descendants ? "да" : "нет" }}
          </template>
        </el-table-column>
        <el-table-column label="Назначена" width="140">
          <template #default="{ row }">{{ formatDate(row.assigned_at) }}</template>
        </el-table-column>
        <el-table-column v-if="can('staff.role.assign')" width="130" align="right">
          <template #default="{ row }">
            <el-popconfirm
              title="Отозвать роль?"
              confirm-button-text="Отозвать"
              cancel-button-text="Отмена"
              @confirm="revoke(row.id)"
            >
              <template #reference>
                <el-button type="danger" text :disabled="busy">Отозвать</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>

        <template #empty>
          <el-empty description="Ролей не назначено — сотрудник пока ничего не видит" />
        </template>
      </el-table>

      <el-card v-if="can('staff.role.assign')" class="card assign" shadow="never">
        <div class="assign__title">Назначить роль</div>

        <el-alert
          v-if="!assignableRoles.length"
          type="info"
          :closable="false"
          show-icon
          title="Нет ролей, доступных для назначения"
          description="В справочнике только системная роль, а её выдают не назначением. Нужен экран создания ролей."
        />

        <el-form v-else label-position="top" class="assign__form">
          <el-form-item label="Роль">
            <el-select v-model="form.role_id" placeholder="Выберите роль" style="width: 100%">
              <el-option
                v-for="role in assignableRoles"
                :key="role.id"
                :label="role.name"
                :value="role.id"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="Организация">
            <el-select
              v-model="form.org_unit_id"
              placeholder="Выберите подразделение"
              style="width: 100%"
            >
              <el-option
                v-for="unit in orgUnits"
                :key="unit.id"
                :label="unit.name"
                :value="unit.id"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="Область действия">
            <el-checkbox v-model="form.include_descendants">
              включая подчинённые подразделения
            </el-checkbox>
          </el-form-item>

          <el-button
            type="primary"
            :loading="busy"
            :disabled="!form.role_id || !form.org_unit_id"
            @click="assign"
          >
            Назначить
          </el-button>
        </el-form>
      </el-card>
    </template>
    <el-dialog v-model="resetOpen" title="Новый пароль" width="480">
      <el-alert
        type="warning"
        :closable="false"
        show-icon
        title="Пароль показывается один раз"
        description="Передайте его сотруднику. Восстановить прежний нельзя — можно только выдать новый."
      />
      <div class="issued mono">{{ issuedPassword }}</div>

      <template #footer>
        <el-button type="primary" @click="resetOpen = false">Понятно</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editOpen" title="Изменить сотрудника" width="640">
      <el-form label-position="top" @submit.prevent>
        <div class="edit-grid">
          <el-form-item label="Фамилия">
            <el-input v-model="editForm.last_name" />
          </el-form-item>
          <el-form-item label="Имя">
            <el-input v-model="editForm.first_name" />
          </el-form-item>
          <el-form-item label="Отчество">
            <el-input v-model="editForm.middle_name" />
          </el-form-item>
          <el-form-item label="Должность">
            <el-input v-model="editForm.position" />
          </el-form-item>
        </div>

        <el-form-item label="Телефон">
          <el-input v-model="editForm.phone_number" />
        </el-form-item>

        <el-form-item label="Работает в">
          <el-select
            v-model="editForm.org_unit_id"
            placeholder="Подразделение"
            style="width: 100%"
          >
            <el-option
              v-for="unit in orgUnits"
              :key="unit.id"
              :label="unit.name"
              :value="unit.id"
            />
          </el-select>
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
import type { components } from "@md/api-client";

type Employee = components["schemas"]["EmployeeSchema"];
type EmployeeRole = components["schemas"]["EmployeeRoleSchema"];
type Role = components["schemas"]["RoleSchema"];
type OrgUnit = components["schemas"]["OrgUnitSchema"];

const api = useApi();
const { can } = useCurrentUser();
const route = useRoute();
const id = String(route.params.id);

const employee = ref<Employee | null>(null);
const editOpen = ref(false);
const resetOpen = ref(false);
const issuedPassword = ref("");
const editError = ref("");
const editForm = reactive({
  first_name: "",
  last_name: "",
  middle_name: "",
  position: "",
  phone_number: "",
  org_unit_id: "",
});
const roles = ref<EmployeeRole[]>([]);
const dictionary = ref<Role[]>([]);
const orgUnits = ref<OrgUnit[]>([]);

const pending = ref(true);
const rolesPending = ref(false);
const busy = ref(false);
const saving = ref(false);
const error = ref("");
const failure = ref("");
const notice = ref("");

const form = reactive({
  role_id: "",
  org_unit_id: "",
  include_descendants: true,
});

const assignableRoles = computed(() => dictionary.value.filter((role) => role.is_assignable));

function orgUnitName(orgUnitId: string | null): string {
  if (!orgUnitId) {
    return "вся организация";
  }

  return orgUnits.value.find((unit) => unit.id === orgUnitId)?.name ?? "—";
}

function reasonOf(status: number, fallback: string): string {
  if (status === 403) {
    return "Нет прав на это действие";
  }
  if (status === 404) {
    return "Не найдено";
  }

  return `${fallback}: ${status}`;
}

async function loadEmployee(): Promise<void> {
  const { data, response } = await api.GET("/api/staff/employees/{employee_id}", {
    params: { path: { employee_id: id } },
  });

  if (!response.ok || !data) {
    throw new Error(reasonOf(response.status, "Не удалось загрузить карточку"));
  }

  employee.value = data;
}

async function loadDictionaries(): Promise<void> {
  if (can("staff.role.read")) {
    const { data, response } = await api.GET("/api/staff/employees/roles", {});
    if (response.ok && data) {
      dictionary.value = data;
    }
  }

  if (can("org_unit.read")) {
    const { data, response } = await api.GET("/api/business/org-units", {});
    if (response.ok && data) {
      orgUnits.value = data;
      form.org_unit_id = data[0]?.id ?? "";
    }
  }
}

async function loadRoles(): Promise<void> {
  if (!can("staff.role.read")) {
    return;
  }

  rolesPending.value = true;
  try {
    const { data, response } = await api.GET("/api/staff/employees/{employee_id}/roles", {
      params: { path: { employee_id: id } },
    });

    if (!response.ok || !data) {
      throw new Error(reasonOf(response.status, "Не удалось загрузить роли"));
    }

    roles.value = data;
  } catch (cause) {
    failure.value = cause instanceof Error ? cause.message : "Ошибка загрузки ролей";
  } finally {
    rolesPending.value = false;
  }
}

async function assign(): Promise<void> {
  busy.value = true;
  failure.value = "";
  notice.value = "";

  try {
    const { response } = await api.POST("/api/staff/employees/{employee_id}/roles", {
      params: { path: { employee_id: id } },
      body: {
        role_id: form.role_id,
        org_unit_id: form.org_unit_id,
        include_descendants: form.include_descendants,
      },
    });

    if (!response.ok) {
      throw new Error(reasonOf(response.status, "Не удалось назначить роль"));
    }

    notice.value = "Роль назначена";
    await loadRoles();
  } catch (cause) {
    failure.value = cause instanceof Error ? cause.message : "Ошибка назначения";
  } finally {
    busy.value = false;
  }
}

async function revoke(assignmentId: string): Promise<void> {
  busy.value = true;
  failure.value = "";
  notice.value = "";

  try {
    const { response } = await api.DELETE(
      "/api/staff/employees/role-assignments/{assignment_id}",
      {
        params: { path: { assignment_id: assignmentId } },
      },
    );

    if (!response.ok) {
      throw new Error(reasonOf(response.status, "Не удалось отозвать роль"));
    }

    notice.value = "Роль отозвана";
    await loadRoles();
  } catch (cause) {
    failure.value = cause instanceof Error ? cause.message : "Ошибка отзыва";
  } finally {
    busy.value = false;
  }
}

async function resetPassword(): Promise<void> {
  const current = employee.value;
  if (!current) {
    return;
  }

  busy.value = true;
  failure.value = "";
  notice.value = "";

  try {
    const { response, data, error: failurePayload } = await api.POST(
      "/api/staff/employees/{employee_id}/password",
      { params: { path: { employee_id: current.id } } },
    );

    if (!response.ok || !data) {
      const payload = failurePayload as { message?: string } | undefined;
      throw new Error(
        payload?.message ?? `Не удалось сбросить пароль: ${response.status}`,
      );
    }

    issuedPassword.value = (data as unknown as { password: string }).password;
    resetOpen.value = true;
    notice.value = "Пароль сброшен — передайте новый сотруднику";
  } catch (cause) {
    failure.value = cause instanceof Error ? cause.message : "Ошибка сброса пароля";
  } finally {
    busy.value = false;
  }
}


function openEdit(): void {
  const current = employee.value;
  if (!current) return;

  editError.value = "";
  notice.value = "";
  editForm.first_name = current.first_name;
  editForm.last_name = current.last_name;
  editForm.middle_name = current.middle_name ?? "";
  editForm.position = current.position;
  editForm.phone_number = current.phone_number ?? "";
  editForm.org_unit_id = current.org_unit_id;
  editOpen.value = true;
}


async function saveEdit(): Promise<void> {
  const current = employee.value;
  if (!current) return;

  saving.value = true;
  editError.value = "";

  try {
    const { response, error } = await api.PATCH(
      "/api/staff/employees/{employee_id}",
      {
        params: { path: { employee_id: current.id } },
        body: {
          first_name: editForm.first_name.trim(),
          last_name: editForm.last_name.trim(),
          middle_name: editForm.middle_name.trim() || null,
          position: editForm.position.trim(),
          phone_number: editForm.phone_number.trim() || null,
          org_unit_id: editForm.org_unit_id,
        },
      },
    );

    if (!response.ok) {
      const payload = error as { message?: string } | undefined;
      throw new Error(payload?.message ?? `Не удалось сохранить: ${response.status}`);
    }

    editOpen.value = false;
    notice.value = "Изменения сохранены";
    await loadEmployee();
  } catch (cause) {
    editError.value = cause instanceof Error ? cause.message : "Ошибка сохранения";
  } finally {
    saving.value = false;
  }
}


async function toggleActive(): Promise<void> {
  const current = employee.value;
  if (!current) return;

  busy.value = true;
  failure.value = "";
  notice.value = "";

  try {
    const { response } = await api.PATCH("/api/staff/employees/{employee_id}", {
      params: { path: { employee_id: current.id } },
      body: { is_active: !current.is_active },
    });

    if (!response.ok) {
      throw new Error(reasonOf(response.status, "Не удалось изменить статус"));
    }

    notice.value = current.is_active ? "Сотрудник уволен" : "Сотрудник возвращён в работу";
    await loadEmployee();
  } catch (cause) {
    failure.value = cause instanceof Error ? cause.message : "Ошибка";
  } finally {
    busy.value = false;
  }
}


onMounted(async () => {
  try {
    await loadEmployee();
    await loadDictionaries();
    await loadRoles();
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Ошибка загрузки";
  } finally {
    pending.value = false;
  }
});
</script>

<style scoped>
.back {
  display: inline-block;
  margin-bottom: 12px;
  color: #909399;
  font-size: 13px;
  text-decoration: none;
}

.back:hover {
  color: #7f1d1d;
}

.card {
  margin-top: 12px;
}

.card-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.issued {
  margin-top: 12px;
  padding: 12px;
  font-size: 18px;
  text-align: center;
  background: #f5f7fa;
  border-radius: 6px;
}

.edit-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 16px;
}

.section__title {
  margin: 28px 0 0;
  font-size: 17px;
  font-weight: 600;
}

.assign {
  max-width: 760px;
  background: #fafafa;
}

.assign__title {
  font-weight: 600;
  margin-bottom: 12px;
}

.assign__form {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 16px;
  align-items: end;
}
</style>
