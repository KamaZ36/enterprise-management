<template>
  <el-config-provider :locale="ru">
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
  </el-config-provider>
</template>

<script setup lang="ts">
import ru from "element-plus/es/locale/lang/ru";
</script>
