<template>
  <div class="page">
    <h1 class="page__title">Сотрудники</h1>
    <p class="page__subtitle">
      Всего в системе: {{ total }}. Нажмите на фамилию, чтобы открыть карточку.
    </p>

    <div class="page__toolbar">
      <el-button v-if="can('staff.employee.manage')" type="primary" @click="openCreate">
        Принять на работу
      </el-button>
      <el-button :loading="pending" @click="load">Обновить</el-button>
    </div>

    <el-alert
      v-if="error"
      :title="error"
      type="error"
      :closable="false"
      show-icon
      class="page__error"
    />

    <el-table v-loading="pending" :data="items" stripe border>
      <el-table-column label="ФИО" min-width="260">
        <template #default="{ row }">
          <NuxtLink :to="`/employees/${row.id}`" class="link">{{ fullName(row as Employee) }}</NuxtLink>
        </template>
      </el-table-column>

      <el-table-column prop="position" label="Должность" min-width="200" />

      <el-table-column label="Телефон" width="190">
        <template #default="{ row }">{{ row.phone_number ?? "—" }}</template>
      </el-table-column>

      <el-table-column label="Принят" width="130">
        <template #default="{ row }">{{ formatDate(row.hired_at) }}</template>
      </el-table-column>

      <el-table-column label="Статус" width="130">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" effect="light">
            {{ row.is_active ? "работает" : "уволен" }}
          </el-tag>
        </template>
      </el-table-column>

      <template #empty>
        <el-empty description="Сотрудников пока нет" />
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

    <el-dialog v-model="createOpen" title="Приём на работу" width="560">
      <el-form label-position="top">
        <div class="form-grid">
          <el-form-item label="Фамилия">
            <el-input v-model="form.last_name" />
          </el-form-item>
          <el-form-item label="Имя">
            <el-input v-model="form.first_name" />
          </el-form-item>
          <el-form-item label="Отчество">
            <el-input v-model="form.middle_name" />
          </el-form-item>
          <el-form-item label="Должность">
            <el-input v-model="form.position" placeholder="Мясник" />
          </el-form-item>
          <el-form-item label="Телефон">
            <el-input v-model="form.phone_number" placeholder="+7 900 000-00-00" />
          </el-form-item>
          <el-form-item label="Дата приёма">
            <el-date-picker
              v-model="form.hired_at"
              type="date"
              value-format="YYYY-MM-DD"
              style="width: 100%"
            />
          </el-form-item>
        </div>

        <el-form-item label="Логин для входа">
          <el-input v-model="form.username" placeholder="ivanov" />
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
        <el-button type="primary" :loading="saving" @click="createEmployee">
          Принять и выдать доступ
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="credentialsOpen" title="Доступ выдан" width="480">
      <el-alert
        type="warning"
        :closable="false"
        show-icon
        title="Пароль показывается один раз"
        description="Передайте его сотруднику. Восстановить пароль нельзя — можно только выдать новый."
      />

      <el-descriptions :column="1" border class="credentials">
        <el-descriptions-item label="Логин">{{ credentials.username }}</el-descriptions-item>
        <el-descriptions-item label="Пароль">
          <span class="mono credentials__password">{{ credentials.password }}</span>
        </el-descriptions-item>
      </el-descriptions>

      <template #footer>
        <el-button type="primary" @click="credentialsOpen = false">Понятно</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import type { components } from "@md/api-client";

type Employee = components["schemas"]["EmployeeSchema"];

const PAGE_SIZE = 20;

const api = useApi();
const { can } = useCurrentUser();

const items = ref<Employee[]>([]);
const total = ref(0);
const page = ref(1);
const pending = ref(false);
const error = ref("");

const createOpen = ref(false);
const credentialsOpen = ref(false);
const saving = ref(false);
const createError = ref("");
const credentials = reactive({ username: "", password: "" });

const today = new Date().toISOString().slice(0, 10);
const form = reactive({
  last_name: "",
  first_name: "",
  middle_name: "",
  position: "",
  phone_number: "",
  hired_at: today,
  username: "",
});

function reasonOf(status: number, fallback: string): string {
  if (status === 403) {
    return "Нет прав на это действие";
  }
  if (status === 409) {
    return "Такой логин уже занят";
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
    const { data, response } = await api.GET("/api/employees", {
      params: { query: { limit: PAGE_SIZE, offset: (page.value - 1) * PAGE_SIZE } },
    });

    if (!response.ok || !data) {
      throw new Error(reasonOf(response.status, "Не удалось загрузить список"));
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

function openCreate(): void {
  createError.value = "";
  createOpen.value = true;
}

async function createEmployee(): Promise<void> {
  saving.value = true;
  createError.value = "";

  try {
    const { data, response } = await api.POST("/api/employees", {
      body: {
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        middle_name: form.middle_name.trim() || null,
        phone_number: form.phone_number.trim() || null,
        position: form.position.trim(),
        hired_at: form.hired_at,
      },
    });

    if (!response.ok || !data) {
      throw new Error(reasonOf(response.status, "Не удалось принять сотрудника"));
    }

    const employeeId = (data as unknown as { employee_id: string }).employee_id;

    const credentialResponse = await api.POST("/api/employees/credential", {
      body: { employee_id: employeeId, username: form.username.trim() },
    });

    if (!credentialResponse.response.ok || !credentialResponse.data) {
      throw new Error(
        reasonOf(credentialResponse.response.status, "Сотрудник принят, но доступ не выдан"),
      );
    }

    const issued = credentialResponse.data as unknown as {
      username: string;
      password: string;
    };

    credentials.username = issued.username;
    credentials.password = issued.password;
    createOpen.value = false;
    credentialsOpen.value = true;

    form.last_name = "";
    form.first_name = "";
    form.middle_name = "";
    form.position = "";
    form.phone_number = "";
    form.username = "";

    page.value = 1;
    await load();
  } catch (cause) {
    createError.value = cause instanceof Error ? cause.message : "Ошибка приёма на работу";
  } finally {
    saving.value = false;
  }
}

onMounted(load);
watch(page, load);
</script>

<style scoped>
.page__error {
  margin-bottom: 16px;
}

.link {
  color: #7f1d1d;
  font-weight: 600;
  text-decoration: none;
}

.link:hover {
  text-decoration: underline;
}

.pager {
  margin-top: 18px;
  justify-content: flex-end;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 16px;
}

.credentials {
  margin-top: 16px;
}

.credentials__password {
  font-size: 16px;
  font-weight: 700;
  color: #7f1d1d;
}
</style>
