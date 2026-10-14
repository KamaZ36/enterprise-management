<template>
  <section class="section">
    <div class="wrap">
      <NuxtLink to="/cafe" class="back muted small">← Все кафе</NuxtLink>

      <p v-if="pending" class="muted">Загружаем меню…</p>

      <template v-else-if="cafe">
        <div class="kicker">Меню</div>
        <h1 class="section__title">{{ cafe.name }}</h1>

        <p class="muted">
          {{ cafe.address || "Адрес уточняется" }}
          <template v-if="cafe.phone_number"> · {{ cafe.phone_number }}</template>
        </p>

        <p v-if="!items.length" class="muted">
          Меню пока не заполнено — заходите чуть позже.
        </p>

        <ul v-else class="menu">
          <li
            v-for="item in items"
            :key="item.nomenclature_id"
            class="menu__item"
          >
            <span class="menu__name">{{ item.name }}</span>
            <span class="menu__unit muted small">
              за {{ unitTitle(item.unit) }}
            </span>
            <span class="menu__price">{{ formatKopecks(item.value) }}</span>
          </li>
        </ul>

        <p class="muted small note">
          Меню живое: цены и состав берутся из прайса кафе.
        </p>

        <div class="order">
          <a :href="orderUrl" class="button">Заказать</a>
          <span class="muted small">Заказ — в приложении кафе</span>
        </div>
      </template>

      <p v-else class="muted">Кафе с такой ссылкой не найдено.</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { components } from "@md/api-client";
import { formatKopecks } from "@md/money";

type Cafe = components["schemas"]["CafeOrgUnitSchema"];
type AssortmentItem = components["schemas"]["AssortmentItemSchema"];

const UNIT_TITLES: Record<string, string> = {
  kg: "кг",
  g: "г",
  pcs: "шт",
  l: "л",
  m: "м",
};

const api = usePublicApi();
const route = useRoute();
const code = String(route.params.code);

const { data: cafes, pending } = await useAsyncData("public-cafes", () =>
  api<Cafe[]>("/api/business/org-units/cafe"),
);

const cafe = computed(
  () => (cafes.value ?? []).find((item) => item.code === code) ?? null,
);

const { data: assortment } = await useAsyncData(
  () => `assortment-${cafe.value?.id ?? "none"}`,
  () =>
    cafe.value
      ? api<{ items: AssortmentItem[] }>(
          `/api/catalog/org-units/${cafe.value.id}/assortment`,
        )
      : Promise.resolve({ items: [] }),
  { watch: [cafe] },
);

const items = computed(() => assortment.value?.items ?? []);

const config = useRuntimeConfig();
const orderUrl = computed(() =>
  cafe.value
    ? `${String(config.public.cafeAppUrl)}/?cafe=${encodeURIComponent(cafe.value.code)}`
    : String(config.public.cafeAppUrl),
);

function unitTitle(unit: string): string {
  return UNIT_TITLES[unit] ?? unit;
}

useHead(() => ({
  title: cafe.value ? `${cafe.value.name} — меню` : "Кафе — Мясная деревня",
}));
</script>

<style scoped>
.back {
  display: inline-block;
  margin-bottom: 18px;
  text-decoration: none;
}

.menu {
  margin: 28px 0;
  padding: 0;
  list-style: none;
  border-top: 1px solid var(--edge);
}

.menu__item {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 12px;
  align-items: baseline;
  padding: 14px 4px;
  border-bottom: 1px solid var(--edge);
}

.menu__name {
  font-size: 17px;
}

.menu__unit {
  white-space: nowrap;
}

.menu__price {
  font-weight: 600;
  white-space: nowrap;
  color: var(--accent-soft);
}

.note {
  margin-top: 24px;
}

.order {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}
</style>
