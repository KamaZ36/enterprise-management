<template>
  <el-option
    v-for="location in locations"
    :key="location.id"
    :label="location.name"
    :value="location.id"
  />
</template>

<script setup lang="ts">
import type { Location } from "~/utils/locations";

defineProps<{ locations: readonly Location[] }>();
</script>
