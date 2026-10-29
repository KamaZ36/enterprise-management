<template>
  <div class="page">
    <h1 class="page__title">Кассы DoKa</h1>
    <p class="page__subtitle">
      Каждая касса DoKa привязана к складской локации, на которую списываются
      продажи. Агент на кассе ходит на сервер по ключу — ключ показывается один
      раз при выдаче.
    </p>

    <ViewOnlyNotice view="pos.source_read" edit="pos.source_manage" />

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

    <div class="page__toolbar">
      <el-button
        v-if="can('pos.source_manage')"
        type="primary"
        @click="openCreate"
      >
        Добавить кассу
      </el-button>
      <el-button :loading="pending" @click="load">Обновить</el-button>
    </div>

    <el-card shadow="never">
      <el-table :data="sources" v-loading="pending" empty-text="Касс DoKa пока нет">
        <el-table-column label="Название" min-width="200">
          <template #default="{ row }">
            <span>{{ (row as PosSource).name }}</span>
            <el-tag
              v-if="!(row as PosSource).is_active"
              size="small"
              type="info"
              effect="light"
              class="tag"
            >
              отключена
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="ИД организации DoKa" min-width="180">
          <template #default="{ row }">
            <span class="mono">{{ (row as PosSource).doka_org_id }}</span>
          </template>
        </el-table-column>

        <el-table-column label="Склад" min-width="200">
          <template #default="{ row }">
            <el-tag v-if="(row as PosSource).org_unit_name" size="small" effect="plain">
              {{ (row as PosSource).org_unit_name }}
            </el-tag>
            <span v-else class="muted">не найдено</span>
          </template>
        </el-table-column>

        <el-table-column label="Добавлена" width="160">
          <template #default="{ row }">
            {{ formatDate((row as PosSource).created_at) }}
          </template>
        </el-table-column>

        <el-table-column label="" width="230" align="right">
          <template #default="{ row }">
            <el-button text size="small" @click="openAgents(row as PosSource)">
              Агенты
            </el-button>
            <el-button
              v-if="can('pos.source_manage')"
              text
              size="small"
              @click="openEdit(row as PosSource)"
            >
              Изменить
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="formOpen"
      :title="editingId ? 'Изменить кассу DoKa' : 'Новая касса DoKa'"
      width="620"
    >
      <el-alert
        v-if="formError"
        :title="formError"
        type="error"
        :closable="false"
        show-icon
        class="page__error"
      />

      <el-form label-position="top" @submit.prevent>
        <el-form-item label="ИД организации в DoKa">
          <el-input
            v-model="form.doka_org_id"
            :disabled="Boolean(editingId)"
            placeholder="например, 915612757914"
          />
          <div class="hint">
            Это атрибут «ИД» из журнала продаж DoKa. После создания не меняется.
          </div>
        </el-form-item>

        <el-form-item label="Название">
          <el-input v-model="form.name" placeholder="Кафе ЗЁРНЫШКО" />
        </el-form-item>

        <el-form-item label="Складская локация">
          <el-select
            v-model="form.org_unit_id"
            filterable
            placeholder="Выберите склад или точку"
            style="width: 100%"
          >
            <el-option
              v-for="location in activeLocations"
              :key="location.id"
              :label="location.name"
              :value="location.id"
            />
          </el-select>
          <div class="hint">Сюда будут списываться проданные позиции.</div>
        </el-form-item>

        <el-form-item v-if="editingId" label="Статус">
          <el-switch v-model="form.is_active" />
          <span class="hint">
            отключённая касса не принимает данные от агента
          </span>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="formOpen = false">Отмена</el-button>
        <el-button
          type="primary"
          :loading="saving"
          :disabled="!form.doka_org_id.trim() || !form.name.trim() || !form.org_unit_id"
          @click="saveSource"
        >
          {{ editingId ? "Сохранить" : "Создать" }}
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="agentsOpen"
      :title="agentsTarget ? `Агенты · ${agentsTarget.name}` : 'Агенты'"
      width="1000"
    >
      <el-alert
        v-if="agentsError"
        :title="agentsError"
        type="error"
        :closable="false"
        show-icon
        class="page__error"
      />

      <div class="agents-toolbar">
        <el-button
          v-if="can('pos.source_manage')"
          type="primary"
          size="small"
          @click="openIssue"
        >
          Выдать ключ
        </el-button>
        <el-button size="small" :loading="agentsPending" @click="loadAgents">
          Обновить
        </el-button>
      </div>

      <el-table
        :data="agents"
        v-loading="agentsPending"
        empty-text="Агент ещё не подключался"
      >
        <el-table-column label="Установка" min-width="180">
          <template #default="{ row }">
            <span v-if="(row as PosAgent).install_id" class="mono">
              {{ (row as PosAgent).install_id }}
            </span>
            <span v-else class="muted">привяжется при первом запросе</span>
          </template>
        </el-table-column>

        <el-table-column label="ПК" min-width="150">
          <template #default="{ row }">
            <div>{{ (row as PosAgent).hostname ?? "—" }}</div>
            <div class="muted">версия {{ (row as PosAgent).version ?? "—" }}</div>
          </template>
        </el-table-column>

        <el-table-column label="Ключ" width="120">
          <template #default="{ row }">
            <span class="mono">••••{{ (row as PosAgent).api_key_prefix }}</span>
          </template>
        </el-table-column>

        <el-table-column label="Статус" width="130">
          <template #default="{ row }">
            <el-tag :type="agentStatusType((row as PosAgent).status)" size="small">
              {{ AGENT_STATUS_LABELS[(row as PosAgent).status] ?? (row as PosAgent).status }}
            </el-tag>
            <div v-if="!(row as PosAgent).is_active" class="muted">ключ отозван</div>
          </template>
        </el-table-column>

        <el-table-column label="Очередь" width="90" align="center">
          <template #default="{ row }">
            {{ (row as PosAgent).pending_receipts }}
          </template>
        </el-table-column>

        <el-table-column label="Последняя связь" width="165">
          <template #default="{ row }">
            {{ (row as PosAgent).last_seen_at ? formatDate((row as PosAgent).last_seen_at!) : "—" }}
          </template>
        </el-table-column>

        <el-table-column label="Последняя ошибка" min-width="200">
          <template #default="{ row }">
            <span v-if="(row as PosAgent).last_error" class="error-text">
              {{ (row as PosAgent).last_error }}
            </span>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>

        <el-table-column label="" width="170" align="right">
          <template #default="{ row }">
            <el-button
              v-if="can('pos.source_manage')"
              text
              size="small"
              @click="rotateKey(row as PosAgent)"
            >
              Ротация
            </el-button>
            <el-button
              v-if="can('pos.source_manage')"
              text
              size="small"
              :type="(row as PosAgent).is_active ? 'warning' : 'success'"
              @click="toggleAgent(row as PosAgent)"
            >
              {{ (row as PosAgent).is_active ? "Отключить" : "Включить" }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <el-dialog v-model="issueOpen" title="Выдать ключ агенту" width="560">
      <el-alert
        v-if="issueError"
        :title="issueError"
        type="error"
        :closable="false"
        show-icon
        class="page__error"
      />

      <el-form label-position="top" @submit.prevent>
        <el-form-item label="Идентификатор установки (необязательно)">
          <el-input
            v-model="issueForm.install_id"
            placeholder="привяжется автоматически при первом запросе"
          />
        </el-form-item>
        <el-form-item label="Имя ПК (необязательно)">
          <el-input v-model="issueForm.hostname" placeholder="PC-CAFE-01" />
        </el-form-item>
        <el-form-item label="Версия агента (необязательно)">
          <el-input v-model="issueForm.version" placeholder="1.0.0" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="issueOpen = false">Отмена</el-button>
        <el-button type="primary" :loading="issuing" @click="issueKey">
          Выдать
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="keyOpen" title="Ключ агента" width="640">
      <el-alert
        title="Сохраните ключ сейчас"
        description="Сервер хранит только хэш. Повторно этот ключ не покажется — при утере сделайте ротацию."
        type="warning"
        :closable="false"
        show-icon
        class="page__error"
      />

      <div class="key-row">
        <el-input :model-value="issuedKey" readonly class="key-input" />
        <el-button @click="copyKey">Копировать</el-button>
      </div>

      <div v-if="issuedAgent" class="key-meta">
        <div>
          Установка:
          <span class="mono">{{ issuedAgent.install_id ?? "привяжется позже" }}</span>
        </div>
        <div>ПК: {{ issuedAgent.hostname ?? "—" }}</div>
      </div>

      <template #footer>
        <el-button type="primary" @click="keyOpen = false">Готово</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import type { components } from "@md/api-client";
import { ElMessage, ElMessageBox } from "element-plus";

import { CAN } from "~/utils/access";

definePageMeta({ permissions: CAN.posSourcesOpen });

type PosSource = components["schemas"]["PosSourceSchema"];
type PosAgent = components["schemas"]["PosAgentSchema"];
type PosLocation = components["schemas"]["PosLocationSchema"];

const AGENT_STATUS_LABELS: Record<string, string> = {
  ok: "Работает",
  warning: "Предупреждение",
  error: "Ошибка",
  paused: "Пауза",
};

const api = useApi();
const { can } = useCurrentUser();

const sources = ref<PosSource[]>([]);
const locations = ref<PosLocation[]>([]);
const pending = ref(false);
const error = ref("");
const notice = ref("");
const saving = ref(false);

const formOpen = ref(false);
const formError = ref("");
const editingId = ref<string | null>(null);
const form = reactive({
  doka_org_id: "",
  name: "",
  org_unit_id: "",
  is_active: true,
});

const agentsOpen = ref(false);
const agentsTarget = ref<PosSource | null>(null);
const agents = ref<PosAgent[]>([]);
const agentsPending = ref(false);
const agentsError = ref("");

const issueOpen = ref(false);
const issuing = ref(false);
const issueError = ref("");
const issueForm = reactive({
  install_id: "",
  hostname: "",
  version: "",
});

const keyOpen = ref(false);
const issuedKey = ref("");
const issuedAgent = ref<PosAgent | null>(null);

const activeLocations = computed(() =>
  locations.value.filter((location) => location.is_active),
);

function agentStatusType(
  status: string,
): "success" | "warning" | "danger" | "info" {
  if (status === "ok") return "success";
  if (status === "warning") return "warning";
  if (status === "error") return "danger";
  return "info";
}

function formatDate(value: string): string {
  return new Date(value).toLocaleString("ru-RU", {
    dateStyle: "short",
    timeStyle: "short",
  });
}

function reasonOf(status: number, body: unknown, fallback: string): string {
  const message = (body as { message?: string } | undefined)?.message;
  if (message) return message;
  if (status === 403) return "Нет прав на это действие";
  if (status === 404) return "Касса не найдена";
  if (status === 409) return "Касса с таким ИД DoKa уже зарегистрирована";
  if (status === 422) return "Проверьте заполненные поля";
  return `${fallback}: ${status}`;
}

async function load(): Promise<void> {
  pending.value = true;
  error.value = "";

  try {
    const { data, response } = await api.GET("/api/pos/sources", {});

    if (!response.ok || !data) {
      throw new Error(
        reasonOf(response.status, null, "Не удалось загрузить кассы"),
      );
    }

    sources.value = data;
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Ошибка загрузки";
    sources.value = [];
  } finally {
    pending.value = false;
  }
}

async function loadLocations(): Promise<void> {
  if (!can("pos.source_manage") && !can("pos.source_read")) {
    return;
  }

  const { data, response } = await api.GET("/api/pos/locations", {});
  locations.value = response.ok && data ? data : [];
}

function resetForm(): void {
  form.doka_org_id = "";
  form.name = "";
  form.org_unit_id = "";
  form.is_active = true;
}

function openCreate(): void {
  editingId.value = null;
  formError.value = "";
  notice.value = "";
  resetForm();
  formOpen.value = true;
  void loadLocations();
}

function openEdit(source: PosSource): void {
  editingId.value = source.id;
  formError.value = "";
  notice.value = "";
  form.doka_org_id = source.doka_org_id;
  form.name = source.name;
  form.org_unit_id = source.org_unit_id;
  form.is_active = source.is_active;
  formOpen.value = true;
  void loadLocations();
}

async function saveSource(): Promise<void> {
  saving.value = true;
  formError.value = "";

  try {
    if (editingId.value) {
      const { response, error: failure } = await api.PATCH(
        "/api/pos/sources/{source_id}",
        {
          params: { path: { source_id: editingId.value } },
          body: {
            name: form.name.trim(),
            org_unit_id: form.org_unit_id,
            is_active: form.is_active,
          },
        },
      );

      if (!response.ok) {
        throw new Error(
          reasonOf(response.status, failure, "Не удалось изменить кассу"),
        );
      }

      notice.value = "Касса обновлена";
    } else {
      const { response, error: failure } = await api.POST("/api/pos/sources", {
        body: {
          doka_org_id: form.doka_org_id.trim(),
          name: form.name.trim(),
          org_unit_id: form.org_unit_id,
        },
      });

      if (!response.ok) {
        throw new Error(
          reasonOf(response.status, failure, "Не удалось создать кассу"),
        );
      }

      notice.value = "Касса добавлена. Теперь выдайте ключ агенту.";
    }

    formOpen.value = false;
    await load();
  } catch (cause) {
    formError.value =
      cause instanceof Error ? cause.message : "Ошибка сохранения";
  } finally {
    saving.value = false;
  }
}

function openAgents(source: PosSource): void {
  agentsTarget.value = source;
  agentsError.value = "";
  agents.value = [];
  agentsOpen.value = true;
  void loadAgents();
}

async function loadAgents(): Promise<void> {
  const target = agentsTarget.value;
  if (!target) return;

  agentsPending.value = true;
  agentsError.value = "";

  try {
    const { data, response } = await api.GET(
      "/api/pos/sources/{source_id}/agents",
      { params: { path: { source_id: target.id } } },
    );

    if (!response.ok || !data) {
      throw new Error(
        reasonOf(response.status, null, "Не удалось загрузить агентов"),
      );
    }

    agents.value = data;
  } catch (cause) {
    agentsError.value =
      cause instanceof Error ? cause.message : "Ошибка загрузки";
    agents.value = [];
  } finally {
    agentsPending.value = false;
  }
}

function openIssue(): void {
  issueError.value = "";
  issueForm.install_id = "";
  issueForm.hostname = "";
  issueForm.version = "";
  issueOpen.value = true;
}

async function issueKey(): Promise<void> {
  const target = agentsTarget.value;
  if (!target) return;

  issuing.value = true;
  issueError.value = "";

  try {
    const { data, response, error: failure } = await api.POST(
      "/api/pos/sources/{source_id}/agents/keys",
      {
        params: { path: { source_id: target.id } },
        body: {
          install_id: issueForm.install_id.trim() || null,
          hostname: issueForm.hostname.trim() || null,
          version: issueForm.version.trim() || null,
        },
      },
    );

    if (!response.ok || !data) {
      throw new Error(
        reasonOf(response.status, failure, "Не удалось выдать ключ"),
      );
    }

    issueOpen.value = false;
    showKey(data.api_key, data.agent);
    await loadAgents();
  } catch (cause) {
    issueError.value =
      cause instanceof Error ? cause.message : "Ошибка выдачи ключа";
  } finally {
    issuing.value = false;
  }
}

async function rotateKey(agent: PosAgent): Promise<void> {
  const target = agentsTarget.value;
  if (!target) return;

  try {
    await ElMessageBox.confirm(
      "Старый ключ перестанет работать сразу. Агенту нужно будет ввести новый.",
      "Перевыпустить ключ",
      { confirmButtonText: "Перевыпустить", cancelButtonText: "Отмена" },
    );
  } catch {
    return;
  }

  try {
    const { data, response, error: failure } = await api.POST(
      "/api/pos/agents/{agent_id}/keys/rotate",
      { params: { path: { agent_id: agent.id } } },
    );

    if (!response.ok || !data) {
      throw new Error(
        reasonOf(response.status, failure, "Не удалось перевыпустить ключ"),
      );
    }

    showKey(data.api_key, data.agent);
    await loadAgents();
  } catch (cause) {
    agentsError.value =
      cause instanceof Error ? cause.message : "Ошибка ротации ключа";
  }
}

async function toggleAgent(agent: PosAgent): Promise<void> {
  const target = agentsTarget.value;
  if (!target) return;

  agentsError.value = "";

  try {
    const { response, error: failure } = await api.PATCH(
      "/api/pos/agents/{agent_id}/active",
      {
        params: { path: { agent_id: agent.id } },
        body: { is_active: !agent.is_active },
      },
    );

    if (!response.ok) {
      throw new Error(
        reasonOf(response.status, failure, "Не удалось изменить агента"),
      );
    }

    await loadAgents();
  } catch (cause) {
    agentsError.value =
      cause instanceof Error ? cause.message : "Ошибка изменения агента";
  }
}

function showKey(key: string, agent: PosAgent): void {
  issuedKey.value = key;
  issuedAgent.value = agent;
  keyOpen.value = true;
}

async function copyKey(): Promise<void> {
  try {
    await navigator.clipboard.writeText(issuedKey.value);
    ElMessage.success("Ключ скопирован");
  } catch {
    ElMessage.warning("Не удалось скопировать — выделите ключ вручную");
  }
}

onMounted(async () => {
  await Promise.all([load(), loadLocations()]);
});
</script>

<style scoped>
.muted {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.mono {
  font-family: monospace;
}

.tag {
  margin-left: 6px;
}

.hint {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.4;
  margin-top: 4px;
}

.error-text {
  color: var(--el-color-danger);
  font-size: 12px;
  line-height: 1.3;
}

.agents-toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.key-row {
  display: flex;
  gap: 8px;
}

.key-input {
  font-family: monospace;
}

.key-meta {
  margin-top: 12px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.6;
  word-break: break-all;
}
</style>
