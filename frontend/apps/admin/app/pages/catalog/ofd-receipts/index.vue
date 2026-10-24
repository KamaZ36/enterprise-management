<template>
  <div class="page">
    <h1 class="page__title">Чеки ОФД</h1>
    <p class="page__subtitle">
      Чеки из ОФД попадают на склад по привязке кассы. Пока товар не сопоставлен
      с номенклатурой, чек не проводится.
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
        v-if="canAll(CAN.ofdReceiptsSync)"
        type="primary"
        @click="openSync"
      >
        Загрузить из ОФД
      </el-button>
      <el-button
        v-if="canAll(CAN.ofdReceiptsManage)"
        :loading="posting"
        @click="postReady"
      >
        Провести готовые
      </el-button>
      <el-select
        v-model="statusFilter"
        placeholder="Все статусы"
        clearable
        style="width: 190px"
        @change="applyFilters"
      >
        <el-option
          v-for="(label, value) in STATUS_LABELS"
          :key="value"
          :label="label"
          :value="value"
        />
      </el-select>
      <el-input
        v-model="regFilter"
        placeholder="РНМ кассы"
        clearable
        style="width: 210px"
        @keyup.enter="applyFilters"
        @clear="applyFilters"
      />
      <el-button :loading="pending" @click="load">Обновить</el-button>
    </div>

    <el-card shadow="never">
      <el-table :data="items" v-loading="pending" empty-text="Чеков пока нет">
        <el-table-column label="Дата" min-width="145">
          <template #default="{ row }">
            {{ formatDate((row as OfdReceipt).doc_datetime) }}
          </template>
        </el-table-column>
        <el-table-column label="Касса" min-width="170">
          <template #default="{ row }">
            <div>{{ (row as OfdReceipt).reg_number }}</div>
            <div class="muted">док. {{ (row as OfdReceipt).doc_number }}</div>
          </template>
        </el-table-column>
        <el-table-column label="Точка" min-width="150">
          <template #default="{ row }">
            {{ (row as OfdReceipt).org_unit_name ?? "Не определена" }}
          </template>
        </el-table-column>
        <el-table-column label="Операция" min-width="150">
          <template #default="{ row }">
            {{ operationLabel(row as OfdReceipt) }}
          </template>
        </el-table-column>
        <el-table-column label="Сумма" width="130" align="right">
          <template #default="{ row }">
            {{ formatKopecks((row as OfdReceipt).total_kopecks) }}
          </template>
        </el-table-column>
        <el-table-column label="Строки" width="100" align="center">
          <template #default="{ row }">
            {{ (row as OfdReceipt).line_count }}
            <span v-if="(row as OfdReceipt).unmapped_count" class="muted">
              ({{ (row as OfdReceipt).unmapped_count }} без пары)
            </span>
          </template>
        </el-table-column>
        <el-table-column label="Статус" min-width="145">
          <template #default="{ row }">
            <el-tag :type="statusType((row as OfdReceipt).status)">
              {{
                STATUS_LABELS[(row as OfdReceipt).status] ??
                (row as OfdReceipt).status
              }}
            </el-tag>
            <div v-if="(row as OfdReceipt).error" class="muted status-error">
              {{ (row as OfdReceipt).error }}
            </div>
          </template>
        </el-table-column>
        <el-table-column label="" width="110" align="right">
          <template #default="{ row }">
            <el-button text @click="openDetail((row as OfdReceipt).id)">
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

    <el-dialog v-model="syncOpen" title="Загрузить чеки из ОФД" width="560">
      <el-alert
        v-if="syncError"
        :title="syncError"
        type="error"
        :closable="false"
        show-icon
        class="page__error"
      />

      <el-form label-position="top">
        <el-form-item label="Касса (РНМ)">
          <el-select
            v-model="syncForm.reg_number"
            filterable
            allow-create
            default-first-option
            placeholder="Выберите кассу или введите РНМ"
            style="width: 100%"
          >
            <el-option
              v-for="register in registers"
              :key="register.id"
              :label="`${register.name} · ${register.reg_number ?? 'без РНМ'}`"
              :value="register.reg_number ?? ''"
              :disabled="!register.reg_number"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="С">
          <el-date-picker
            v-model="syncForm.date_from"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
            placeholder="Начало периода"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="По">
          <el-date-picker
            v-model="syncForm.date_to"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
            placeholder="Конец периода"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="syncOpen = false">Отмена</el-button>
        <el-button type="primary" :loading="syncing" @click="runSync">
          Загрузить
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailOpen" title="Чек ОФД" width="1050">
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
            {{ formatDate(detail.doc_datetime) }}
          </el-descriptions-item>
          <el-descriptions-item label="Сумма">
            {{ formatKopecks(detail.total_kopecks) }}
          </el-descriptions-item>
          <el-descriptions-item label="Касса">
            {{ detail.reg_number }}
          </el-descriptions-item>
          <el-descriptions-item label="Документ">
            {{ detail.doc_number }}
          </el-descriptions-item>
          <el-descriptions-item label="ФПД">
            {{ detail.fiscal_sign }}
          </el-descriptions-item>
          <el-descriptions-item label="Точка">
            {{ detail.org_unit_name ?? "Не определена" }}
          </el-descriptions-item>
          <el-descriptions-item label="ФН">
            {{ detail.fn_number }}
          </el-descriptions-item>
          <el-descriptions-item label="ИНН">
            {{ detail.inn }}
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

        <el-table
          :data="detail.lines"
          class="lines"
          empty-text="В чеке нет строк"
        >
          <el-table-column label="№" width="55" prop="line_number" />
          <el-table-column label="Товар в чеке" min-width="220" prop="name" />
          <el-table-column label="Штрихкод" min-width="155">
            <template #default="{ row }">
              {{ (row as OfdReceiptLine).barcode ?? "—" }}
            </template>
          </el-table-column>
          <el-table-column label="Кол-во" width="100" align="right">
            <template #default="{ row }">
              {{ quantityLabel(row as OfdReceiptLine) }}
            </template>
          </el-table-column>
          <el-table-column label="Сумма" width="120" align="right">
            <template #default="{ row }">
              {{ formatKopecks((row as OfdReceiptLine).total_kopecks) }}
            </template>
          </el-table-column>
          <el-table-column label="Номенклатура" min-width="220">
            <template #default="{ row }">
              <span v-if="(row as OfdReceiptLine).nomenclature_name">
                {{ (row as OfdReceiptLine).nomenclature_name }}
              </span>
              <el-tag v-else type="warning" size="small">
                Не сопоставлено
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="" width="130" align="right">
            <template #default="{ row }">
              <el-button
                v-if="
                  canAll(CAN.ofdReceiptsManage) &&
                  can('nomenclature.read') &&
                  detail?.status !== 'posted'
                "
                text
                @click="openMap(row as OfdReceiptLine)"
              >
                Сопоставить
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-collapse class="raw">
          <el-collapse-item title="Исходный JSON из ОФД" name="raw">
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
            canAll(CAN.ofdReceiptsManage) && detail?.status === 'ready'
          "
          type="primary"
          :loading="postingOne"
          @click="postOne"
        >
          Провести
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="mapOpen" title="Сопоставить товар" width="620">
      <el-alert
        v-if="mapError"
        :title="mapError"
        type="error"
        :closable="false"
        show-icon
        class="page__error"
      />

      <div v-if="mapLine" class="map-line">
        <div class="map-line__name">{{ mapLine.name }}</div>
        <div class="muted">
          Штрихкод: {{ mapLine.barcode ?? "нет" }} ·
          {{ quantityLabel(mapLine) }}
        </div>
      </div>

      <div class="map-search">
        <el-input
          v-model="mapSearch"
          placeholder="Название или артикул"
          clearable
          @keyup.enter="searchNomenclatures"
          @clear="searchNomenclatures"
        />
        <el-button :loading="mapSearching" @click="searchNomenclatures">
          Найти
        </el-button>
      </div>

      <el-select
        v-model="mapForm.nomenclature_id"
        filterable
        placeholder="Выберите номенклатуру"
        style="width: 100%"
      >
        <el-option
          v-for="item in nomenclatureOptions"
          :key="item.id"
          :label="`${item.name} · ${item.sku}`"
          :value="item.id"
        />
      </el-select>

      <el-checkbox v-model="mapForm.remember_barcode" class="remember">
        Запомнить штрихкод для следующих чеков
      </el-checkbox>

      <template #footer>
        <el-button @click="mapOpen = false">Отмена</el-button>
        <el-button
          type="primary"
          :loading="mapping"
          :disabled="!mapForm.nomenclature_id"
          @click="saveMapping"
        >
          Сопоставить
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { formatKopecks } from "@md/money";
import type { components } from "@md/api-client";
import { ElMessage, ElMessageBox } from "element-plus";

import { CAN } from "~/utils/access";

definePageMeta({ permissions: CAN.ofdReceiptsOpen });

type OfdReceipt = components["schemas"]["OfdReceiptSchema"];
type OfdReceiptDetail = components["schemas"]["OfdReceiptDetailSchema"];
type OfdReceiptLine = components["schemas"]["OfdReceiptLineSchema"];
type Nomenclature = components["schemas"]["NomenclatureSchema"];
type CashRegister = components["schemas"]["CashRegisterSchema"];

const PAGE_SIZE = 20;

const STATUS_LABELS: Record<string, string> = {
  new: "Новый",
  needs_location: "Нет склада",
  needs_mapping: "Нужно сопоставить",
  ready: "Готов к проведению",
  posted: "Проведён",
  failed: "Ошибка",
  ignored: "Вручную",
};

const UNIT_LABELS: Record<string, string> = {
  "0": "шт",
  "1": "г",
  "2": "кг",
  "3": "т",
  "4": "см",
  "5": "дм",
  "6": "м",
  "10": "мл",
  "11": "л",
  PIECE: "шт",
  GRAM: "г",
  KILOGRAM: "кг",
  TON: "т",
  LITER: "л",
  MILLILITER: "мл",
  METER: "м",
};

const api = useApi();
const { can } = useCurrentUser();

const items = ref<OfdReceipt[]>([]);
const total = ref(0);
const page = ref(1);
const pending = ref(false);
const error = ref("");
const notice = ref("");

const statusFilter = ref<string | null>(null);
const regFilter = ref("");

const registers = ref<CashRegister[]>([]);

const syncOpen = ref(false);
const syncing = ref(false);
const syncError = ref("");
const syncForm = reactive({
  reg_number: "",
  date_from: "",
  date_to: "",
});

const detailOpen = ref(false);
const detail = ref<OfdReceiptDetail | null>(null);
const detailPending = ref(false);
const detailError = ref("");
const postingOne = ref(false);
const posting = ref(false);

const mapOpen = ref(false);
const mapLine = ref<OfdReceiptLine | null>(null);
const mapError = ref("");
const mapping = ref(false);
const mapSearch = ref("");
const mapSearching = ref(false);
const nomenclatureOptions = ref<Nomenclature[]>([]);
const mapForm = reactive({
  nomenclature_id: "",
  remember_barcode: true,
});

function statusType(status: string): "success" | "warning" | "danger" | "info" {
  if (status === "posted" || status === "ready") return "success";
  if (status === "failed") return "danger";
  if (status === "needs_mapping" || status === "needs_location") {
    return "warning";
  }
  return "info";
}

function operationLabel(receipt: OfdReceipt): string {
  const labels: Record<string, string> = {
    Income: "Приход",
    "Refund income": "Возврат прихода",
    Expense: "Расход",
    "Refund expenses": "Возврат расхода",
  };
  return labels[receipt.operation_type] ?? receipt.operation_type;
}

function quantityLabel(line: OfdReceiptLine): string {
  const quantity = Number(line.quantity);
  const unit = line.unit ? (UNIT_LABELS[line.unit] ?? "") : "";
  const formatted = Number.isFinite(quantity)
    ? quantity.toLocaleString("ru-RU", { maximumFractionDigits: 3 })
    : line.quantity;
  return unit ? `${formatted} ${unit}` : formatted;
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
  if (status === 404) return "Чек или касса не найдены";
  if (status === 422) return "Проверьте заполненные поля";
  return `${fallback}: ${status}`;
}

function toLocalInput(date: Date): string {
  const pad = (value: number) => String(value).padStart(2, "0");
  return [
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`,
    `${pad(date.getHours())}:${pad(date.getMinutes())}:00`,
  ].join("T");
}

async function load(): Promise<void> {
  pending.value = true;
  error.value = "";

  try {
    const { data, response } = await api.GET("/api/fiscal/ofd/receipts", {
      params: {
        query: {
          status: statusFilter.value || undefined,
          reg_number: regFilter.value.trim() || undefined,
          limit: PAGE_SIZE,
          offset: (page.value - 1) * PAGE_SIZE,
        },
      },
    });

    if (!response.ok || !data) {
      throw new Error(
        reasonOf(response.status, null, "Не удалось загрузить чеки"),
      );
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
  load();
}

async function loadRegisters(): Promise<void> {
  try {
    const { data, response } = await api.GET("/api/fiscal/cash-registers", {});
    registers.value = response.ok && data ? data : [];
  } catch {
    // Список касс не критичен: РНМ можно ввести вручную.
    registers.value = [];
  }
}

function openSync(): void {
  syncError.value = "";
  syncForm.reg_number =
    registers.value.find((item) => item.reg_number)?.reg_number ?? "";
  const now = new Date();
  const startOfDay = new Date(now);
  startOfDay.setHours(0, 0, 0, 0);
  syncForm.date_to = toLocalInput(now);
  syncForm.date_from = toLocalInput(startOfDay);
  syncOpen.value = true;
}

async function runSync(): Promise<void> {
  if (!syncForm.reg_number.trim()) {
    syncError.value = "Укажите РНМ кассы";
    return;
  }
  if (!syncForm.date_from || !syncForm.date_to) {
    syncError.value = "Укажите период";
    return;
  }

  syncing.value = true;
  syncError.value = "";

  try {
    const { data, response, error: failure } = await api.POST(
      "/api/fiscal/ofd/receipts/sync",
      {
        body: {
          reg_number: syncForm.reg_number.trim(),
          date_from: syncForm.date_from,
          date_to: syncForm.date_to,
        },
      },
    );

    if (!response.ok || !data) {
      throw new Error(reasonOf(response.status, failure, "Не удалось загрузить"));
    }

    syncOpen.value = false;
    notice.value = `ОФД: найдено ${data.receipts_found}, сохранено ${
      data.receipts_created
    }${data.error ? `. ${data.error}` : ""}`;
    await load();
  } catch (cause) {
    syncError.value =
      cause instanceof Error ? cause.message : "Ошибка синхронизации";
  } finally {
    syncing.value = false;
  }
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
    const { data, response } = await api.GET(
      "/api/fiscal/ofd/receipts/{receipt_id}",
      { params: { path: { receipt_id: id } } },
    );

    if (!response.ok || !data) {
      throw new Error(
        reasonOf(response.status, null, "Не удалось загрузить чек"),
      );
    }

    detail.value = data;
  } catch (cause) {
    detailError.value = cause instanceof Error ? cause.message : "Ошибка загрузки";
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
      "/api/fiscal/ofd/receipts/{receipt_id}/post",
      { params: { path: { receipt_id: detail.value.id } } },
    );

    if (!response.ok) {
      throw new Error(reasonOf(response.status, failure, "Не удалось провести"));
    }

    ElMessage.success("Чек проведён");
    await Promise.all([reloadDetail(), load()]);
  } catch (cause) {
    const message =
      cause instanceof Error ? cause.message : "Ошибка проведения";
    // Бэкенд мог пометить чек как failed — показываем актуальный статус.
    await reloadDetail();
    detailError.value = message;
  } finally {
    postingOne.value = false;
  }
}

async function postReady(): Promise<void> {
  try {
    await ElMessageBox.confirm(
      "Провести до 50 готовых чеков? Недостаток остатка попадёт в ошибки.",
      "Проведение чеков",
      { confirmButtonText: "Провести", cancelButtonText: "Отмена" },
    );
  } catch {
    return;
  }

  posting.value = true;
  error.value = "";

  try {
    const { data, response, error: failure } = await api.POST(
      "/api/fiscal/ofd/receipts/post-ready",
      { body: { limit: 50 } },
    );

    if (!response.ok || !data) {
      throw new Error(reasonOf(response.status, failure, "Не удалось провести"));
    }

    notice.value = `Проведено: ${data.posted}, ошибок: ${data.failed}`;
    await load();
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Ошибка проведения";
  } finally {
    posting.value = false;
  }
}

async function openMap(line: OfdReceiptLine): Promise<void> {
  mapLine.value = line;
  mapError.value = "";
  mapSearch.value = line.name;
  mapForm.nomenclature_id = line.nomenclature_id ?? "";
  mapForm.remember_barcode = true;
  mapOpen.value = true;
  await searchNomenclatures();
}

async function searchNomenclatures(): Promise<void> {
  mapSearching.value = true;

  try {
    const { data, response } = await api.GET("/api/catalog/nomenclatures", {
      params: {
        query: {
          search: mapSearch.value.trim() || undefined,
          limit: 30,
          offset: 0,
        },
      },
    });

    if (!response.ok || !data) {
      throw new Error(
        reasonOf(response.status, null, "Не удалось найти товары"),
      );
    }

    nomenclatureOptions.value = data.items;
  } catch (cause) {
    mapError.value = cause instanceof Error ? cause.message : "Ошибка поиска";
    nomenclatureOptions.value = [];
  } finally {
    mapSearching.value = false;
  }
}

async function saveMapping(): Promise<void> {
  const line = mapLine.value;
  if (!line || !mapForm.nomenclature_id) return;

  mapping.value = true;
  mapError.value = "";

  try {
    const { response, error: failure } = await api.POST(
      "/api/fiscal/ofd/lines/{line_id}/map",
      {
        params: { path: { line_id: line.id } },
        body: {
          nomenclature_id: mapForm.nomenclature_id,
          remember_barcode: mapForm.remember_barcode,
        },
      },
    );

    if (!response.ok) {
      throw new Error(
        reasonOf(response.status, failure, "Не удалось сопоставить"),
      );
    }

    mapOpen.value = false;
    ElMessage.success("Товар сопоставлен");
    await Promise.all([reloadDetail(), load()]);
  } catch (cause) {
    mapError.value =
      cause instanceof Error ? cause.message : "Ошибка сопоставления";
  } finally {
    mapping.value = false;
  }
}

onMounted(async () => {
  await Promise.all([load(), loadRegisters()]);
});
</script>

<style scoped>
.muted {
  color: var(--el-text-color-secondary);
  font-size: 12px;
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

.map-line {
  margin-bottom: 16px;
}

.map-line__name {
  font-weight: 600;
  margin-bottom: 4px;
}

.map-search {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.remember {
  margin-top: 12px;
}
</style>
