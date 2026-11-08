<template>
  <div class="page">
    <h1 class="page__title">Ввод начальных остатков</h1>
    <p class="page__subtitle">
      Документы для перехода с бумажного учёта: количество, себестоимость,
      партия и срок годности. После проведения остатки попадают в баланс и
      отчёты.
    </p>

    <div class="page__toolbar">
      <el-button
        v-if="canManage"
        type="primary"
        @click="openCreate"
      >
        Новый ввод остатков
      </el-button>
      <el-input
        v-model="search"
        placeholder="Номер или комментарий"
        clearable
        style="max-width: 320px"
        @keyup.enter="applySearch"
        @clear="applySearch"
      />
      <el-button @click="applySearch">Найти</el-button>
      <el-select
        v-model="locationId"
        placeholder="Все точки"
        clearable
        style="width: 260px"
        @change="reload"
      >
        <LocationOptions :locations="locations" />
      </el-select>
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

    <el-table
      v-loading="pending"
      :data="items"
      stripe
      border
      @row-click="openDetail"
    >
      <el-table-column label="Дата" width="120">
        <template #default="{ row }">{{ formatDate(row.occurred_at) }}</template>
      </el-table-column>
      <el-table-column label="Номер" width="150">
        <template #default="{ row }">{{ row.number ?? "—" }}</template>
      </el-table-column>
      <el-table-column label="Подразделение" min-width="180">
        <template #default="{ row }">{{ locationName(row.org_unit_id) }}</template>
      </el-table-column>
      <el-table-column label="Комментарий" min-width="220">
        <template #default="{ row }">{{ row.comment ?? "—" }}</template>
      </el-table-column>
      <el-table-column prop="line_count" label="Строк" width="90" align="right" />
      <el-table-column label="Сумма" width="150" align="right">
        <template #default="{ row }">{{ formatKopecks(row.total_kopecks) }}</template>
      </el-table-column>
      <el-table-column label="Статус" width="120">
        <template #default="{ row }">
          <el-tag :type="row.status === 'posted' ? 'success' : 'info'" effect="light">
            {{ row.status === "posted" ? "проведён" : "черновик" }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column v-if="canManage" width="230" align="right">
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'draft'"
            text
            :disabled="busy"
            @click.stop="askPost(row as OpeningBalanceListItem)"
          >
            Провести
          </el-button>
          <el-button
            v-if="row.status === 'draft'"
            text
            type="danger"
            :disabled="busy"
            @click.stop="askDelete(row as OpeningBalanceListItem)"
          >
            Удалить
          </el-button>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="Вводов остатков пока нет" />
      </template>
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

    <el-dialog
      v-model="formOpen"
      :title="editingId ? 'Изменить ввод остатков' : 'Ввод начальных остатков'"
      width="900"
    >
      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="Документ для перехода с бумажного учёта"
        description="Укажите количество, себестоимость, партию и срок годности. Номенклатуру можно создать прямо из строки, если её ещё нет в справочнике."
        class="page__error"
      />

      <el-alert
        v-if="formError"
        :title="formError"
        type="error"
        :closable="false"
        show-icon
        class="page__error"
      />

      <el-form label-position="top" @submit.prevent>
        <div class="form-grid">
          <el-form-item label="Подразделение">
            <el-select
              v-model="form.org_unit_id"
              style="width: 100%"
              :disabled="Boolean(editingId)"
            >
              <LocationOptions :locations="locations" />
            </el-select>
          </el-form-item>
          <el-form-item label="Дата и время">
            <el-date-picker
              v-model="form.occurred_at"
              type="datetime"
              style="width: 100%"
            />
          </el-form-item>
        </div>

        <el-form-item label="Комментарий">
          <el-input
            v-model="form.comment"
            placeholder="Например: перенос остатков на 01.11.2026"
          />
        </el-form-item>

        <div class="lines-head">
          <span>Строки документа</span>
          <el-button size="small" @click="addLine">Добавить строку</el-button>
        </div>

        <div class="line line--head">
          <span class="line__name">Номенклатура</span>
          <span class="line__qty">Количество</span>
          <span class="line__qty">Цена, ₽</span>
          <span class="line__lot">Партия</span>
          <span class="line__date">Годен до</span>
          <span class="line__action" />
        </div>

        <div v-for="(line, index) in lines" :key="index" class="line">
          <el-select
            v-model="line.nomenclature_id"
            filterable
            remote
            placeholder="Начните вводить название, артикул или штрихкод"
            :remote-method="(query: string) => searchNomenclature(line, query)"
            @focus="line.query = ''"
            class="line__name"
          >
            <el-option
              v-for="option in line.options"
              :key="option.id"
              :label="option.sku ? `${option.name} · ${option.sku}` : option.name"
              :value="option.id"
            />
            <template #empty>
              <div class="nomenclature-empty">
                <template v-if="line.query">
                  <span>Ничего не найдено</span>
                  <el-button
                    v-if="can('nomenclature.create')"
                    text
                    type="primary"
                    size="small"
                    @click.stop="openQuickNomenclature(line)"
                  >
                    Создать «{{ line.query }}»
                  </el-button>
                </template>
                <span v-else>Начните вводить название или артикул</span>
              </div>
            </template>
          </el-select>

          <el-input v-model="line.quantity" class="line__qty" placeholder="например 12,5" />
          <el-input v-model="line.unit_cost" class="line__qty" placeholder="например 450,50" />
          <el-input v-model="line.lot_code" class="line__lot" placeholder="Партия" />
          <el-date-picker
            v-model="line.expires_at"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="Годен до"
            class="line__date"
          />
          <el-button
            text
            type="danger"
            :disabled="lines.length === 1"
            @click="removeLine(index)"
          >
            Убрать
          </el-button>
        </div>
      </el-form>

      <template #footer>
        <el-button @click="formOpen = false">Отмена</el-button>
        <el-button :loading="saving" :disabled="!canSubmit" @click="save(false)">
          {{ editingId ? "Сохранить" : "Сохранить черновик" }}
        </el-button>
        <el-button
          v-if="!editingId"
          type="primary"
          :loading="saving"
          :disabled="!canSubmit"
          @click="save(true)"
        >
          Сохранить и провести
        </el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="drawerOpen" :title="drawerTitle" size="680px">
      <template v-if="detail">
        <el-alert
          v-if="detailError"
          :title="detailError"
          type="error"
          :closable="false"
          show-icon
          class="page__error"
        />

        <el-descriptions :column="2" border>
          <el-descriptions-item label="Номер">
            {{ detail.number ?? "—" }}
          </el-descriptions-item>
          <el-descriptions-item label="Дата">
            {{ formatDate(detail.occurred_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="Подразделение">
            {{ locationName(detail.org_unit_id) }}
          </el-descriptions-item>
          <el-descriptions-item label="Статус">
            <el-tag
              :type="detail.status === 'posted' ? 'success' : 'info'"
              effect="light"
            >
              {{ detail.status === "posted" ? "проведён" : "черновик" }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="Проведён">
            {{ detail.posted_at ? formatDate(detail.posted_at) : "нет" }}
          </el-descriptions-item>
          <el-descriptions-item v-if="detail.comment" label="Комментарий" :span="2">
            {{ detail.comment }}
          </el-descriptions-item>
        </el-descriptions>

        <el-table :data="detail.lines" border class="lines">
          <el-table-column prop="nomenclature_name" label="Номенклатура" min-width="200" />
          <el-table-column label="Количество" width="120" align="right">
            <template #default="{ row }">{{ formatQuantity(row.quantity) }}</template>
          </el-table-column>
          <el-table-column label="Цена" width="110" align="right">
            <template #default="{ row }">{{ formatQuantity(row.unit_cost, 2) }}</template>
          </el-table-column>
          <el-table-column label="Сумма" width="130" align="right">
            <template #default="{ row }">{{ formatKopecks(row.total_kopecks) }}</template>
          </el-table-column>
          <el-table-column label="Партия" width="150">
            <template #default="{ row }">
              <span>{{ row.lot_code ?? "—" }}</span>
              <div v-if="row.expires_at" class="muted hint">
                до {{ formatDate(row.expires_at) }}
              </div>
            </template>
          </el-table-column>
        </el-table>

        <div
          v-if="detail.status !== 'posted' && canManage"
          class="drawer-actions"
        >
          <el-button @click="openEdit">Редактировать</el-button>
          <el-button type="primary" :loading="posting" @click="askPost(detail)">
            Провести
          </el-button>
          <el-button type="danger" text :disabled="busy" @click="askDelete(detail)">
            Удалить
          </el-button>
        </div>
      </template>
    </el-drawer>

    <QuickNomenclatureDialog ref="quickDialog" @selected="applyQuickNomenclature" />
  </div>
</template>

<script setup lang="ts">
import { CAN } from "~/utils/access";
import { formatKopecks, formatQuantity } from "@md/money";
import type { components } from "@md/api-client";
import { locationDisplay, type Location } from "~/utils/locations";

definePageMeta({ permissions: CAN.openingBalancesOpen });

type OpeningBalanceListItem =
  components["schemas"]["OpeningBalanceListItemSchema"];
type OpeningBalanceDetail =
  components["schemas"]["OpeningBalanceDetailSchema"];
type NomenclatureOption = {
  id: string;
  name: string;
  sku: string;
  requires_vetis?: boolean;
};
type NomenclatureLine = {
  nomenclature_id: string;
  options: NomenclatureOption[];
  query?: string;
};
type OpeningBalanceLine = NomenclatureLine & {
  quantity: string;
  unit_cost: string;
  lot_code: string;
  expires_at: string;
};

const PAGE_SIZE = 20;

const api = useApi();
const { can } = useCurrentUser();
const { confirm } = useConfirm();
const canManage = computed(
  () => can("inventory.opening_balance.manage"),
);

const items = ref<OpeningBalanceListItem[]>([]);
const locations = ref<Location[]>([]);
const locationId = ref<string | null>(null);
const total = ref(0);
const page = ref(1);
const search = ref("");
const applied = ref("");
const pending = ref(false);
const busy = ref(false);
const error = ref("");
const notice = ref("");

const formOpen = ref(false);
const saving = ref(false);
const formError = ref("");
const editingId = ref<string | null>(null);
const form = reactive({
  org_unit_id: "",
  occurred_at: new Date(),
  comment: "",
});
const lines = ref<OpeningBalanceLine[]>([emptyLine()]);

const drawerOpen = ref(false);
const detail = ref<OpeningBalanceDetail | null>(null);
const detailError = ref("");
const posting = ref(false);

const quickDialog = ref<{ show: (name?: string) => void } | null>(null);
const quickTarget = ref<NomenclatureLine | null>(null);

const canSubmit = computed(
  () =>
    Boolean(form.org_unit_id) &&
    lines.value.some(isCompleteLine),
);

const drawerTitle = computed(() =>
  detail.value
    ? `Ввод остатков от ${formatDate(detail.value.occurred_at)}`
    : "Ввод остатков",
);

function emptyLine(): OpeningBalanceLine {
  return {
    nomenclature_id: "",
    options: [],
    quantity: "",
    unit_cost: "",
    lot_code: "",
    expires_at: "",
  };
}

function isCompleteLine(line: OpeningBalanceLine): boolean {
  return (
    Boolean(line.nomenclature_id) &&
    Number(line.quantity) > 0 &&
    line.unit_cost !== "" &&
    Number(line.unit_cost) >= 0
  );
}

function locationName(id: string): string {
  return locationDisplay(
    locations.value.find((location) => location.id === id),
  );
}

function serverMessage(failure: unknown, fallback: string): string {
  const payload = failure as { message?: string } | undefined;

  return payload?.message ?? fallback;
}

function deleteReasonOf(status: number, fallback: string): string {
  if (status === 403) {
    return "Нет прав удалять ввод начальных остатков";
  }
  if (status === 404) {
    return "Документ не найден";
  }

  return `${fallback}: ${status}`;
}

async function loadLocations(): Promise<void> {
  if (!can("inventory.document.read")) {
    return;
  }

  const { data, response } = await api.GET("/api/inventory/locations", {});
  if (response.ok && data) {
    locations.value = data;
  }
}

async function load(): Promise<void> {
  pending.value = true;
  error.value = "";

  try {
    const { data, response } = await api.GET(
      "/api/inventory/opening-balances",
      {
        params: {
          query: {
            org_unit_id: locationId.value ?? undefined,
            limit: PAGE_SIZE,
            offset: (page.value - 1) * PAGE_SIZE,
            search: applied.value || undefined,
          },
        },
      },
    );

    if (!response.ok || !data) {
      throw new Error(
        `Не удалось загрузить ввод остатков: ${response.status}`,
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

function applySearch(): void {
  applied.value = search.value.trim();
  page.value = 1;
  void load();
}

function reload(): void {
  page.value = 1;
  void load();
}

function openCreate(): void {
  editingId.value = null;
  formError.value = "";
  notice.value = "";
  form.org_unit_id = locations.value[0]?.id ?? "";
  form.occurred_at = new Date();
  form.comment = "";
  lines.value = [emptyLine()];
  formOpen.value = true;
}

function openEdit(): void {
  const current = detail.value;
  if (!current) {
    return;
  }

  formError.value = "";
  notice.value = "";
  editingId.value = current.id;
  form.org_unit_id = current.org_unit_id;
  form.occurred_at = new Date(current.occurred_at);
  form.comment = current.comment ?? "";
  lines.value = current.lines.map((line) => ({
    nomenclature_id: line.nomenclature_id,
    quantity: String(line.quantity),
    unit_cost: String(line.unit_cost),
    lot_code: line.lot_code ?? "",
    expires_at: line.expires_at ?? "",
    options: [
      {
        id: line.nomenclature_id,
        name: line.nomenclature_name ?? line.nomenclature_id,
        sku: "",
      },
    ],
  }));
  drawerOpen.value = false;
  formOpen.value = true;
}

function addLine(): void {
  lines.value = [...lines.value, emptyLine()];
}

function removeLine(index: number): void {
  lines.value = lines.value.filter((_, position) => position !== index);
}

async function searchNomenclature(
  line: NomenclatureLine,
  query: string,
): Promise<void> {
  line.query = query.trim();

  const { data, response } = await api.GET("/api/catalog/nomenclatures", {
    params: { query: { search: query || undefined, limit: 20 } },
  });

  if (response.ok && data) {
    line.options = data.items;
  }
}

function openQuickNomenclature(line: NomenclatureLine): void {
  quickTarget.value = line;
  quickDialog.value?.show(line.query ?? "");
}

function applyQuickNomenclature(option: NomenclatureOption): void {
  const target = quickTarget.value;
  if (!target) {
    return;
  }

  if (!target.options.some((item) => item.id === option.id)) {
    target.options = [option, ...target.options];
  }
  target.nomenclature_id = option.id;
  target.query = "";
  notice.value = `Выбрана номенклатура «${option.name}»`;
  quickTarget.value = null;
}

function body() {
  return {
    occurred_at: form.occurred_at.toISOString(),
    comment: form.comment.trim() || null,
    lines: lines.value
      .filter(isCompleteLine)
      .map((line) => ({
        nomenclature_id: line.nomenclature_id,
        quantity: line.quantity,
        unit_cost: line.unit_cost,
        lot_code: line.lot_code.trim() || null,
        expires_at: line.expires_at || null,
      })),
  };
}

async function save(postAfterCreate: boolean): Promise<void> {
  if (editingId.value) {
    await update();
    return;
  }

  saving.value = true;
  formError.value = "";
  notice.value = "";

  try {
    const created = await api.POST("/api/inventory/opening-balances", {
      body: {
        org_unit_id: form.org_unit_id,
        ...body(),
      },
    });

    if (!created.response.ok || !created.data) {
      throw new Error(
        serverMessage(
          created.error,
          `Не удалось сохранить: ${created.response.status}`,
        ),
      );
    }

    const openingBalanceId = (
      created.data as unknown as { opening_balance_id: string }
    ).opening_balance_id;

    if (postAfterCreate) {
      const posted = await api.POST(
        "/api/inventory/opening-balances/{opening_balance_id}/post",
        { params: { path: { opening_balance_id: openingBalanceId } } },
      );

      if (!posted.response.ok) {
        formError.value = `Черновик создан, но не проведён: ${serverMessage(posted.error, String(posted.response.status))}`;
        await load();
        return;
      }

      notice.value = "Начальные остатки проведены";
    } else {
      notice.value = "Черновик ввода остатков сохранён";
    }

    formOpen.value = false;
    await reload();
  } catch (cause) {
    formError.value =
      cause instanceof Error ? cause.message : "Ошибка сохранения";
  } finally {
    saving.value = false;
  }
}

async function update(): Promise<void> {
  saving.value = true;
  formError.value = "";
  notice.value = "";

  try {
    const updated = await api.PATCH(
      "/api/inventory/opening-balances/{opening_balance_id}",
      {
        params: { path: { opening_balance_id: editingId.value ?? "" } },
        body: body(),
      },
    );

    if (!updated.response.ok) {
      throw new Error(
        serverMessage(
          updated.error,
          `Не удалось сохранить: ${updated.response.status}`,
        ),
      );
    }

    const editedId = editingId.value;
    formOpen.value = false;
    editingId.value = null;
    notice.value = "Изменения сохранены";
    if (editedId) {
      await openDetail({ id: editedId });
    }
    await load();
  } catch (cause) {
    formError.value =
      cause instanceof Error ? cause.message : "Ошибка сохранения";
  } finally {
    saving.value = false;
  }
}

async function openDetail(row: { id: string }): Promise<void> {
  detailError.value = "";

  const { data, response } = await api.GET(
    "/api/inventory/opening-balances/{opening_balance_id}",
    { params: { path: { opening_balance_id: row.id } } },
  );

  if (!response.ok || !data) {
    error.value = `Не удалось открыть ввод остатков: ${response.status}`;
    return;
  }

  detail.value = data;
  drawerOpen.value = true;
}

async function post(id: string): Promise<void> {
  posting.value = true;
  detailError.value = "";
  error.value = "";
  notice.value = "";

  try {
    const { response, error: failure } = await api.POST(
      "/api/inventory/opening-balances/{opening_balance_id}/post",
      { params: { path: { opening_balance_id: id } } },
    );

    if (!response.ok) {
      throw new Error(
        serverMessage(failure, `Не удалось провести: ${response.status}`),
      );
    }

    notice.value = "Начальные остатки проведены";

    if (drawerOpen.value) {
      await openDetail({ id });
    }
    await load();
  } catch (cause) {
    const message = cause instanceof Error ? cause.message : "Ошибка проведения";
    if (drawerOpen.value) {
      detailError.value = message;
    } else {
      error.value = message;
    }
  } finally {
    posting.value = false;
  }
}

async function remove(id: string): Promise<void> {
  busy.value = true;
  error.value = "";
  notice.value = "";

  try {
    const { response } = await api.DELETE(
      "/api/inventory/opening-balances/{opening_balance_id}",
      { params: { path: { opening_balance_id: id } } },
    );

    if (!response.ok) {
      throw new Error(
        deleteReasonOf(response.status, "Не удалось удалить ввод остатков"),
      );
    }

    notice.value = "Черновик ввода остатков удалён";
    detail.value = null;
    drawerOpen.value = false;
    await load();
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Ошибка удаления";
  } finally {
    busy.value = false;
  }
}

async function askPost(row: { id: string }): Promise<void> {
  if (!(await confirm({ title: "Провести документ?" }))) {
    return;
  }

  await post(row.id);
}

async function askDelete(row: { id: string }): Promise<void> {
  if (!(await confirm({ title: "Удалить черновик?", danger: true }))) {
    return;
  }

  await remove(row.id);
}

onMounted(async () => {
  await loadLocations();
  await load();
});
</script>

<style scoped>
.page__error {
  margin-bottom: 16px;
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

.lines {
  margin-top: 16px;
}

.lines-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 16px 0 8px;
}

.line {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}

.line__name {
  flex: 1;
}

.line__qty {
  width: 110px;
}

.line__lot {
  width: 130px;
}

.line__date {
  width: 150px;
}

.line__action {
  width: 74px;
}

.line--head {
  color: #909399;
  font-size: 12px;
  margin-bottom: 4px;
}

.nomenclature-empty {
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: flex-start;
  padding: 8px 12px;
  color: #909399;
  font-size: 13px;
}

.drawer-actions {
  display: flex;
  gap: 8px;
  margin-top: 16px;
}

.hint {
  font-size: 11px;
}
</style>
