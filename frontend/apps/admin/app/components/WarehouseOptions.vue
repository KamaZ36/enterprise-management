<template>
  <el-option-group
    v-for="group in groups"
    :key="group.key"
    :label="group.title"
  >
    <el-option
      v-for="warehouse in group.warehouses"
      :key="warehouse.id"
      :label="warehouse.name"
      :value="warehouse.id"
    />
  </el-option-group>
</template>

<script setup lang="ts">
import { groupWarehousesByUnit, type Warehouse } from "~/utils/warehouses";

const props = defineProps<{ warehouses: readonly Warehouse[] }>();

const groups = computed(() => groupWarehousesByUnit(props.warehouses));
</script>
