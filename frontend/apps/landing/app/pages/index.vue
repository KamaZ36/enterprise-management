<template>
  <div>
    <section class="hero2">
      <div class="wrap hero2__inner">
        <div class="kicker">Собственное производство · Кафе · Магазины</div>
        <h1 class="hero2__title">Мясная деревня</h1>
        <p class="hero2__lead">
          Собственное производство мясной продукции, кафе и магазины.
          Производим колбасные изделия и мясные деликатесы, готовим в своём кафе
          и продаём продукцию в собственных магазинах.
        </p>
        <a href="#shops" class="button">Где купить</a>
      </div>

      <div class="hero2__badge">
        <span>Натурально</span>
      </div>

      <a href="#cafe" class="hero2__hint">Листайте вниз ↓</a>
    </section>


    <section class="section" id="cafe">
      <div class="wrap split">
        <div class="split__text">
          <div class="kicker">Кафе</div>
          <h2 class="split__title">Наше кафе</h2>
          <p class="muted">
            В меню — мясные блюда собственного производства и другие позиции на
            каждый день. Заглядывайте на обед или приходите провести время за
            хорошей едой.
          </p>

          <NuxtLink to="/cafe" class="button">Меню кафе</NuxtLink>

          <div class="features">
            <div v-for="item in cafe" :key="item.title" class="feature">
              <div class="feature__icon">{{ item.icon }}</div>
              <div class="feature__title">{{ item.title }}</div>
            </div>
          </div>
        </div>

        <div class="photo">
          <img src="/photos/cafe-1.jpg" alt="Зал кафе «Мясная деревня»" loading="lazy" />
        </div>
      </div>
    </section>

    <section class="section" id="shops">
      <div class="wrap split split--reverse">
        <div class="photo">
          <img src="/photos/shop-1.jpg" alt="Магазин «Мясная деревня»" loading="lazy" />
        </div>

        <div class="split__text">
          <div class="kicker">Магазины</div>
          <h2 class="split__title">Наши магазины</h2>
          <p class="muted">
            В наших магазинах представлена продукция собственного производства:
            колбасы, мясные деликатесы и другие изделия. Выбирайте продукты для
            повседневного стола и особых случаев.
          </p>

          <div class="features features--column">
            <div v-for="item in shops" :key="item.title" class="feature">
              <div class="feature__icon">{{ item.icon }}</div>
              <div class="feature__title">{{ item.title }}</div>
            </div>
          </div>

          <a href="#contacts" class="button">Найти магазин</a>
        </div>
      </div>
    </section>

    <section class="section" id="company">
      <div class="wrap split">
        <div class="split__text">
          <div class="kicker">О компании</div>
          <h2 class="split__title">Традиции, которые мы сохраняем</h2>
          <p class="muted">
            «Мясная деревня» выросла из небольшого производства: начинали с
            колбасных изделий и мясных деликатесов, а сегодня у нас своё
            производство, кафе и магазины. Рецепты собирали по крупицам и не
            меняем их ради скорости — варим, коптим и готовим так, как делали бы
            для своей семьи. Нам важно, чтобы на вашем столе была понятная еда:
            с честным составом и знакомым вкусом.
          </p>

          <div class="directions">
            <div v-for="item in directions" :key="item.title" class="direction">
              <div class="direction__icon">{{ item.icon }}</div>
              <div class="direction__title">{{ item.title }}</div>
              <div class="direction__text">{{ item.text }}</div>
            </div>
          </div>

          <a href="#contacts" class="button button--ghost">Связаться с нами</a>
        </div>

        <div class="photo">
          <img src="/photos/building.webp" alt="Здание «Мясная деревня»: магазин и кафе" loading="lazy" />
        </div>
      </div>
    </section>

    <section class="ribbon">
      <img src="/photos/table.jpg" alt="Ассортимент «Мясная деревня»" loading="lazy" />
    </section>

    <section class="section" id="contacts">
      <div class="wrap">
        <div class="kicker">Контакты</div>
        <h2 class="section__title">Как нас найти</h2>

        <div class="contacts">
          <div class="contact">
            <div class="contact__icon">📞</div>
            <div class="contact__title">Телефон</div>
            <div class="contact__text">+7 (000) 000-00-00</div>
          </div>

          <div class="contact">
            <div class="contact__icon">📍</div>
            <div class="contact__title">Адрес</div>
            <div class="contact__text">Укажите адрес производства и магазинов</div>
          </div>

          <div class="contact">
            <div class="contact__icon">🕘</div>
            <div class="contact__title">Часы работы</div>
            <div class="contact__text">Укажите часы работы</div>
          </div>

          <div class="map">
            <span class="photo__label">Карта проезда</span>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
const cafe = [
  { icon: "🍽️", title: "Блюда из нашей продукции" },
  { icon: "☕", title: "Уютная атмосфера" },
  { icon: "📅", title: "Бронь стола" },
];

const shops = [
  { icon: "🧊", title: "Свежая продукция каждый день" },
  { icon: "📍", title: "Удобное расположение" },
  { icon: "🏷️", title: "Приятные цены и акции" },
];

const directions = [
  {
    icon: "🏭",
    title: "Производство",
    text: "Колбасные изделия, деликатесы и полуфабрикаты",
  },
  { icon: "🍲", title: "Кафе", text: "Мясные блюда из собственной продукции" },
  { icon: "🏪", title: "Магазины", text: "Свежие продукты каждый день" },
];
</script>
