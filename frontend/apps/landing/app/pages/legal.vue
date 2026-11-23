<script setup lang="ts">
import { company } from "~/utils/company";

useHead({ title: "Реквизиты — Мясная деревня" });

const rows = computed(() => {
  const result = [
    { label: "Продавец", value: company.legalName, href: "" },
    { label: "ИНН", value: company.inn, href: "" },
    { label: "ОГРНИП", value: company.ogrnip, href: "" },
  ];

  if (company.address) {
    result.push({ label: "Адрес", value: company.address, href: "" });
  }
  if (company.phone) {
    result.push({
      label: "Телефон",
      value: company.phone,
      href: `tel:${company.phone.replace(/[^+\d]/g, "")}`,
    });
  }
  if (company.email) {
    result.push({
      label: "E-mail",
      value: company.email,
      href: `mailto:${company.email}`,
    });
  }
  if (company.hours) {
    result.push({ label: "Режим работы", value: company.hours, href: "" });
  }

  return result;
});
</script>

<template>
  <section class="section">
    <div class="wrap">
      <NuxtLink to="/" class="back">← На главную</NuxtLink>
      <h1 class="section__title">Реквизиты</h1>

      <dl class="requisites">
        <div v-for="row in rows" :key="row.label" class="requisites__row">
          <dt>{{ row.label }}</dt>
          <dd>
            <a v-if="row.href" :href="row.href">{{ row.value }}</a>
            <template v-else>{{ row.value }}</template>
          </dd>
        </div>
      </dl>
    </div>
  </section>
</template>

<style scoped>
.back {
  display: inline-block;
  margin-bottom: 18px;
  color: var(--muted);
  font-size: 14px;
}

.requisites {
  display: grid;
  gap: 14px;
  max-width: 640px;
  margin: 0;
}

.requisites__row {
  display: grid;
  grid-template-columns: 170px 1fr;
  gap: 20px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--edge);
}

.requisites dt {
  color: var(--muted);
}

.requisites dd {
  margin: 0;
}

.requisites a {
  color: var(--accent-soft);
}

@media (max-width: 560px) {
  .requisites__row {
    grid-template-columns: 1fr;
    gap: 4px;
  }
}
</style>
