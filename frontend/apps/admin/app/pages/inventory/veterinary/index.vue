<template>
  <div class="page">
    <h1 class="page__title">Ветеринарные документы</h1>
    <p class="page__subtitle">
      Ручные ВСД, привязанные к партиям при приёмке
    </p>

    <el-alert
      v-if="!canAll(CAN.veterinaryDocumentsOpen)"
      title="Нет права видеть ветеринарные документы"
      description="Попросите доступ к ветеринарным документам."
      type="warning"
      :closable="false"
      show-icon
      class="page__error"
    />

    <div v-if="canAll(CAN.veterinaryDocumentsOpen)" class="page__toolbar">
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
        placeholder="Номер, GUID или партия"
        style="width: 280px"
        clearable
        @input="onSearch"
      />
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
      v-if="canAll(CAN.veterinaryDocumentsOpen)"
      v-loading="pending"
      :data="documents"
      empty-text="Документов нет"
      class="page__table"
    >
      <el-table-column label="Дата" width="150">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="Номер ВСД" min-width="180">
        <template #default="{ row }">{{ row.number ?? "—" }}</template>
      </el-table-column>
      <el-table-column label="GUID ВСД" min-width="260">
        <template #default="{ row }">{{ row.guid ?? "—" }}</template>
      </el-table-column>
      <el-table-column label="Партия ВетИС" min-width="180">
        <template #default="{ row }">{{ row.batch_id ?? "—" }}</template>
      </el-table-column>
      <el-table-column label="GUID позиции" min-width="260">
        <template #default="{ row }">{{ row.product_item_guid ?? "—" }}</template>
      </el-table-column>
      <el-table-column label="Источник" width="120">
        <template #default="{ row }">
          <el-tag type="info" effect="light">{{ row.source }}</el-tag>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-if="canAll(CAN.veterinaryDocumentsOpen)"
      v-model:current-page="page"
      class="pager"
      layout="prev, pager, next, total"
      :page-size="PAGE_SIZE"
      :total="total"
      :disabled="pending"
      @current-change="load"
    />
  </div>
</template>

<script setup lang="ts">
import { CAN } from "~/utils/access";

definePageMeta({ permissions: CAN.veterinaryDocumentsOpen });
import type { components } from "@md/api-client";

import { formatDate } from "~/utils/format";

type Location = components["schemas"]["LocationSchema"];
type VeterinaryDocument = components["schemas"]["VeterinaryDocumentSchema"];

const PAGE_SIZE = 20;

const api = useApi();

const locations = ref<Location[]>([]);
const documents = ref<VeterinaryDocument[]>([]);
const total = ref(0);
const page = ref(1);
const locationId = ref("");
const filter = ref("");
const pending = ref(false);
const error = ref("");

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
  if (!canAll(CAN.veterinaryDocumentsOpen)) {
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
      "/api/veterinary/documents",
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
        payload?.message ??
          `Не удалось загрузить ветеринарные документы: ${response.status}`,
      );
    }

    documents.value = data.items;
    total.value = data.total;
  } catch (cause) {
    error.value =
      cause instanceof Error ? cause.message : "Ошибка загрузки";
  } finally {
    pending.value = false;
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

.pager {
  margin-top: 18px;
}
</style>
