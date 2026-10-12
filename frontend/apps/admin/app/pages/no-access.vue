<template>
  <div class="page">
    <h1 class="page__title">Раздел недоступен</h1>
    <p class="page__subtitle">
      У вашей роли нет прав на этот раздел. Обратитесь к администратору.
    </p>

    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="Почему так"
      description="Разделы интерфейса открываются по правам роли. Если раздел нужен для работы — попросите выдать права."
      class="page__error"
    />

    <el-button type="primary" @click="goHome">На главную</el-button>
  </div>
</template>

<script setup lang="ts">
const router = useRouter();

function goHome(): void {
  void router.push("/");
}
</script>
