<template>
  <div class="page">
    <h1 class="page__title">Кассы</h1>
    <p class="page__subtitle">
      Фискальные регистраторы и их привязка к точкам. По РНМ чеки из ОФД будут
      попадать на нужный склад.
    </p>

    <ViewOnlyNotice view="cash_register.read" edit="cash_register.manage" />

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

    <el-card shadow="never">
      <div class="toolbar">
        <el-select
          v-model="pointFilter"
          placeholder="Все точки"
          clearable
          style="width: 240px"
          @change="load"
        >
          <el-option
            v-for="location in locations"
            :key="location.id"
            :label="location.name"
            :value="location.id"
          />
        </el-select>

        <el-input
          v-model="search"
          placeholder="Поиск по названию или РНМ"
          clearable
          style="width: 260px"
        />

        <el-button size="small" :loading="pending" @click="load">
          Обновить
        </el-button>

        <el-button
          v-if="can('cash_register.manage')"
          type="primary"
          size="small"
          @click="openCreate"
        >
          Добавить
        </el-button>
      </div>

      <el-table
        v-loading="pending"
        :data="filtered"
        row-key="id"
        stripe
        empty-text="Касс пока нет"
      >
        <el-table-column label="Название" min-width="200">
          <template #default="{ row }">
            <span>{{ row.name }}</span>
            <el-tag
              v-if="!row.is_active"
              size="small"
              type="info"
              effect="light"
              class="tag"
            >
              снята
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="РНМ" width="170">
          <template #default="{ row }">
            <span class="mono">{{ row.reg_number ?? "—" }}</span>
          </template>
        </el-table-column>

        <el-table-column label="ЗН" width="170">
          <template #default="{ row }">
            <span class="mono">{{ row.serial_number ?? "—" }}</span>
          </template>
        </el-table-column>

        <el-table-column label="Точка" min-width="180">
          <template #default="{ row }">
            <el-tag v-if="row.org_unit_name" size="small" effect="plain">
              {{ row.org_unit_name }}
            </el-tag>
            <span v-else class="muted">не привязана</span>
          </template>
        </el-table-column>

        <el-table-column label="Модель" min-width="150">
          <template #default="{ row }">
            {{ row.model ?? "—" }}
          </template>
        </el-table-column>

        <el-table-column label="ФФД" width="80">
          <template #default="{ row }">
            {{ row.ffd_version ?? "—" }}
          </template>
        </el-table-column>

        <el-table-column label="" width="230" align="right">
          <template #default="{ row }">
            <el-button text size="small" @click="openHistory(row as CashRegister)">
              История
            </el-button>
            <el-button
              v-if="can('cash_register.manage')"
              text
              size="small"
              @click="openEdit(row as CashRegister)"
            >
              Изменить
            </el-button>
            <el-button
              v-if="can('cash_register.manage') && row.is_active"
              text
              size="small"
              @click="openBind(row as CashRegister)"
            >
              {{ row.org_unit_id ? "Перепривязать" : "Привязать" }}
            </el-button>
            <el-button
              v-if="can('cash_register.manage') && row.org_unit_id"
              text
              size="small"
              type="warning"
              @click="unbind(row as CashRegister)"
            >
              Отвязать
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="createOpen" title="Новая касса" width="720">
      <el-form label-position="top" @submit.prevent>
        <div class="form-grid">
          <el-form-item label="Название">
            <el-input v-model="form.name" placeholder="Касса на Ленина" />
          </el-form-item>
          <el-form-item label="РНМ">
            <el-input v-model="form.reg_number" placeholder="16 цифр" />
          </el-form-item>
          <el-form-item label="ЗН (заводской номер)">
            <el-input v-model="form.serial_number" />
          </el-form-item>
          <el-form-item label="Место в ОФД">
            <el-input v-model="form.fiscal_place" placeholder="Торговый зал" />
          </el-form-item>
          <el-form-item label="Модель">
            <el-input v-model="form.model" placeholder="АТОЛ 91Ф" />
          </el-form-item>
          <el-form-item label="Номер ФН">
            <el-input v-model="form.fn_number" />
          </el-form-item>
          <el-form-item label="Версия ФФД">
            <el-input v-model="form.ffd_version" placeholder="1.2" />
          </el-form-item>
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
        <el-button type="primary" :loading="saving" @click="createRegister">
          Создать
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editOpen" title="Изменить кассу" width="720">
      <el-form label-position="top" @submit.prevent>
        <div class="form-grid">
          <el-form-item label="Название">
            <el-input v-model="form.name" />
          </el-form-item>
          <el-form-item label="РНМ">
            <el-input v-model="form.reg_number" placeholder="16 цифр" />
          </el-form-item>
          <el-form-item label="ЗН (заводской номер)">
            <el-input v-model="form.serial_number" />
          </el-form-item>
          <el-form-item label="Место в ОФД">
            <el-input v-model="form.fiscal_place" />
          </el-form-item>
          <el-form-item label="Модель">
            <el-input v-model="form.model" />
          </el-form-item>
          <el-form-item label="Номер ФН">
            <el-input v-model="form.fn_number" />
          </el-form-item>
          <el-form-item label="Версия ФФД">
            <el-input v-model="form.ffd_version" />
          </el-form-item>
        </div>

        <el-form-item label="Статус">
          <el-switch v-model="editActive" />
          <span class="hint">
            снятие с учёта закрывает текущую привязку к точке
          </span>
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

    <el-dialog v-model="bindOpen" title="Привязать кассу" width="560">
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="Точка">
          <el-select
            v-model="bindForm.org_unit_id"
            placeholder="Выберите точку"
            style="width: 100%"
          >
            <el-option
              v-for="location in activeLocations"
              :key="location.id"
              :label="location.name"
              :value="location.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="С какого момента">
          <el-date-picker
            v-model="bindForm.effective_from"
            type="datetime"
            placeholder="Сейчас"
            style="width: 100%"
          />
        </el-form-item>

        <p v-if="bindTarget?.org_unit_id" class="hint">
          Текущая привязка будет закрыта в момент начала новой.
        </p>

        <el-alert
          v-if="bindError"
          :title="bindError"
          type="error"
          :closable="false"
          show-icon
        />
      </el-form>

      <template #footer>
        <el-button @click="bindOpen = false">Отмена</el-button>
        <el-button
          type="primary"
          :loading="saving"
          :disabled="!bindForm.org_unit_id"
          @click="bindRegister"
        >
          Привязать
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="historyOpen" title="История привязок" width="720">
      <div v-if="history">
        <div class="history-title">{{ history.name }}</div>
        <el-table :data="history.bindings" size="small">
          <el-table-column label="Точка" min-width="200">
            <template #default="{ row }">
              {{ row.org_unit_name ?? row.org_unit_id }}
            </template>
          </el-table-column>
          <el-table-column label="С" width="180">
            <template #default="{ row }">{{ formatDate(row.effective_from) }}</template>
          </el-table-column>
          <el-table-column label="По" width="180">
            <template #default="{ row }">
              {{ row.effective_to ? formatDate(row.effective_to) : "по сейчас" }}
            </template>
          </el-table-column>
        </el-table>
        <el-empty
          v-if="!history.bindings.length"
          description="Привязок ещё не было"
          :image-size="70"
        />
      </div>
      <el-skeleton v-else :rows="3" animated />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { CAN } from "~/utils/access";

definePageMeta({ permissions: CAN.cashRegistersOpen });
import { ElMessageBox } from "element-plus";
import type { components } from "@md/api-client";

type CashRegister = components["schemas"]["CashRegisterSchema"];
type CashRegisterDetail = components["schemas"]["CashRegisterDetailSchema"];
type StockLocation = components["schemas"]["StockLocationOptionSchema"];

const api = useApi();
const { can } = useCurrentUser();

const registers = ref<CashRegister[]>([]);
const locations = ref<StockLocation[]>([]);
const pointFilter = ref<string | null>(null);
const search = ref("");

const pending = ref(false);
const saving = ref(false);
const error = ref("");
const notice = ref("");

const createOpen = ref(false);
const editOpen = ref(false);
const bindOpen = ref(false);
const historyOpen = ref(false);
const createError = ref("");
const editError = ref("");
const bindError = ref("");

const editingId = ref<string | null>(null);
const editActive = ref(true);
const bindTarget = ref<CashRegister | null>(null);
const history = ref<CashRegisterDetail | null>(null);

const form = reactive({
  name: "",
  reg_number: "",
  serial_number: "",
  fiscal_place: "",
  model: "",
  fn_number: "",
  ffd_version: "",
});

const bindForm = reactive<{
  org_unit_id: string | null;
  effective_from: Date | null;
}>({
  org_unit_id: null,
  effective_from: null,
});

const filtered = computed(() => {
  const needle = search.value.trim().toLowerCase();
  if (!needle) {
    return registers.value;
  }

  return registers.value.filter((row) => {
    return (
      row.name.toLowerCase().includes(needle) ||
      (row.reg_number ?? "").includes(needle) ||
      (row.serial_number ?? "").toLowerCase().includes(needle)
    );
  });
});

const activeLocations = computed(() =>
  locations.value.filter((location) => location.is_active),
);

function reasonOf(status: number, body: unknown, fallback: string): string {
  const message = (body as { message?: string } | undefined)?.message;
  if (message) {
    return message;
  }
  if (status === 403) {
    return "Нет прав на это действие";
  }
  if (status === 409) {
    return "Касса с таким РНМ уже есть";
  }
  if (status === 422) {
    return "Проверьте заполненные поля";
  }

  return `${fallback}: ${status}`;
}

function formatDate(value: string): string {
  return new Date(value).toLocaleString("ru-RU", {
    dateStyle: "short",
    timeStyle: "short",
  });
}

async function load(): Promise<void> {
  pending.value = true;
  error.value = "";

  try {
    const { data, response } = await api.GET("/api/fiscal/cash-registers", {
      params: {
        query: {
          org_unit_id: pointFilter.value ?? undefined,
        },
      },
    });

    if (!response.ok || !data) {
      throw new Error(reasonOf(response.status, null, "Не удалось загрузить кассы"));
    }

    registers.value = data;
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Ошибка загрузки";
    registers.value = [];
  } finally {
    pending.value = false;
  }
}

async function loadLocations(): Promise<void> {
  const { data } = await api.GET("/api/fiscal/stock-locations", {});
  locations.value = data ?? [];
}

function resetForm(): void {
  form.name = "";
  form.reg_number = "";
  form.serial_number = "";
  form.fiscal_place = "";
  form.model = "";
  form.fn_number = "";
  form.ffd_version = "";
}

function body(formValue: typeof form) {
  return {
    name: formValue.name.trim() || null,
    reg_number: formValue.reg_number.trim() || null,
    serial_number: formValue.serial_number.trim() || null,
    fiscal_place: formValue.fiscal_place.trim() || null,
    model: formValue.model.trim() || null,
    fn_number: formValue.fn_number.trim() || null,
    ffd_version: formValue.ffd_version.trim() || null,
  };
}

function openCreate(): void {
  resetForm();
  createError.value = "";
  notice.value = "";
  createOpen.value = true;
}

async function createRegister(): Promise<void> {
  saving.value = true;
  createError.value = "";

  try {
    const { response, error: failure } = await api.POST(
      "/api/fiscal/cash-registers",
      { body: body(form) },
    );

    if (!response.ok) {
      throw new Error(
        reasonOf(response.status, failure, "Не удалось создать кассу"),
      );
    }

    createOpen.value = false;
    notice.value = `Касса «${form.name.trim() || "без названия"}» добавлена`;
    await load();
  } catch (cause) {
    createError.value =
      cause instanceof Error ? cause.message : "Ошибка создания";
  } finally {
    saving.value = false;
  }
}

function openEdit(row: CashRegister): void {
  editingId.value = row.id;
  editError.value = "";
  notice.value = "";
  form.name = row.name;
  form.reg_number = row.reg_number ?? "";
  form.serial_number = row.serial_number ?? "";
  form.fiscal_place = row.fiscal_place ?? "";
  form.model = row.model ?? "";
  form.fn_number = row.fn_number ?? "";
  form.ffd_version = row.ffd_version ?? "";
  editActive.value = row.is_active;
  editOpen.value = true;
}

async function saveEdit(): Promise<void> {
  const id = editingId.value;
  if (!id) {
    return;
  }

  saving.value = true;
  editError.value = "";

  try {
    const { response, error: failure } = await api.PATCH(
      "/api/fiscal/cash-registers/{cash_register_id}",
      {
        params: { path: { cash_register_id: id } },
        body: { ...body(form), is_active: editActive.value },
      },
    );

    if (!response.ok) {
      throw new Error(
        reasonOf(response.status, failure, "Не удалось изменить кассу"),
      );
    }

    editOpen.value = false;
    notice.value = "Касса обновлена";
    await load();
  } catch (cause) {
    editError.value =
      cause instanceof Error ? cause.message : "Ошибка сохранения";
  } finally {
    saving.value = false;
  }
}

function openBind(row: CashRegister): void {
  bindTarget.value = row;
  bindError.value = "";
  notice.value = "";
  bindForm.org_unit_id = null;
  bindForm.effective_from = null;
  bindOpen.value = true;
}

async function bindRegister(): Promise<void> {
  const target = bindTarget.value;
  if (!target || !bindForm.org_unit_id) {
    return;
  }

  saving.value = true;
  bindError.value = "";

  try {
    const { response, error: failure } = await api.POST(
      "/api/fiscal/cash-registers/{cash_register_id}/bind",
      {
        params: { path: { cash_register_id: target.id } },
        body: {
          org_unit_id: bindForm.org_unit_id,
          effective_from: bindForm.effective_from
            ? bindForm.effective_from.toISOString()
            : null,
        },
      },
    );

    if (!response.ok) {
      throw new Error(
        reasonOf(response.status, failure, "Не удалось привязать кассу"),
      );
    }

    bindOpen.value = false;
    notice.value = "Касса привязана к точке";
    await load();
  } catch (cause) {
    bindError.value =
      cause instanceof Error ? cause.message : "Ошибка привязки";
  } finally {
    saving.value = false;
  }
}

async function unbind(row: CashRegister): Promise<void> {
  const confirmed = await ElMessageBox.confirm(
    `Закрыть привязку кассы «${row.name}» к точке «${row.org_unit_name ?? ""}»?`,
    "Отвязать кассу",
    { confirmButtonText: "Отвязать", cancelButtonText: "Отмена", type: "warning" },
  ).catch(() => null);

  if (!confirmed) {
    return;
  }

  const { response, error: failure } = await api.POST(
    "/api/fiscal/cash-registers/{cash_register_id}/unbind",
    {
      params: { path: { cash_register_id: row.id } },
      body: { effective_to: null },
    },
  );

  if (!response.ok) {
    error.value = reasonOf(response.status, failure, "Не удалось отвязать кассу");
    return;
  }

  notice.value = "Привязка закрыта";
  await load();
}

async function openHistory(row: CashRegister): Promise<void> {
  history.value = null;
  historyOpen.value = true;

  const { data, response } = await api.GET(
    "/api/fiscal/cash-registers/{cash_register_id}",
    { params: { path: { cash_register_id: row.id } } },
  );

  if (response.ok && data) {
    history.value = data;
  }
}

onMounted(async () => {
  await Promise.all([load(), loadLocations()]);
});
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 16px;
}

.mono {
  font-family: monospace;
}

.muted {
  color: var(--el-text-color-secondary);
}

.tag {
  margin-left: 6px;
}

.hint {
  margin-left: 8px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.notice {
  margin-bottom: 12px;
}

.history-title {
  font-weight: 600;
  margin-bottom: 8px;
}
</style>
