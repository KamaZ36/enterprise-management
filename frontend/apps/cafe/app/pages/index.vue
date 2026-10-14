<template>
  <section class="section">
    <div class="wrap">
      <p v-if="pending || loading" class="loading">Загружаем меню…</p>

      <template v-else-if="active">
        <div class="menu-layout">
          <div>
            <div class="kicker">Меню кафе</div>
            <h1 class="menu-title">Что будем заказывать?</h1>
            <p class="menu-lead">
              Готовим каждый день. Мясные блюда — из продуктов собственного
              производства.
            </p>
            <p class="menu-pickup">
              <AppIcon name="pin" :size="16" />
              Самовывоз из кафе{{ active.name ? ` «${active.name}»` : "" }}
            </p>

            <nav v-if="categories.length > 1" class="categories">
              <button
                v-for="category in categories"
                :key="category.id"
                class="categories__item"
                :class="{ 'categories__item--active': category.id === selected }"
                type="button"
                @click="selected = category.id"
              >
                {{ category.title }}
              </button>
            </nav>

            <p v-if="!visibleItems.length" class="menu-empty">
              В этом разделе пока нет блюд.
            </p>

            <div v-else class="dish-grid">
              <MenuDishCard
                v-for="item in visibleItems"
                :key="item.nomenclature_id"
                :item="item"
                @add="addToCart"
              />
            </div>

            <p class="menu-note">
              <i class="info">i</i>
              Время приготовления уточним при подтверждении заказа.
            </p>
          </div>

          <OrderSidebar class="menu-side" />
        </div>
      </template>

      <template v-else-if="cafes.length">
        <div class="kicker">Кафе</div>
        <h1 class="menu-title">Выберите кафе</h1>

        <div class="dish-grid">
          <NuxtLink
            v-for="cafe in cafes"
            :key="cafe.id"
            :to="`/?cafe=${cafe.code}`"
            class="card"
          >
            <div class="card__title">{{ cafe.name }}</div>
            <div class="muted">{{ cafe.address || "Адрес уточняется" }}</div>
          </NuxtLink>
        </div>
      </template>

      <p v-else class="muted">Кафе пока не открыты.</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { components } from "@md/api-client";

type AssortmentItem = components["schemas"]["AssortmentItemSchema"];

const api = useApi();
const { cafes, active, pending } = useCafe();
const { add } = useCart();

const items = ref<AssortmentItem[]>([]);
const loading = ref(false);
const selected = ref("");

const categories = computed(() => {
  const found = new Map<string, string>();

  for (const item of items.value) {
    if (item.category_id && item.category_name) {
      found.set(item.category_id, item.category_name);
    }
  }

  return [
    { id: "", title: "Все блюда" },
    ...[...found].map(([id, title]) => ({ id, title })),
  ];
});

const visibleItems = computed(() =>
  selected.value
    ? items.value.filter((item) => item.category_id === selected.value)
    : items.value,
);

async function loadMenu(): Promise<void> {
  const cafe = active.value;
  selected.value = "";

  if (!cafe) {
    items.value = [];
    return;
  }

  loading.value = true;

  try {
    const { data, response } = await api.GET(
      "/api/catalog/org-units/{org_unit_id}/assortment",
      { params: { path: { org_unit_id: cafe.id } } },
    );

    items.value = response.ok && data ? data.items : [];
  } finally {
    loading.value = false;
  }
}

watch(() => active.value?.id, loadMenu, { immediate: true });

function addToCart(item: AssortmentItem): void {
  add(item);
}
</script>
