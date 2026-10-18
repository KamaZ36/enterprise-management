<template>
  <aside class="order-card">
    <h2 class="order-card__title">Ваш заказ</h2>

    <p v-if="showEmpty" class="order-card__empty">
      Пока пусто — выберите блюда из меню.
    </p>

    <TransitionGroup name="order-line">
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
    </TransitionGroup>

    <template v-if="lines.length">
      <div class="fulfillment" role="radiogroup" aria-label="Способ получения">
        <label
          class="fulfillment__option"
          :class="{ 'is-active': fulfillment === 'pickup' }"
        >
          <input
            v-model="fulfillment"
            class="fulfillment__input"
            type="radio"
            value="pickup"
          />
          <AppIcon name="store" class="fulfillment__icon" />
          <span class="fulfillment__text">
            <span class="fulfillment__title">Самовывоз</span>
            <span class="fulfillment__sub">Забрать в кафе</span>
          </span>
          <span class="fulfillment__mark" aria-hidden="true">
            <AppIcon name="check" />
          </span>
        </label>

        <label
          class="fulfillment__option fulfillment__option--disabled"
          aria-disabled="true"
        >
          <input
            v-model="fulfillment"
            class="fulfillment__input"
            type="radio"
            value="delivery"
            disabled
          />
          <AppIcon name="truck" class="fulfillment__icon" />
          <span class="fulfillment__text">
            <span class="fulfillment__title">Доставка</span>
            <span class="fulfillment__sub">Скоро появится</span>
          </span>
        </label>
      </div>

      <p class="muted small fulfillment__hint">
        Оплата при получении — в кафе.
      </p>

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
        Для оформления нужно войти.
        <button class="link-button" type="button" @click="showAuthModal">
          Войти
        </button>
      </p>
    </template>
  </aside>
</template>

<script setup lang="ts">
import { lineTotal, priceLabel, quantityLabel } from "~/utils/money";
import type { CartLine } from "~/composables/useCart";

const { lines, total, fulfillment, increase, decrease, remove } = useCart();
const { checkout, saving, error } = useCheckout();
const { isAuthenticated } = useSession();
const { show: showAuthModal } = useAuthModal();

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

// Пока последняя позиция «уезжает», не показываем заглушку «Пока пусто».
const showEmpty = ref(lines.value.length === 0);
let emptyTimer: ReturnType<typeof setTimeout> | undefined;

watch(
  () => lines.value.length,
  (length) => {
    clearTimeout(emptyTimer);

    if (length > 0) {
      showEmpty.value = false;
      return;
    }

    emptyTimer = setTimeout(() => {
      showEmpty.value = true;
    }, 340);
  },
);

onBeforeUnmount(() => {
  clearTimeout(freshTimer);
  clearTimeout(totalTimer);
  clearTimeout(emptyTimer);
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

/* Позиция уезжает вправо и «схлопывается», соседи плавно подтягиваются. */
.order-line {
  overflow: hidden;
  transition:
    max-height 0.34s cubic-bezier(0.22, 1, 0.36, 1),
    padding 0.34s cubic-bezier(0.22, 1, 0.36, 1),
    opacity 0.26s ease,
    transform 0.34s cubic-bezier(0.22, 1, 0.36, 1),
    border-color 0.26s ease;
}

.order-line-leave-active {
  max-height: 240px;
}

.order-line-leave-to {
  max-height: 0;
  padding-top: 0;
  padding-bottom: 0;
  border-color: transparent;
  opacity: 0;
  transform: translateX(28px);
}

.order-line-move {
  transition: transform 0.34s cubic-bezier(0.22, 1, 0.36, 1);
}

/* Выбор способа получения */
.fulfillment {
  display: grid;
  gap: 8px;
  margin: 8px 0 0;
}

.fulfillment__option {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 11px 14px;
  border: 1px solid var(--line-soft);
  border-radius: 14px;
  background: rgb(0 0 0 / 22%);
  cursor: pointer;
  transition:
    border-color 0.2s,
    background 0.2s,
    box-shadow 0.2s,
    transform 0.15s;
}

.fulfillment__option:hover {
  border-color: var(--edge-strong);
  background: rgb(0 0 0 / 32%);
}

.fulfillment__option:active {
  transform: scale(0.99);
}

.fulfillment__option.is-active {
  border-color: var(--accent);
  background: rgb(200 118 58 / 12%);
  box-shadow:
    0 0 0 3px rgb(200 118 58 / 14%),
    inset 0 0 0 1px rgb(200 118 58 / 28%);
}

.fulfillment__input {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
  pointer-events: none;
}

.fulfillment__option:has(.fulfillment__input:focus-visible) {
  outline: 2px solid var(--accent-soft);
  outline-offset: 2px;
}

.fulfillment__icon {
  flex: none;
  width: 22px;
  height: 22px;
  color: var(--muted);
  transition: color 0.2s;
}

.fulfillment__option.is-active .fulfillment__icon {
  color: var(--accent-soft);
}

.fulfillment__text {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
  line-height: 1.2;
}

.fulfillment__title {
  font-size: 14.5px;
  font-weight: 600;
}

.fulfillment__sub {
  color: var(--muted-soft);
  font-size: 12px;
}

.fulfillment__mark {
  display: grid;
  width: 20px;
  height: 20px;
  margin-left: auto;
  place-items: center;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 4px 12px rgb(200 118 58 / 40%);
  color: #fff6ef;
  opacity: 0;
  transform: scale(0.5);
  transition:
    opacity 0.2s,
    transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.fulfillment__option.is-active .fulfillment__mark {
  opacity: 1;
  transform: scale(1);
}

.fulfillment__mark :deep(.app-icon) {
  width: 13px;
  height: 13px;
}

.fulfillment__option--disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.fulfillment__option--disabled:hover {
  border-color: var(--line-soft);
  background: rgb(0 0 0 / 22%);
}

.fulfillment__option--disabled:active {
  transform: none;
}

.fulfillment__hint {
  margin: 10px 0 0;
}
</style>
