<template>
  <section class="section">
    <div class="wrap">
      <div class="kicker">Вход</div>
      <h1 class="section__title">Войти в кабинет</h1>
      <p class="muted">Введите телефон — пришлём код. Пароль не нужен.</p>

      <form
        class="form-narrow"
        @submit.prevent="codeSent ? submitCode() : requestCode()"
      >
        <label class="field">
          <span class="field__label">Телефон</span>
          <input
            v-model="phone"
            class="input"
            type="tel"
            placeholder="+7 900 000-00-00"
            :disabled="codeSent"
          />
        </label>

        <label v-if="codeSent" class="field">
          <span class="field__label">Код из СМС</span>
          <input
            v-model="code"
            class="input"
            inputmode="numeric"
            maxlength="6"
            placeholder="0000"
          />
        </label>

        <p v-if="error" class="notice notice--error">{{ error }}</p>

        <div class="actions">
          <button class="button" type="submit" :disabled="sending || logging">
            {{ codeSent ? "Войти" : "Получить код" }}
          </button>

          <button
            v-if="codeSent"
            class="link-button"
            type="button"
            @click="reset"
          >
            Изменить телефон
          </button>
        </div>
      </form>

      <p v-if="codeSent && isDev" class="muted small">
        В dev-режиме код пишется в лог бэкенда.
      </p>
    </div>
  </section>
</template>

<script setup lang="ts">
const api = useApi();
const route = useRoute();
const { set } = useSession();

const phone = ref("");
const code = ref("");
const codeSent = ref(false);
const sending = ref(false);
const logging = ref(false);
const error = ref("");
const isDev = import.meta.dev;

function cleanPhone(value: string): string {
  return value.replace(/[^\d+]/g, "");
}

function nextPath(): string {
  return typeof route.query.next === "string" && route.query.next
    ? route.query.next
    : "/";
}

async function requestCode(): Promise<void> {
  error.value = "";
  const value = cleanPhone(phone.value);

  if (value.replace(/\D/g, "").length < 10) {
    error.value = "Укажите телефон в формате +7 900 000-00-00";
    return;
  }

  sending.value = true;

  try {
    const { response } = await api.POST("/api/customers/login/code", {
      body: { phone: value },
    });

    if (!response.ok) {
      error.value = `Не удалось отправить код: ${response.status}`;
      return;
    }

    codeSent.value = true;
  } finally {
    sending.value = false;
  }
}

async function submitCode(): Promise<void> {
  error.value = "";
  logging.value = true;

  try {
    const { data, response } = await api.POST("/api/customers/login", {
      body: { phone: cleanPhone(phone.value), code: code.value.trim() },
    });

    if (!response.ok || !data) {
      error.value =
        response.status === 400 || response.status === 401
          ? "Код не подошёл. Запросите новый."
          : `Не удалось войти: ${response.status}`;
      return;
    }

    const session = (data as { session?: string }).session;
    if (!session) {
      error.value = "Сервер не вернул сессию";
      return;
    }

    set(session);
    await navigateTo(nextPath());
  } finally {
    logging.value = false;
  }
}

function reset(): void {
  codeSent.value = false;
  code.value = "";
  error.value = "";
}
</script>
