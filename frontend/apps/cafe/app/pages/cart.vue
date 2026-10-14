<template>
  <section class="section">
    <div class="wrap cart-page">
      <NuxtLink to="/" class="link-button back">← В меню</NuxtLink>

      <OrderSidebar />
    </div>
  </section>
</template>

<script setup lang="ts">
useHead({ title: "Корзина — Мясная деревня" });
</script>

<style scoped>
.back {
  display: inline-block;
  margin-bottom: 16px;
}
</style>
