<script setup lang="ts">
const menuOpen = ref(false);
const config = useRuntimeConfig();
const cafeAppUrl = String(config.public.cafeAppUrl);
</script>

<template>
  <div class="shell">
    <header class="top">
      <div class="wrap top__inner">
        <NuxtLink to="/" class="brand">
          <span class="brand__text">Мясная деревня</span>
        </NuxtLink>

        <nav class="nav" :class="{ 'nav--open': menuOpen }" @click="menuOpen = false">
          <a :href="cafeAppUrl">Кафе</a>
          <a href="/#shops">Магазины</a>
          <a href="/#company">О компании</a>
          <a href="/#contacts">Контакты</a>
        </nav>

        <div class="top__right">
          <a :href="cafeAppUrl" class="button button--small">Кафе</a>

          <button
            class="burger"
            type="button"
            :aria-expanded="menuOpen"
            aria-label="Меню"
            @click="menuOpen = !menuOpen"
          >
            <AppIcon :name="menuOpen ? 'close' : 'menu'" />
          </button>
        </div>
      </div>
    </header>

    <main class="main">
      <slot />
    </main>

    <footer class="bottom">
      <div class="wrap bottom__inner">
        <div>
          <div class="brand__text">Мясная деревня</div>
          <div class="muted">Производство, магазины, кафе</div>
        </div>

        <div class="bottom__contacts">
          <div>Телефон: <span class="muted">укажите свой</span></div>
          <div>Адрес: <span class="muted">укажите свой</span></div>
        </div>
      </div>

      <div class="wrap muted small">
        © {{ new Date().getFullYear() }} Мясная деревня
      </div>
    </footer>
  </div>
</template>
