<template>
  <div class="shell">
    <header class="top">
      <div class="wrap top__inner">
        <NuxtLink to="/" class="brand">
          <span class="brand__mark">МД</span>
          <span class="brand__text">Мясная деревня</span>
        </NuxtLink>

        <nav class="nav">
          <a href="/#cafe">Кафе</a>
          <a href="/#shops">Магазины</a>
          <a href="/#company">О компании</a>
          <a href="/#contacts">Контакты</a>
        </nav>

        <div class="top__right">
          <span class="top__phone">+7 (000) 000-00-00</span>
          <NuxtLink to="/cafe" class="button button--small">Сайт кафе</NuxtLink>
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
