<template>
  <section class="section">
    <div class="wrap">
      <div class="kicker">Кабинет</div>
      <h1 class="section__title">Мои заказы</h1>

      <p v-if="!isAuthenticated" class="muted">
        Войдите, чтобы увидеть свои заказы.
        <button class="link-button" type="button" @click="showAuthModal">
          Войти
        </button>
      </p>
      <p v-else-if="pending" class="loading">Загружаем заказы…</p>
      <p v-else-if="error" class="notice notice--error">{{ error }}</p>

      <p v-else-if="!items.length" class="muted">
        Заказов пока нет.
        <NuxtLink to="/" class="link-button">Перейти в меню</NuxtLink>
      </p>

      <div v-else class="grid grid--3 menu-grid">
        <NuxtLink
          v-for="(order, index) in items"
          :key="order.id"
          v-reveal="index * 60"
          :to="`/orders/${order.id}`"
          class="card"
        >
          <div class="card__title">Заказ {{ order.number ?? "—" }}</div>

          <div style="margin: 10px 0">
            <span :class="orderStatusClass(order.status)">
              {{ ORDER_STATUS_TITLES[order.status] ?? order.status }}
            </span>
          </div>

          <div class="muted small">
            {{ formatOrderTime(order.created_at) }} · {{ order.line_count }} поз.
          </div>

          <div class="dish__price">{{ formatKopecks(order.total) }}</div>
        </NuxtLink>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { components } from "@md/api-client";
import { formatKopecks } from "@md/money";

import {
  formatOrderTime,
  orderStatusClass,
  ORDER_STATUS_TITLES,
} from "~/utils/orders";

type MyOrderListItem = components["schemas"]["MyOrderListItemSchema"];

const api = useApi();
const { isAuthenticated } = useSession();
const { show: showAuthModal } = useAuthModal();

const items = ref<MyOrderListItem[]>([]);
const pending = ref(false);
const error = ref("");

async function loadOrders(): Promise<void> {
  if (!isAuthenticated.value) {
    showAuthModal();
    return;
  }

  pending.value = true;
  error.value = "";

  try {
    const { data, response } = await api.GET("/api/sales/me/orders", {
      params: { query: { limit: 50 } },
    });

    if (response.status === 401) {
      showAuthModal();
      return;
    }

    if (!response.ok || !data) {
      error.value = "Не удалось загрузить заказы";
      items.value = [];
      return;
    }

    items.value = data.items;
  } finally {
    pending.value = false;
  }
}

onMounted(loadOrders);

watch(isAuthenticated, (value) => {
  if (value) {
    void loadOrders();
  }
});
</script>
