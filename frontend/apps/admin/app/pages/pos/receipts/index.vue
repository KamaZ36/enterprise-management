<template>
  <div class="page">
    <h1 class="page__title">Чеки DoKa</h1>
    <p class="page__subtitle">
      Продажи, которые агент забирает из журнала DoKa. Чек проводится по складу,
      когда все его товары сопоставлены с номенклатурой и хватает остатка.
    </p>

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
        v-if="canAll(CAN.posReceiptsManage)"
        type="primary"
        :loading="posting"
        @click="postPending"
      >
        Провести непринятые
      </el-button>

      <el-select
        v-if="sources.length"
        v-model="sourceFilter"
        placeholder="Все кассы"
        clearable
        style="width: 220px"
        @change="applyFilters"
      >
        <el-option
          v-for="source in sources"
          :key="source.id"
          :label="source.name"
          :value="source.id"
        />
      </el-select>

      <el-select
        v-model="statusFilter"
        placeholder="Все статусы"
        clearable
        style="width: 200px"
        @change="applyFilters"
      >
        <el-option
          v-for="(label, value) in STATUS_LABELS"
          :key="value"
          :label="label"
          :value="value"
        />
      </el-select>

      <el-date-picker
        v-model="range"
        type="daterange"
        unlink-panels
        range-separator="—"
        start-placeholder="С даты"
        end-placeholder="По дату"
        value-format="YYYY-MM-DD"
        style="width: 260px"
        @change="applyFilters"
      />

      <el-button :loading="pending" @click="load">Обновить</el-button>
    </div>

    <el-card shadow="never">
      <el-table :data="items" v-loading="pending" empty-text="Чеков пока нет">
        <el-table-column label="Дата" min-width="150">
          <template #default="{ row }">
            {{ formatDate((row as PosReceipt).occurred_at) }}
          </template>
        </el-table-column>

        <el-table-column label="Касса" min-width="170">
          <template #default="{ row }">
            <div>{{ (row as PosReceipt).source_name ?? "—" }}</div>
            <div class="muted">
              {{ (row as PosReceipt).subdivision_name ?? "без подразделения" }}
            </div>
          </template>
        </el-table-column>

        <el-table-column label="Точка" min-width="150">
          <template #default="{ row }">
            {{ (row as PosReceipt).org_unit_name ?? "—" }}
          </template>
        </el-table-column>

        <el-table-column label="Тип" width="110">
          <template #default="{ row }">
            <el-tag
              :type="(row as PosReceipt).kind === 'return' ? 'warning' : 'info'"
              effect="plain"
              size="small"
            >
              {{ KIND_LABELS[(row as PosReceipt).kind] ?? (row as PosReceipt).kind }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="Сумма" width="130" align="right">
          <template #default="{ row }">
            {{ formatKopecks((row as PosReceipt).total_kopecks) }}
          </template>
        </el-table-column>

        <el-table-column label="Строки" width="110" align="center">
          <template #default="{ row }">
            {{ (row as PosReceipt).line_count }}
            <span v-if="(row as PosReceipt).unmapped_count" class="muted">
              ({{ (row as PosReceipt).unmapped_count }} без пары)
            </span>
          </template>
        </el-table-column>

        <el-table-column label="Статус" min-width="160">
          <template #default="{ row }">
            <el-tag :type="statusType((row as PosReceipt).status)">
              {{
                STATUS_LABELS[(row as PosReceipt).status] ??
                (row as PosReceipt).status
              }}
            </el-tag>
            <div v-if="(row as PosReceipt).error" class="muted status-error">
              {{ (row as PosReceipt).error }}
            </div>
          </template>
        </el-table-column>

        <el-table-column label="" width="110" align="right">
          <template #default="{ row }">
            <el-button text @click="openDetail((row as PosReceipt).id)">
              Открыть
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="page"
        class="pager"
        layout="prev, pager, next, total"
        :page-size="PAGE_SIZE"
        :total="total"
        :disabled="pending"
        @current-change="load"
      />
    </el-card>

    <el-dialog v-model="detailOpen" title="Чек DoKa" width="1100">
      <el-alert
        v-if="detailError"
        :title="detailError"
        type="error"
        :closable="false"
        show-icon
        class="page__error"
      />

      <template v-if="detail">
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="Статус">
            <el-tag :type="statusType(detail.status)">
              {{ STATUS_LABELS[detail.status] ?? detail.status }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="Дата">
            {{ formatDate(detail.occurred_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="Сумма">
            {{ formatKopecks(detail.total_kopecks) }}
          </el-descriptions-item>
          <el-descriptions-item label="Касса">
            {{ detail.source_name ?? "—" }}
          </el-descriptions-item>
          <el-descriptions-item label="Точка">
            {{ detail.org_unit_name ?? "—" }}
          </el-descriptions-item>
          <el-descriptions-item label="Тип">
            {{ KIND_LABELS[detail.kind] ?? detail.kind }}
          </el-descriptions-item>
          <el-descriptions-item label="Оплата">
            {{ paymentLabel(detail.payment_kind) }}
          </el-descriptions-item>
          <el-descriptions-item label="Подразделение DoKa">
            {{ detail.subdivision_name ?? "—" }}
          </el-descriptions-item>
          <el-descriptions-item label="Кассир">
            {{ detail.cashier ?? "—" }}
          </el-descriptions-item>
          <el-descriptions-item label="Смена">
            {{ detail.shift ?? "—" }}
          </el-descriptions-item>
          <el-descriptions-item label="Чек №">
            {{ detail.number ?? "—" }}
          </el-descriptions-item>
          <el-descriptions-item label="ФД / ФП">
            {{ detail.fd_number ?? "—" }} / {{ detail.fp_number ?? "—" }}
          </el-descriptions-item>
          <el-descriptions-item label="ФН">
            {{ detail.fn_number ?? "—" }}
          </el-descriptions-item>
          <el-descriptions-item label="Проведён">
            {{ detail.posted_at ? formatDate(detail.posted_at) : "—" }}
          </el-descriptions-item>
          <el-descriptions-item label="GUID">
            <span class="mono">{{ shortGuid(detail.external_guid) }}</span>
          </el-descriptions-item>
        </el-descriptions>

        <el-alert
          v-if="detail.error"
          :title="detail.error"
          type="warning"
          :closable="false"
          show-icon
          class="detail-error"
        />

        <el-table :data="detail.lines" class="lines" empty-text="В чеке нет строк">
          <el-table-column label="№" width="55" prop="line_number" />
          <el-table-column label="Товар в чеке" min-width="190">
            <template #default="{ row }">
              <div>{{ (row as PosReceiptLine).product_name ?? "—" }}</div>
              <div class="muted mono">
                {{ shortGuid((row as PosReceiptLine).product_guid) }}
              </div>
            </template>
          </el-table-column>
          <el-table-column label="Кол-во" width="120" align="right">
            <template #default="{ row }">
              {{ quantityLabel(row as PosReceiptLine) }}
            </template>
          </el-table-column>
          <el-table-column label="Сумма" width="120" align="right">
            <template #default="{ row }">
              {{ formatKopecks((row as PosReceiptLine).amount_kopecks) }}
            </template>
          </el-table-column>
          <el-table-column label="Коэф." width="90" align="right">
            <template #default="{ row }">
              {{ formatQuantity((row as PosReceiptLine).unit_factor, 6) }}
            </template>
          </el-table-column>
          <el-table-column label="Номенклатура" min-width="220">
            <template #default="{ row }">
              <span v-if="(row as PosReceiptLine).nomenclature_name">
                {{ (row as PosReceiptLine).nomenclature_name }}
              </span>
              <el-tag v-else type="warning" size="small">Не сопоставлено</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="" width="130" align="right">
            <template #default="{ row }">
              <el-button
                v-if="
                  canAll(CAN.posReceiptsMap) &&
                  detail?.status !== 'posted' &&
                  !(row as PosReceiptLine).nomenclature_id
                "
                text
                @click="openMap(row as PosReceiptLine)"
              >
                Сопоставить
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-collapse class="raw">
          <el-collapse-item title="Исходные данные из DoKa" name="raw">
            <pre class="raw-json">{{ JSON.stringify(detail.raw, null, 2) }}</pre>
          </el-collapse-item>
        </el-collapse>
      </template>

      <template #footer>
        <el-button @click="detailOpen = false">Закрыть</el-button>
        <el-button :loading="detailPending" @click="reloadDetail">
          Обновить
        </el-button>
        <el-button
          v-if="
            canAll(CAN.posReceiptsManage) &&
            detail &&
            ['new', 'ready', 'needs_stock', 'failed'].includes(detail.status)
          "
          type="primary"
          :loading="postingOne"
          @click="postOne"
        >
          Провести
        </el-button>
      </template>
    </el-dialog>

    <PosMapDialog
      v-if="detail && mapLine"
      v-model="mapOpen"
      :source-id="detail.source_id"
      :product-guid="mapLine.product_guid"
      :product-name="mapLine.product_name"
      :product-unit="mapLine.unit"
      :unit-factor="mapLine.unit_factor"
      @mapped="onMapped"
    />
  </div>
</template>

<script setup lang="ts">
import { formatKopecks, formatQuantity } from "@md/money";
import type { components } from "@md/api-client";
import { ElMessage, ElMessageBox } from "element-plus";

import { CAN } from "~/utils/access";

definePageMeta({ permissions: CAN.posReceiptsOpen });

type PosReceipt = components["schemas"]["PosReceiptSchema"];
type PosReceiptDetail = components["schemas"]["PosReceiptDetailSchema"];
type PosReceiptLine = components["schemas"]["PosReceiptLineSchema"];
type PosSource = components["schemas"]["PosSourceSchema"];

const PAGE_SIZE = 20;

const STATUS_LABELS: Record<string, string> = {
  new: "Новый",
  needs_mapping: "Нужно сопоставить",
  ready: "Готов к проведению",
  needs_stock: "Нет остатка",
  posted: "Проведён",
  failed: "Ошибка",
  ignored: "Пропущен",
};

const KIND_LABELS: Record<string, string> = {
  sale: "Продажа",
  return: "Возврат",
};

const api = useApi();

const items = ref<PosReceipt[]>([]);
const total = ref(0);
const page = ref(1);
const pending = ref(false);
const error = ref("");
const notice = ref("");

const sources = ref<PosSource[]>([]);
const sourceFilter = ref<string | null>(null);
const statusFilter = ref<string | null>(null);
const range = ref<string[] | null>(null);

const detailOpen = ref(false);
const detail = ref<PosReceiptDetail | null>(null);
const detailPending = ref(false);
const detailError = ref("");
const posting = ref(false);
const postingOne = ref(false);

const mapOpen = ref(false);
const mapLine = ref<PosReceiptLine | null>(null);

function statusType(status: string): "success" | "warning" | "danger" | "info" {
  if (status === "posted" || status === "ready") return "success";
  if (status === "failed") return "danger";
  if (status === "needs_mapping" || status === "needs_stock") return "warning";
  return "info";
}

function paymentLabel(kind: string): string {
  const labels: Record<string, string> = {
    card: "Карта",
    cash: "Наличные",
    ecash: "Электронные",
  };
  return labels[kind] ?? kind;
}

function formatDate(value: string): string {
  return new Date(value).toLocaleString("ru-RU", {
    dateStyle: "short",
    timeStyle: "short",
  });
}

function shortGuid(value: string | null | undefined): string {
  if (!value) return "—";
  return value.length > 20 ? `${value.slice(0, 8)}…${value.slice(-4)}` : value;
}

function quantityLabel(line: PosReceiptLine): string {
  return line.unit
    ? `${formatQuantity(line.quantity, 6)} ${line.unit}`
    : formatQuantity(line.quantity, 6);
}

function reasonOf(status: number, body: unknown, fallback: string): string {
  const message = (body as { message?: string } | undefined)?.message;
  if (message) return message;
  if (status === 403) return "Нет прав на это действие";
  if (status === 404) return "Чек не найден";
  if (status === 409) return "Чек уже проведён";
  if (status === 422) return "Проверьте параметры запроса";
  return `${fallback}: ${status}`;
}

function isoBoundary(value: string, endOfDay: boolean): string {
  const date = new Date(`${value}T${endOfDay ? "23:59:59.999" : "00:00:00"}`);
  return date.toISOString();
}

async function load(): Promise<void> {
  pending.value = true;
  error.value = "";

  try {
    const { data, response } = await api.GET("/api/pos/receipts", {
      params: {
        query: {
          source_id: sourceFilter.value ?? undefined,
          status: statusFilter.value || undefined,
          date_from: range.value?.[0]
            ? isoBoundary(range.value[0], false)
            : undefined,
          date_to: range.value?.[1]
            ? isoBoundary(range.value[1], true)
            : undefined,
          limit: PAGE_SIZE,
          offset: (page.value - 1) * PAGE_SIZE,
        },
      },
    });

    if (!response.ok || !data) {
      throw new Error(reasonOf(response.status, null, "Не удалось загрузить чеки"));
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

function applyFilters(): void {
  page.value = 1;
  void load();
}

async function loadSources(): Promise<void> {
  if (!canAll(CAN.posSourcesOpen)) {
    sources.value = [];
    return;
  }

  const { data, response } = await api.GET("/api/pos/sources", {});
  sources.value = response.ok && data ? data : [];
}

async function openDetail(id: string): Promise<void> {
  detailError.value = "";
  detail.value = null;
  detailOpen.value = true;
  await loadDetail(id);
}

async function loadDetail(id: string): Promise<void> {
  detailPending.value = true;
  detailError.value = "";

  try {
    const { data, response } = await api.GET("/api/pos/receipts/{receipt_id}", {
      params: { path: { receipt_id: id } },
    });

    if (!response.ok || !data) {
      throw new Error(
        reasonOf(response.status, null, "Не удалось загрузить чек"),
      );
    }

    detail.value = data;
  } catch (cause) {
    detailError.value =
      cause instanceof Error ? cause.message : "Ошибка загрузки";
  } finally {
    detailPending.value = false;
  }
}

async function reloadDetail(): Promise<void> {
  if (detail.value) {
    await loadDetail(detail.value.id);
  }
}

async function postOne(): Promise<void> {
  if (!detail.value) return;

  postingOne.value = true;
  detailError.value = "";

  try {
    const { response, error: failure } = await api.POST(
      "/api/pos/receipts/{receipt_id}/post",
      { params: { path: { receipt_id: detail.value.id } } },
    );

    if (!response.ok) {
      throw new Error(
        reasonOf(response.status, failure, "Не удалось провести чек"),
      );
    }

    ElMessage.success("Чек проведён");
    await Promise.all([reloadDetail(), load()]);
  } catch (cause) {
    const message =
      cause instanceof Error ? cause.message : "Ошибка проведения";
    await reloadDetail();
    detailError.value = message;
  } finally {
    postingOne.value = false;
  }
}

async function postPending(): Promise<void> {
  try {
    await ElMessageBox.confirm(
      "Провести до 50 чеков, ожидающих склад? Недостаток остатка останется в статусе «Нет остатка».",
      "Проведение чеков DoKa",
      { confirmButtonText: "Провести", cancelButtonText: "Отмена" },
    );
  } catch {
    return;
  }

  posting.value = true;
  error.value = "";

  try {
    const { data, response, error: failure } = await api.POST(
      "/api/pos/receipts/post-pending",
      { body: { limit: 50 } },
    );

    if (!response.ok || !data) {
      throw new Error(
        reasonOf(response.status, failure, "Не удалось провести чеки"),
      );
    }

    notice.value = `Проведено: ${data.posted}, ждут: ${data.pending}, ошибок: ${data.failed}`;
    await load();
  } catch (cause) {
    error.value =
      cause instanceof Error ? cause.message : "Ошибка проведения";
  } finally {
    posting.value = false;
  }
}

function openMap(line: PosReceiptLine): void {
  mapLine.value = line;
  mapOpen.value = true;
}

async function onMapped(): Promise<void> {
  await Promise.all([reloadDetail(), load()]);
}

onMounted(async () => {
  await Promise.all([load(), loadSources()]);
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

.status-error {
  margin-top: 4px;
  line-height: 1.3;
}

.pager {
  margin-top: 16px;
  justify-content: flex-end;
}

.detail-error {
  margin: 16px 0 0;
}

.lines {
  margin-top: 16px;
}

.raw {
  margin-top: 16px;
}

.raw-json {
  margin: 0;
  max-height: 340px;
  overflow: auto;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
