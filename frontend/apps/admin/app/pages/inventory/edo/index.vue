<template>
  <div class="page">
    <h1 class="page__title">Входящие УПД</h1>
    <p class="page__subtitle">
      Ручная регистрация входящих документов ЭДО по точкам
    </p>

    <el-alert
      v-if="!canAll(CAN.edoDocumentsOpen)"
      title="Нет права видеть входящие УПД"
      description="Попросите доступ к документам ЭДО."
      type="warning"
      :closable="false"
      show-icon
      class="page__error"
    />

    <div v-if="canAll(CAN.edoDocumentsOpen)" class="page__toolbar">
      <el-select
        v-model="locationId"
        placeholder="Выберите точку"
        style="width: 280px"
        @change="reload"
      >
        <LocationOptions :locations="locations" />
      </el-select>
      <el-input
        v-model="filter"
        placeholder="Номер, поставщик или ID"
        style="width: 280px"
        clearable
        @input="onSearch"
      />
      <el-button
        v-if="canAll(CAN.edoDocumentsManage)"
        type="primary"
        @click="openCreate"
      >
        Добавить УПД
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

    <el-table
      v-if="canAll(CAN.edoDocumentsOpen)"
      v-loading="pending"
      :data="documents"
      empty-text="Документов нет"
      class="page__table"
    >
      <el-table-column label="Дата" width="130">
        <template #default="{ row }">
          {{ row.doc_date ? formatDate(row.doc_date) : formatDate(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column prop="number" label="Номер УПД" min-width="160" />
      <el-table-column label="Поставщик" min-width="200">
        <template #default="{ row }">
          {{ row.supplier_name ?? "—" }}
          <div v-if="row.supplier_inn" class="muted hint">
            ИНН {{ row.supplier_inn }}
          </div>
        </template>
      </el-table-column>
      <el-table-column label="Адрес доставки" min-width="240">
        <template #default="{ row }">{{ row.delivery_address ?? "—" }}</template>
      </el-table-column>
      <el-table-column label="ID в ЭДО" min-width="220">
        <template #default="{ row }">{{ row.external_id ?? "—" }}</template>
      </el-table-column>
      <el-table-column label="Статус" width="120">
        <template #default="{ row }">
          <el-tag type="info" effect="light">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-if="canAll(CAN.edoDocumentsOpen)"
      v-model:current-page="page"
      class="pager"
      layout="prev, pager, next, total"
      :page-size="PAGE_SIZE"
      :total="total"
      :disabled="pending"
      @current-change="load"
    />

    <el-dialog v-model="createOpen" title="Новый входящий УПД" width="680">
      <el-form label-position="top" @submit.prevent>
        <div class="form-grid">
          <el-form-item label="Точка">
            <el-select v-model="form.org_unit_id" style="width: 100%">
              <LocationOptions :locations="locations" />
            </el-select>
          </el-form-item>
          <el-form-item label="Дата документа">
            <el-date-picker
              v-model="form.doc_date"
              type="date"
              value-format="YYYY-MM-DD"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="Номер УПД">
            <el-input v-model="form.number" placeholder="УПД-1042" />
          </el-form-item>
          <el-form-item label="ID в ЭДО">
            <el-input v-model="form.external_id" placeholder="UUID документа" />
          </el-form-item>
          <el-form-item label="Поставщик">
            <el-input v-model="form.supplier_name" placeholder="ООО Поставщик" />
          </el-form-item>
          <el-form-item label="ИНН поставщика">
            <el-input v-model="form.supplier_inn" placeholder="7700000000" />
          </el-form-item>
        </div>
        <el-form-item label="Адрес доставки">
          <el-input v-model="form.delivery_address" placeholder="город, улица, дом" />
        </el-form-item>
        <el-form-item label="Комментарий">
          <el-input v-model="form.comment" type="textarea" :rows="2" />
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
          :disabled="!form.org_unit_id || !form.number.trim()"
          @click="save"
        >
          Сохранить
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { CAN } from "~/utils/access";

definePageMeta({ permissions: CAN.edoDocumentsOpen });
import type { components } from "@md/api-client";

import { formatDate } from "~/utils/format";

type Location = components["schemas"]["LocationSchema"];
type EdoDocument = components["schemas"]["EdoDocumentSchema"];

const PAGE_SIZE = 20;

const api = useApi();

const locations = ref<Location[]>([]);
const documents = ref<EdoDocument[]>([]);
const total = ref(0);
const page = ref(1);
const locationId = ref("");
const filter = ref("");
const pending = ref(false);
const error = ref("");

const createOpen = ref(false);
const saving = ref(false);
const createError = ref("");
const form = reactive({
  org_unit_id: "",
  number: "",
  external_id: "",
  doc_date: "",
  supplier_name: "",
  supplier_inn: "",
  delivery_address: "",
  comment: "",
});

let searchTimer: ReturnType<typeof setTimeout> | undefined;

function onSearch(): void {
  if (searchTimer) {
    clearTimeout(searchTimer);
  }

  searchTimer = setTimeout(() => {
    void reload();
  }, 300);
}

function reload(): Promise<void> {
  page.value = 1;

  return load();
}

async function loadLocations(): Promise<void> {
  if (!canAll(CAN.edoDocumentsOpen)) {
    return;
  }

  const { data, response } = await api.GET("/api/inventory/locations", {});

  if (response.ok && data) {
    locations.value = data;
    locationId.value = data[0]?.id ?? "";
  }
}

async function load(): Promise<void> {
  if (!locationId.value) {
    return;
  }

  pending.value = true;
  error.value = "";

  try {
    const { response, data, error: failure } = await api.GET(
      "/api/edo/documents",
      {
        params: {
          query: {
            org_unit_id: locationId.value,
            search: filter.value.trim() || undefined,
            limit: PAGE_SIZE,
            offset: (page.value - 1) * PAGE_SIZE,
          },
        },
      },
    );

    if (!response.ok || !data) {
      const payload = failure as { message?: string } | undefined;
      throw new Error(
        payload?.message ?? `Не удалось загрузить УПД: ${response.status}`,
      );
    }

    documents.value = data.items;
    total.value = data.total;
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Ошибка загрузки";
  } finally {
    pending.value = false;
  }
}

function openCreate(): void {
  createError.value = "";
  form.org_unit_id = locationId.value || locations.value[0]?.id || "";
  form.number = "";
  form.external_id = "";
  form.doc_date = "";
  form.supplier_name = "";
  form.supplier_inn = "";
  form.delivery_address = "";
  form.comment = "";
  createOpen.value = true;
}

async function save(): Promise<void> {
  saving.value = true;
  createError.value = "";

  try {
    const { response, error: failure } = await api.POST("/api/edo/documents", {
      body: {
        org_unit_id: form.org_unit_id,
        number: form.number.trim(),
        external_id: form.external_id.trim() || null,
        doc_date: form.doc_date || null,
        supplier_name: form.supplier_name.trim() || null,
        supplier_inn: form.supplier_inn.trim() || null,
        delivery_address: form.delivery_address.trim() || null,
        comment: form.comment.trim() || null,
      },
    });

    if (!response.ok) {
      const payload = failure as { message?: string } | undefined;
      throw new Error(
        payload?.message ?? `Не удалось сохранить УПД: ${response.status}`,
      );
    }

    createOpen.value = false;
    locationId.value = form.org_unit_id;
    await load();
  } catch (cause) {
    createError.value = cause instanceof Error ? cause.message : "Ошибка сохранения";
  } finally {
    saving.value = false;
  }
}

onMounted(async () => {
  await loadLocations();
  await load();
});
</script>

<style scoped>
.page__error {
  margin-bottom: 12px;
}

.page__table {
  margin-top: 4px;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 16px;
}

.hint {
  font-size: 11px;
}

.pager {
  margin-top: 18px;
}
</style>
