<template>
  <div class="wrap under">
    <div class="under__badge">В разработке</div>
    <h1 class="under__title">Сайт кафе скоро откроется</h1>
    <p class="under__lead muted">
      Мы собираем меню, фотографии и возможность заказа. Пока страница в работе —
      заходите чуть позже или загляните к нам лично.
    </p>

    <div class="under__actions">
      <NuxtLink to="/" class="button">Вернуться на главную</NuxtLink>
      <a href="/#contacts" class="button button--ghost">Контакты</a>
    </div>

    <div class="under__list">
      <div v-for="item in plans" :key="item" class="under__item">
        <span class="under__dot" />
        {{ item }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const plans = [
  "Меню с фотографиями и составом",
  "Заказ столика",
  "Доставка и самовывоз",
];
</script>
