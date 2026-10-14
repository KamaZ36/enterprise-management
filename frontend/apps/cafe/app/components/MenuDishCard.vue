<template>
  <article class="dish-card" :class="{ 'dish-card--added': justAdded }">
    <div class="dish-card__photo">
      <img
        v-if="photo && !broken"
        :src="photo"
        :alt="item.name"
        loading="lazy"
        @error="broken = true"
      />
      <div v-else class="dish-card__placeholder">
        <AppIcon name="bowl" :size="36" />
      </div>
    </div>

    <div class="dish-card__body">
      <h3 class="dish-card__title">{{ item.name }}</h3>
      <p v-if="item.description" class="dish-card__text">
        {{ item.description }}
      </p>

      <div class="dish-card__foot">
        <span class="dish-card__price">
          {{ priceWithUnit(item.value, item.unit) }}
        </span>
        <button
          class="dish-card__add"
          :class="{ 'dish-card__add--added': justAdded }"
          type="button"
          :aria-label="`Добавить: ${item.name}`"
          @click="add"
        >
          <AppIcon v-if="justAdded" name="check" :size="20" />
          <span v-else>+</span>
        </button>
      </div>
    </div>
  </article>
</template>

<script setup lang="ts">
import type { components } from "@md/api-client";

import { priceWithUnit } from "~/utils/money";

type AssortmentItem = components["schemas"]["AssortmentItemSchema"];

const props = defineProps<{ item: AssortmentItem }>();
const emit = defineEmits<{ add: [AssortmentItem] }>();

const broken = ref(false);


const justAdded = ref(false);
let resetTimer: ReturnType<typeof setTimeout> | undefined;

function add(): void {
  emit("add", props.item);

  justAdded.value = true;
  clearTimeout(resetTimer);
  resetTimer = setTimeout(() => {
    justAdded.value = false;
  }, 900);
}

onBeforeUnmount(() => clearTimeout(resetTimer));


const photo = computed(
  () => props.item.image_url || `/menu/${props.item.sku}.jpg`,
);
</script>
