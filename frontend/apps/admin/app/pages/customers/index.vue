<template>
  <div class="page">
    <h1 class="page__title">Клиенты</h1>

    <el-alert
      v-if="error"
      :title="error"
      type="error"
      :closable="false"
      show-icon
      class="page__error"
    />

    <div style="display: flex; flex-wrap: wrap; gap: 12px; align-items: center; margin: 16px 0">
      <el-input
        v-model="search"
        placeholder="Поиск: имя или телефон"
        style="width: 300px"
        clearable
        @keyup.enter="reload"
      />
      <el-button :loading="pending" @click="reload">Найти</el-button>
      <span style="color: #909399">Клиентов: {{ total }}</span>
    </div>

    <el-table
      v-if="items.length"
      v-loading="pending"
      :data="items"
      stripe
      border
      @row-click="openCustomer"
    >
      <el-table-column label="Имя" min-width="200">
        <template #default="{ row }">
          {{ row.first_name ?? "— без имени —" }}
        </template>
      </el-table-column>
      <el-table-column label="Телефон" width="200">
        <template #default="{ row }">
          {{ row.contact_phone ?? "—" }}
        </template>
      </el-table-column>
      <el-table-column label="Статус" width="140">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : 'danger'" effect="light">
            {{ row.status === "active" ? "Активен" : "Заблокирован" }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="Зарегистрирован" width="190">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
    </el-table>

    <el-empty v-else-if="!pending" description="Клиентов пока нет" />

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

definePageMeta({ permissions: CAN.customersOpen });

type CustomerListItem = components["schemas"]["CustomerListItemSchema"];

const PAGE_SIZE = 50;

const api = useApi();
const router = useRouter();

const items = ref<CustomerListItem[]>([]);
const total = ref(0);
const page = ref(1);
const search = ref("");
const pending = ref(false);
const error = ref("");

function formatTime(value: string): string {
  return new Date(value).toLocaleDateString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

async function loadCustomers(): Promise<void> {
  error.value = "";
  pending.value = true;

  try {
    const { data, response } = await api.GET("/api/customers", {
      params: {
        query: {
          search: search.value || undefined,
          limit: PAGE_SIZE,
          offset: (page.value - 1) * PAGE_SIZE,
        },
      },
    });

    if (!response.ok || !data) {
      error.value =
        response.status === 403
          ? "Нет доступа к профилям клиентов"
          : "Не удалось загрузить клиентов";
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
  await loadCustomers();
}

async function goToPage(target: number): Promise<void> {
  page.value = target;
  await loadCustomers();
}

async function openCustomer(row: CustomerListItem): Promise<void> {
  await router.push(`/customers/${row.id}`);
}

onMounted(loadCustomers);
</script>
