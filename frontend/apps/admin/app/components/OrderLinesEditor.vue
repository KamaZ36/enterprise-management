<template>
  <div class="lines">
    <div v-for="(line, index) in modelValue" :key="index" class="lines__row">
      <el-select
        filterable
        placeholder="Позиция"
        class="lines__name"
        :model-value="line.nomenclature_id"
        :loading="loading"
        @update:model-value="setName(index, $event)"
      >
        <el-option
          v-for="option in options"
          :key="option.id"
          :label="option.label"
          :value="option.id"
        />
      </el-select>

      <el-input-number
        class="lines__qty"
        :min="1"
        :step="1"
        :model-value="Number(line.quantity) || 1"
        @update:model-value="setQuantity(index, $event)"
      />

      <el-button text type="danger" @click="remove(index)">Убрать</el-button>
    </div>

    <el-button text type="primary" @click="add">+ Позиция</el-button>

    <p v-if="orgUnitId && !loading && !assortment.length" class="lines__hint">
      У этой точки нет привязанного прайс-листа или в нём нет позиций.
    </p>
  </div>
</template>

<script setup lang="ts">
import type { components } from "@md/api-client";
import { formatKopecks } from "@md/money";

import type { OrderLineDraft } from "~/utils/orderLines";

type AssortmentItem = components["schemas"]["AssortmentItemSchema"];

const props = defineProps<{
  modelValue: OrderLineDraft[];
  orgUnitId?: string;

  extraOptions?: { id: string; name: string }[];
}>();
const emit = defineEmits<{ "update:modelValue": [OrderLineDraft[]] }>();

const api = useApi();
const assortment = ref<AssortmentItem[]>([]);
const loading = ref(false);

const options = computed(() => {
  const result = new Map<string, string>();

  for (const item of assortment.value) {
    result.set(
      item.nomenclature_id,
      `${item.name} — ${formatKopecks(item.value)}`,
    );
  }

  for (const extra of props.extraOptions ?? []) {
    if (!result.has(extra.id)) {
      result.set(extra.id, extra.name);
    }
  }

  return [...result].map(([id, label]) => ({ id, label }));
});

async function loadOptions(): Promise<void> {
  if (!props.orgUnitId) {
    assortment.value = [];
    return;
  }

  loading.value = true;

  try {
    const { data, response } = await api.GET(
      "/api/catalog/org-units/{org_unit_id}/assortment",
      { params: { path: { org_unit_id: props.orgUnitId } } },
    );

    assortment.value = response.ok && data ? data.items : [];
  } finally {
    loading.value = false;
  }
}

function patch(index: number, changes: Partial<OrderLineDraft>): void {
  emit(
    "update:modelValue",
    props.modelValue.map((line, position) =>
      position === index ? { ...line, ...changes } : line,
    ),
  );
}

function setName(index: number, value: unknown): void {
  patch(index, { nomenclature_id: String(value ?? "") });
}

function setQuantity(index: number, value: number | undefined): void {
  patch(index, { quantity: String(value ?? 1) });
}

function add(): void {
  emit("update:modelValue", [
    ...props.modelValue,
    { nomenclature_id: "", quantity: "1" },
  ]);
}

function remove(index: number): void {
  emit(
    "update:modelValue",
    props.modelValue.filter((_, position) => position !== index),
  );
}

watch(() => props.orgUnitId, loadOptions);

onMounted(loadOptions);
</script>

<style scoped>
.lines__row {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}

.lines__name {
  flex: 1;
}

.lines__qty {
  width: 130px;
}

.lines__hint {
  margin: 4px 0 0;
  color: #909399;
  font-size: 12px;
}
</style>
