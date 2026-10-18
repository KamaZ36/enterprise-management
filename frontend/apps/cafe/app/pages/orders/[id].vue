<template>
  <section class="section">
    <div class="wrap">
      <NuxtLink to="/orders" class="link-button">← Мои заказы</NuxtLink>

      <p v-if="!isAuthenticated" class="muted">
        Войдите, чтобы посмотреть заказ.
        <button class="link-button" type="button" @click="showAuthModal">
          Войти
        </button>
      </p>
      <p v-else-if="pending" class="loading">Загружаем заказ…</p>

      <template v-else-if="order">
        <div class="kicker" style="margin-top: 20px">Заказ</div>
        <h1 class="section__title">Заказ {{ order.number ?? "—" }}</h1>

        <p>
          <span :class="orderStatusClass(order.status)">
            {{ ORDER_STATUS_TITLES[order.status] ?? order.status }}
          </span>
          <span class="muted small">
            · {{ order.fulfillment_type === "delivery" ? "Доставка" : "Самовывоз" }}
            · {{ order.payment_status === "paid" ? "Оплачен" : "Оплата при получении" }}
            · оформлен {{ formatOrderTime(order.created_at) }}
          </span>
        </p>

        <div class="order-lines">
          <div
            v-for="line in order.lines"
            :key="line.nomenclature_id"
            class="cart-row"
          >
            <span class="cart-row__name">
              {{ line.nomenclature_name ?? "Позиция" }}
            </span>
            <span class="muted">{{ line.quantity }}</span>
            <span class="cart-row__sum">{{ formatKopecks(line.total) }}</span>
          </div>
        </div>

        <div class="total">
          Итого: <strong>{{ formatKopecks(order.total) }}</strong>
        </div>

        <p v-if="error" class="notice notice--error">{{ error }}</p>

        <div v-if="canCancel" class="actions">
          <button
            class="button button--ghost"
            type="button"
            :disabled="cancelling"
            @click="cancelOrder"
          >
            {{ cancelling ? "Отменяем…" : "Отменить заказ" }}
          </button>
        </div>
      </template>

      <p v-else class="muted">Заказ не найден.</p>
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

type MyOrderDetail = components["schemas"]["MyOrderDetailSchema"];

const api = useApi();
const route = useRoute();
const { isAuthenticated } = useSession();
const { show: showAuthModal } = useAuthModal();

const orderId = String(route.params.id);
const order = ref<MyOrderDetail | null>(null);
const pending = ref(false);
const cancelling = ref(false);
const error = ref("");

const canCancel = computed(
  () =>
    order.value !== null && ["new", "confirmed"].includes(order.value.status),
);

async function loadOrder(): Promise<void> {
  if (!isAuthenticated.value) {
    showAuthModal();
    return;
  }

  pending.value = true;
  error.value = "";

  try {
    const { data, response } = await api.GET(
      "/api/sales/me/orders/{order_id}",
      { params: { path: { order_id: orderId } } },
    );

    if (response.status === 401) {
      showAuthModal();
      return;
    }

    order.value = response.ok && data ? data : null;
  } finally {
    pending.value = false;
  }
}

async function cancelOrder(): Promise<void> {
  cancelling.value = true;
  error.value = "";

  try {
    const { response } = await api.POST(
      "/api/sales/me/orders/{order_id}/cancel",
      { params: { path: { order_id: orderId } } },
    );

    if (!response.ok) {
      error.value =
        response.status === 409
          ? "Заказ уже нельзя отменить"
          : "Не удалось отменить заказ";
    }

    await loadOrder();
  } finally {
    cancelling.value = false;
  }
}

onMounted(loadOrder);

watch(isAuthenticated, (value) => {
  if (value) {
    void loadOrder();
  }
});
</script>
