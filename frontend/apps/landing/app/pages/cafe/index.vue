<template>
  <section class="section">
    <div class="wrap">
      <div class="kicker">Кафе</div>
      <h1 class="section__title">Наши кафе</h1>

      <p v-if="pending" class="muted">Загружаем список кафе…</p>

      <p v-else-if="error" class="muted">
        Не удалось загрузить список кафе. Попробуйте обновить страницу.
      </p>

      <p v-else-if="!cafes.length" class="muted">
        Кафе пока не открыты — заходите чуть позже.
      </p>

      <div v-else class="grid grid--3">
        <NuxtLink
          v-for="cafe in cafes"
          :key="cafe.id"
          :to="`/cafe/${cafe.code}`"
          class="card cafe-card"
        >
          <div class="card__title">{{ cafe.name }}</div>
          <div class="muted">{{ cafe.address || "Адрес уточняется" }}</div>
          <div v-if="cafe.phone_number" class="muted small">
            {{ cafe.phone_number }}
          </div>
          <span class="button button--ghost button--small">Смотреть меню</span>
        </NuxtLink>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { components } from "@md/api-client";

type Cafe = components["schemas"]["CafeOrgUnitSchema"];

const api = usePublicApi();

const { data, pending, error } = await useAsyncData("public-cafes", () =>
  api<Cafe[]>("/api/business/org-units/cafe"),
);

const cafes = computed(() => data.value ?? []);


const onlyCafe = cafes.value.length === 1 ? cafes.value[0] : null;
if (onlyCafe) {
  await navigateTo(`/cafe/${onlyCafe.code}`, {
    redirectCode: 302,
    replace: true,
  });
}

useHead({ title: "Кафе — Мясная деревня" });
</script>

<style scoped>
.cafe-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  color: inherit;
  text-decoration: none;
  transition:
    border-color 0.2s ease,
    transform 0.2s ease;
}

.cafe-card:hover {
  border-color: var(--edge-strong);
  transform: translateY(-2px);
}

.cafe-card .button {
  align-self: flex-start;
  margin-top: auto;
}
</style>
