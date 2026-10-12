<template>
  <el-alert
    v-if="visible"
    type="info"
    :closable="false"
    show-icon
    title="Только просмотр"
    description="Нет прав на изменение — доступны просмотр и выгрузка."
    class="view-only"
  />
</template>

<script setup lang="ts">
const props = defineProps<{ view: string; edit: string }>();

const { can } = useCurrentUser();

const visible = computed(() => can(props.view) && !can(props.edit));
</script>

<style scoped>
.view-only {
  margin-bottom: 12px;
}
</style>
