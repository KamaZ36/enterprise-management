<template>
  <aside class="order-card">
    <h2 class="order-card__title">Ваш заказ</h2>

    <p v-if="!lines.length" class="order-card__empty">
      Пока пусто — выберите блюда из меню.
    </p>

    <div
      v-for="line in lines"
      :key="line.nomenclature_id"
      class="order-line"
      :class="{ 'order-line--fresh': line.nomenclature_id === freshId }"
    >
      <img
        v-if="!broken[line.nomenclature_id]"
        class="order-line__thumb"
        :src="thumbFor(line)"
        :alt="line.name"
        @error="broken[line.nomenclature_id] = true"
      />
      <div v-else class="order-line__thumb" />

      <div class="order-line__body">
        <div class="order-line__head">
          <span class="order-line__name">{{ line.name }}</span>
          <button
            class="order-line__remove"
            type="button"
            :aria-label="`Убрать: ${line.name}`"
            @click="remove(line.nomenclature_id)"
          >
            ×
          </button>
        </div>

        <div class="order-line__controls">
          <span class="stepper">
            <button
              type="button"
              aria-label="Меньше"
              @click="decrease(line.nomenclature_id)"
            >
              −
            </button>
            <span>{{ quantityLabel(line.quantity, line.unit) }}</span>
            <button
              type="button"
              aria-label="Больше"
              @click="increase(line.nomenclature_id)"
            >
              +
            </button>
          </span>

          <span class="order-line__sum">
            {{ priceLabel(lineTotal(line.quantity, line.unit_price)) }}
          </span>
        </div>
      </div>
    </div>

    <template v-if="lines.length">
      <div class="order-card__total">
        <span>Итого</span>
        <strong :class="{ 'is-pulsing': totalPulse }">{{ priceLabel(total) }}</strong>
      </div>

      <p v-if="error" class="notice notice--error">{{ error }}</p>

      <button
        class="button order-card__submit"
        type="button"
        :disabled="saving"
        @click="checkout"
      >
        {{ saving ? "Оформляем…" : "Оформить заказ" }}
      </button>

      <p v-if="!isAuthenticated" class="muted small auth-hint">
        Для оформления нужно войти — попросим код.
      </p>
    </template>
  </aside>
</template>

<script setup lang="ts">
import { lineTotal, priceLabel, quantityLabel } from "~/utils/money";
import type { CartLine } from "~/composables/useCart";

const { lines, total, increase, decrease, remove } = useCart();
const { checkout, saving, error } = useCheckout();
const { isAuthenticated } = useSession();

const broken = reactive<Record<string, boolean>>({});


const freshId = ref<string | null>(null);
let freshTimer: ReturnType<typeof setTimeout> | undefined;

watch(
  () => lines.value.map((line) => line.nomenclature_id),
  (current, previous) => {
    const before = new Set(previous ?? []);
    const added = current.find((id) => !before.has(id));

    if (!added) {
      return;
    }

    freshId.value = added;
    clearTimeout(freshTimer);
    freshTimer = setTimeout(() => {
      freshId.value = null;
    }, 700);
  },
);

const totalPulse = ref(false);
let totalTimer: ReturnType<typeof setTimeout> | undefined;

watch(total, () => {
  totalPulse.value = true;
  clearTimeout(totalTimer);
  totalTimer = setTimeout(() => {
    totalPulse.value = false;
  }, 400);
});

onBeforeUnmount(() => {
  clearTimeout(freshTimer);
  clearTimeout(totalTimer);
});

function thumbFor(line: CartLine): string {
  return line.image_url || `/menu/${line.sku}.jpg`;
}
</script>

<style scoped>
.auth-hint {
  margin: 12px 0 0;
  text-align: center;
}
</style>
