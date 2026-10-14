<template>
  <div class="page">
    <el-page-header
      content="Новая техкарта"
      @back="navigateTo('/production/tech-cards')"
    />

    <el-alert
      v-if="error"
      :title="error"
      type="error"
      :closable="false"
      show-icon
      class="page__error"
    />

    <el-form label-position="top" class="form">
      <el-row :gutter="16">
        <el-col :xs="24" :md="8">
          <el-form-item label="Код">
            <el-input v-model="form.code" placeholder="BEEF-SHOULDER" />
            <span class="hint">
              Код общий для редакций: новая техкарта с тем же кодом станет v2.
            </span>
          </el-form-item>
        </el-col>

        <el-col :xs="24" :md="8">
          <el-form-item label="Название">
            <el-input v-model="form.name" placeholder="Разделка говяжьей лопатки" />
          </el-form-item>
        </el-col>

        <el-col :xs="24" :md="8">
          <el-form-item label="Что задаёт норму">
            <el-select v-model="form.basis" style="width: 100%">
              <el-option
                label="Вход — разделка, обработка партии"
                value="input"
              />
              <el-option label="Выход — рецептура, фасовка" value="output" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="16">
        <el-col :xs="24" :md="8">
          <el-form-item label="Действует с">
            <el-date-picker
              v-model="form.valid_from"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="не обязательно"
              style="width: 100%"
            />
          </el-form-item>
        </el-col>

        <el-col :xs="24" :md="16">
          <el-form-item label="Комментарий">
            <el-input v-model="form.comment" placeholder="не обязательно" />
          </el-form-item>
        </el-col>
      </el-row>

      <h3 class="group">Входы</h3>
      <div
        v-for="(line, index) in form.components"
        :key="`c-${index}`"
        class="line"
      >
        <el-select
          v-model="line.nomenclature_id"
          filterable
          placeholder="Сырьё"
          class="line__name"
        >
          <el-option
            v-for="option in nomenclatures"
            :key="option.id"
            :label="option.name"
            :value="option.id"
          />
        </el-select>
        <el-input v-model="line.quantity" placeholder="Кол-во" class="line__qty" />
        <el-button text type="danger" @click="form.components.splice(index, 1)">
          Убрать
        </el-button>
      </div>
      <el-button text type="primary" @click="addComponent">+ Вход</el-button>

      <h3 class="group">Выходы</h3>
      <div
        v-for="(line, index) in form.outputs"
        :key="`o-${index}`"
        class="line"
      >
        <el-select
          v-model="line.nomenclature_id"
          filterable
          placeholder="Продукт"
          class="line__name"
        >
          <el-option
            v-for="option in nomenclatures"
            :key="option.id"
            :label="option.name"
            :value="option.id"
          />
        </el-select>
        <el-input v-model="line.quantity" placeholder="Кол-во" class="line__qty" />
        <el-select v-model="line.output_kind" class="line__kind">
          <el-option label="Основной" value="main" />
          <el-option label="Попутный" value="by_product" />
        </el-select>
        <el-input
          v-model="line.cost_coefficient"
          placeholder="Коэф."
          class="line__coef"
        />
        <el-button text type="danger" @click="form.outputs.splice(index, 1)">
          Убрать
        </el-button>
      </div>
      <el-button text type="primary" @click="addOutput">+ Выход</el-button>

      <h3 class="group">Потери</h3>
      <div v-for="(line, index) in form.losses" :key="`l-${index}`" class="line">
        <el-select v-model="line.loss_kind" class="line__kind">
          <el-option
            v-for="(title, code) in LOSS_TITLES"
            :key="code"
            :label="title"
            :value="code"
          />
        </el-select>
        <el-input v-model="line.quantity" placeholder="Кол-во" class="line__qty" />
        <el-button text type="danger" @click="form.losses.splice(index, 1)">
          Убрать
        </el-button>
      </div>
      <el-button text type="primary" @click="addLoss">+ Потери</el-button>

      <p class="hint">
        Сумма входов и выходов не обязана сходиться: разницу при проведении
        спишут как потери, распределив её по указанным видам.
      </p>

      <div class="actions">
        <el-button
          type="primary"
          :loading="saving"
          :disabled="!canSubmit"
          @click="submit"
        >
          Сохранить
        </el-button>
        <el-button @click="navigateTo('/production/tech-cards')">
          Отмена
        </el-button>
      </div>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import type { components } from "@md/api-client";

import { CAN } from "~/utils/access";

definePageMeta({ permissions: CAN.techCardCreate });

type Nomenclature = components["schemas"]["NomenclatureSchema"];
type TechCardLineInput = components["schemas"]["TechCardLineInputSchema"];

const LOSS_TITLES: Record<string, string> = {
  shrinkage: "Усушка",
  cooking: "Ужарка и уварка",
  trimming: "Зачистка, жиловка",
  defrost: "Дефростация",
  defect: "Брак",
};

const api = useApi();

const nomenclatures = ref<Nomenclature[]>([]);
const saving = ref(false);
const error = ref("");

const form = reactive({
  code: "",
  name: "",
  basis: "input" as "input" | "output",
  valid_from: null as string | null,
  comment: "",
  components: [{ nomenclature_id: "", quantity: "" }],
  outputs: [
    {
      nomenclature_id: "",
      quantity: "",
      output_kind: "main" as "main" | "by_product",
      cost_coefficient: "",
    },
  ],
  losses: [{ loss_kind: "shrinkage", quantity: "" }],
});

const canSubmit = computed(
  () =>
    form.code.trim().length > 0 &&
    form.name.trim().length > 0 &&
    form.components.some((line) => line.nomenclature_id && line.quantity) &&
    form.outputs.some((line) => line.nomenclature_id && line.quantity),
);

function addComponent(): void {
  form.components.push({ nomenclature_id: "", quantity: "" });
}

function addOutput(): void {
  form.outputs.push({
    nomenclature_id: "",
    quantity: "",
    output_kind: "by_product",
    cost_coefficient: "",
  });
}

function addLoss(): void {
  form.losses.push({ loss_kind: "shrinkage", quantity: "" });
}

async function loadNomenclatures(): Promise<void> {
  const { data, response } = await api.GET("/api/catalog/nomenclatures", {
    params: { query: { limit: 100 } },
  });

  if (response.ok && data) {
    nomenclatures.value = data.items;
  }
}

function buildLines(): TechCardLineInput[] {
  const components: TechCardLineInput[] = form.components
    .filter((line) => line.nomenclature_id && line.quantity)
    .map((line) => ({
      role: "component" as const,
      nomenclature_id: line.nomenclature_id,
      quantity: line.quantity,
    }));

  const outputs: TechCardLineInput[] = form.outputs
    .filter((line) => line.nomenclature_id && line.quantity)
    .map((line) => ({
      role: "output" as const,
      nomenclature_id: line.nomenclature_id,
      quantity: line.quantity,
      output_kind: line.output_kind,
      cost_coefficient: line.cost_coefficient || null,
    }));

  const losses: TechCardLineInput[] = form.losses
    .filter((line) => line.quantity)
    .map((line) => ({
      role: "loss" as const,
      loss_kind: line.loss_kind as TechCardLineInput["loss_kind"],
      quantity: line.quantity,
    }));

  return [...components, ...outputs, ...losses];
}

async function submit(): Promise<void> {
  error.value = "";
  saving.value = true;

  try {
    const { data, response, error: failure } = await api.POST(
      "/api/production/tech-cards",
      {
        body: {
          code: form.code.trim(),
          name: form.name.trim(),
          basis: form.basis,
          valid_from: form.valid_from || null,
          comment: form.comment.trim() || null,
          lines: buildLines(),
        },
      },
    );

    if (!response.ok || !data) {
      const payload = failure as { message?: string } | undefined;
      error.value =
        payload?.message ?? `Не удалось сохранить техкарту: ${response.status}`;
      return;
    }

    await navigateTo(`/production/tech-cards/${data.id}`);
  } finally {
    saving.value = false;
  }
}

onMounted(loadNomenclatures);
</script>

<style scoped>
.form {
  margin-top: 20px;
}

.group {
  margin: 24px 0 12px;
  font-size: 16px;
}

.line {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}

.line__name {
  flex: 1;
  min-width: 220px;
}

.line__qty {
  width: 140px;
}

.line__kind {
  width: 160px;
}

.line__coef {
  width: 110px;
}

.hint {
  display: block;
  color: #909399;
  font-size: 12px;
  margin-top: 4px;
}

.actions {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-top: 28px;
}
</style>
