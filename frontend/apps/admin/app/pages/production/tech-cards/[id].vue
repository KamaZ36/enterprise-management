<template>
  <div class="page">
    <NuxtLink to="/production/tech-cards" class="back">← Техкарты</NuxtLink>

    <el-skeleton v-if="pending" :rows="4" animated />

    <template v-else-if="card">
      <h1 class="page__title">
        {{ card.name }}
        <el-tag type="info" effect="plain">v{{ card.version }}</el-tag>
      </h1>

      <p class="muted">
        Код: <strong>{{ card.code }}</strong>
        · норма {{ BASIS_TITLES[card.basis] ?? card.basis }}
        <template v-if="card.valid_from">
          · действует с {{ formatDate(card.valid_from) }}
        </template>
      </p>

      <p v-if="card.comment" class="muted">{{ card.comment }}</p>

      <h3 class="group">Входы</h3>
      <el-table :data="components" border>
        <el-table-column label="Позиция">
          <template #default="{ row }">
            {{ row.nomenclature_name ?? "—" }}
          </template>
        </el-table-column>
        <el-table-column label="Количество" width="160" align="right">
          <template #default="{ row }">{{ formatQuantity(row.quantity) }}</template>
        </el-table-column>
      </el-table>

      <h3 class="group">Выходы</h3>
      <el-table :data="outputs" border>
        <el-table-column label="Позиция">
          <template #default="{ row }">
            {{ row.nomenclature_name ?? "—" }}
          </template>
        </el-table-column>
        <el-table-column label="Вид" width="140">
          <template #default="{ row }">
            {{ OUTPUT_TITLES[row.output_kind] ?? "—" }}
          </template>
        </el-table-column>
        <el-table-column label="Количество" width="150" align="right">
          <template #default="{ row }">{{ formatQuantity(row.quantity) }}</template>
        </el-table-column>
        <el-table-column label="Коэффициент" width="140" align="right">
          <template #default="{ row }">
            {{ row.cost_coefficient ?? "—" }}
          </template>
        </el-table-column>
      </el-table>

      <h3 class="group">Потери</h3>
      <el-table :data="losses" border>
        <el-table-column label="Вид">
          <template #default="{ row }">
            {{ LOSS_TITLES[row.loss_kind] ?? "Не классифицировано" }}
          </template>
        </el-table-column>
        <el-table-column label="Количество" width="160" align="right">
          <template #default="{ row }">{{ formatQuantity(row.quantity) }}</template>
        </el-table-column>
      </el-table>

      <p class="hint">
        Норма задаётся на одну закладку. Задание масштабирует её на число
        закладок и фиксирует факт — правки этой техкарты прошлое не меняют.
      </p>
    </template>

    <el-empty v-else description="Техкарта не найдена" />
  </div>
</template>

<script setup lang="ts">
import type { components } from "@md/api-client";

import { CAN } from "~/utils/access";

definePageMeta({ permissions: CAN.techCardsOpen });

type TechCardDetail = components["schemas"]["TechCardDetailSchema"];

const BASIS_TITLES: Record<string, string> = {
  input: "по входу",
  output: "по выходу",
};

const OUTPUT_TITLES: Record<string, string> = {
  main: "Основной",
  by_product: "Попутный",
};

const LOSS_TITLES: Record<string, string> = {
  shrinkage: "Усушка",
  cooking: "Ужарка и уварка",
  trimming: "Зачистка, жиловка",
  defrost: "Дефростация",
  defect: "Брак",
};

const api = useApi();
const route = useRoute();

const cardId = String(route.params.id);
const card = ref<TechCardDetail | null>(null);
const pending = ref(false);

const components = computed(
  () => card.value?.lines.filter((line) => line.role === "component") ?? [],
);
const outputs = computed(
  () => card.value?.lines.filter((line) => line.role === "output") ?? [],
);
const losses = computed(
  () => card.value?.lines.filter((line) => line.role === "loss") ?? [],
);

function formatQuantity(value: string): string {
  const numeric = Number(value);

  return Number.isNaN(numeric)
    ? value
    : numeric.toLocaleString("ru-RU", { maximumFractionDigits: 3 });
}

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString("ru-RU");
}

async function load(): Promise<void> {
  pending.value = true;

  try {
    const { data, response } = await api.GET(
      "/api/production/tech-cards/{tech_card_id}",
      { params: { path: { tech_card_id: cardId } } },
    );

    card.value = response.ok && data ? data : null;
  } finally {
    pending.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
.back {
  display: inline-block;
  margin-bottom: 12px;
  color: #909399;
  text-decoration: none;
}

.group {
  margin: 24px 0 12px;
  font-size: 16px;
}

.hint {
  margin-top: 24px;
  color: #909399;
  font-size: 13px;
}
</style>
