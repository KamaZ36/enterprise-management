<template>
  <div class="page">
    <h1 class="page__title">Техкарты</h1>

    <el-alert
      v-if="error"
      :title="error"
      type="error"
      :closable="false"
      show-icon
      class="page__error"
    />

    <div class="toolbar">
      <el-input
        v-model="search"
        placeholder="Код или название"
        style="width: 280px"
        clearable
        @keyup.enter="reload"
        @clear="reload"
      />
      <el-button :loading="pending" @click="reload">Найти</el-button>
      <el-button
        v-if="can('production.tech_card.manage')"
        type="primary"
        @click="openCreate"
      >
        Новая техкарта
      </el-button>
      <span class="muted">Всего: {{ total }}</span>
    </div>

    <el-table
      v-if="items.length"
      v-loading="pending"
      :data="items"
      stripe
      border
      @row-click="openCard"
    >
      <el-table-column label="Код" prop="code" width="220" />
      <el-table-column label="Название" prop="name" />
      <el-table-column label="Версия" width="100" align="right">
        <template #default="{ row }">v{{ row.version }}</template>
      </el-table-column>
      <el-table-column label="Норма" width="170">
        <template #default="{ row }">
          {{ BASIS_TITLES[row.basis] ?? row.basis }}
        </template>
      </el-table-column>
      <el-table-column label="Строк" width="90" align="right" prop="line_count" />
      <el-table-column label="Создана" width="170">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
    </el-table>

    <el-empty
      v-else-if="!pending"
      description="Техкарт пока нет — заведите первую"
    />

    <el-pagination
      v-if="total > PAGE_SIZE"
      :current-page="page"
      :page-size="PAGE_SIZE"
      :total="total"
      :disabled="pending"
      class="pager"
      layout="prev, pager, next, total"
      @current-change="goToPage"
    />
  </div>
</template>

<script setup lang="ts">
import type { components } from "@md/api-client";

import { CAN } from "~/utils/access";

definePageMeta({ permissions: CAN.techCardsOpen });

type TechCardListItem = components["schemas"]["TechCardListItemSchema"];

const BASIS_TITLES: Record<string, string> = {
  input: "По входу",
  output: "По выходу",
};

const PAGE_SIZE = 50;

const api = useApi();
const { can } = useCurrentUser();

const items = ref<TechCardListItem[]>([]);
const total = ref(0);
const page = ref(1);
const search = ref("");
const pending = ref(false);
const error = ref("");

function formatTime(value: string): string {
  return new Date(value).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

async function load(): Promise<void> {
  error.value = "";
  pending.value = true;

  try {
    const { data, response } = await api.GET("/api/production/tech-cards", {
      params: {
        query: {
          search: search.value.trim() || undefined,
          limit: PAGE_SIZE,
          offset: (page.value - 1) * PAGE_SIZE,
        },
      },
    });

    if (!response.ok || !data) {
      error.value =
        response.status === 403
          ? "Нет доступа к техкартам"
          : "Не удалось загрузить техкарты";
      items.value = [];
      total.value = 0;
      return;
    }

    items.value = data.items;
    total.value = data.total;
  } finally {
    pending.value = false;
  }
}

async function reload(): Promise<void> {
  page.value = 1;
  await load();
}

async function goToPage(target: number): Promise<void> {
  page.value = target;
  await load();
}

async function openCard(row: TechCardListItem): Promise<void> {
  await navigateTo(`/production/tech-cards/${row.id}`);
}

async function openCreate(): Promise<void> {
  await navigateTo("/production/tech-cards/new");
}

onMounted(load);
</script>

<style scoped>
.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  margin: 16px 0;
}

.pager {
  margin-top: 16px;
  justify-content: flex-end;
}
</style>
