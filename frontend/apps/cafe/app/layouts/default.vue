<template>
  <div class="shell">
    <header class="top">
      <div class="wrap top__inner">
        <NuxtLink to="/" class="brand">
          <span class="brand__text">Мясная деревня</span>
        </NuxtLink>

        <nav class="nav">
          <NuxtLink to="/" class="is-active">Кафе</NuxtLink>
          <a :href="landingUrl">Магазины</a>
          <a :href="landingUrl">О компании</a>
          <a :href="`${landingUrl}#contacts`">Контакты</a>
        </nav>

        <div class="top__right">
          <select
            v-if="cafes.length > 1"
            class="select"
            :value="active?.code ?? ''"
            @change="onSelect"
          >
            <option v-for="cafe in cafes" :key="cafe.id" :value="cafe.code">
              {{ cafe.name }}
            </option>
          </select>

          <button
            v-if="isAuthenticated"
            class="button button--ghost button--small top-button"
            type="button"
            @click="logout"
          >
            <AppIcon name="user" :size="17" />
            Выйти
          </button>
          <NuxtLink
            v-else
            to="/login"
            class="button button--ghost button--small top-button"
          >
            <AppIcon name="user" :size="17" />
            Войти
          </NuxtLink>

          <NuxtLink
            to="/cart"
            class="button button--small top-button"
            :class="{ 'is-bumped': bump }"
          >
            <AppIcon name="cart" :size="17" />
            Корзина<template v-if="count"> · {{ count }}</template>
          </NuxtLink>
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
          <div class="muted">Кафе и магазины</div>
        </div>

        <div class="bottom__contacts">
          <NuxtLink to="/orders">Мои заказы</NuxtLink>
          <a :href="landingUrl">На главную</a>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
const api = useApi();
const config = useRuntimeConfig();
const landingUrl = String(config.public.landingUrl);

const { cafes, active, select, code } = useCafe();
const { count, clear } = useCart();
const { isAuthenticated, clear: clearSession } = useSession();


const bump = ref(false);
let bumpTimer: ReturnType<typeof setTimeout> | undefined;

watch(count, (value, previous) => {
  if (value <= previous) {
    return;
  }

  bump.value = true;
  clearTimeout(bumpTimer);
  bumpTimer = setTimeout(() => {
    bump.value = false;
  }, 450);
});

onBeforeUnmount(() => clearTimeout(bumpTimer));

function onSelect(event: Event): void {
  const value = (event.target as HTMLSelectElement).value;
  const cafe = cafes.value.find((item) => item.code === value);
  if (!cafe) {
    return;
  }

  select(cafe);

  clear();
}

async function logout(): Promise<void> {
  await api.POST("/api/auth/logout", {});
  clearSession();
  await navigateTo("/");
}


watch(
  [cafes, code],
  () => {
    if (active.value && code.value !== active.value.code) {
      select(active.value);
    }
  },
  { immediate: true },
);
</script>
