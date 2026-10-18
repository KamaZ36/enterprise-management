<template>
  <Teleport to="body">
    <Transition name="auth">
      <div
        v-if="open"
        class="auth"
        role="dialog"
        aria-modal="true"
        aria-labelledby="auth-title"
        @click.self="hide"
      >
        <div class="auth__card">
          <button
            class="auth__close"
            type="button"
            aria-label="Закрыть"
            @click="hide"
          >
            <AppIcon name="close" />
          </button>

          <div class="kicker">Вход</div>
          <h2 id="auth-title" class="auth__title">Войти в кабинет</h2>
          <p class="auth__lead muted">
            Введите телефон — пришлём код. Пароль не нужен.
          </p>

          <form
            class="auth__form"
            @submit.prevent="codeSent ? submitCode() : requestCode()"
          >
            <label class="field">
              <span class="field__label">Телефон</span>
              <input
                ref="phoneInput"
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

            <button
              class="button auth__submit"
              type="submit"
              :disabled="sending || logging"
            >
              {{ submitLabel }}
            </button>

            <button
              v-if="codeSent"
              class="link-button auth__back"
              type="button"
              @click="reset"
            >
              Изменить телефон
            </button>
          </form>

          <p v-if="codeSent && isDev" class="auth__dev muted small">
            В dev-режиме код пишется в лог бэкенда.
          </p>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
const api = useApi();
const { open, hide } = useAuthModal();
const { set } = useSession();

const phone = ref("");
const code = ref("");
const codeSent = ref(false);
const sending = ref(false);
const logging = ref(false);
const error = ref("");
const isDev = import.meta.dev;

const phoneInput = ref<HTMLInputElement | null>(null);

const submitLabel = computed(() => {
  if (!codeSent.value) {
    return sending.value ? "Отправляем…" : "Получить код";
  }

  return logging.value ? "Входим…" : "Войти";
});

function cleanPhone(value: string): string {
  return value.replace(/[^\d+]/g, "");
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
    hide();
    reset();
  } finally {
    logging.value = false;
  }
}

function reset(): void {
  codeSent.value = false;
  code.value = "";
  error.value = "";
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape") {
    hide();
  }
}

watch(open, async (value) => {
  if (!import.meta.client) {
    return;
  }

  if (value) {
    reset();
    document.addEventListener("keydown", onKeydown);
    document.body.style.overflow = "hidden";
    await nextTick();
    phoneInput.value?.focus();
    return;
  }

  document.removeEventListener("keydown", onKeydown);
  document.body.style.overflow = "";
});

onBeforeUnmount(() => {
  if (import.meta.client) {
    document.removeEventListener("keydown", onKeydown);
    document.body.style.overflow = "";
  }
});
</script>

<style scoped>
.auth {
  position: fixed;
  z-index: 80;
  display: grid;
  padding: 24px;
  background: rgb(10 7 5 / 72%);
  inset: 0;
  place-items: center;
  backdrop-filter: blur(7px);
}

.auth__card {
  position: relative;
  width: 100%;
  max-width: 420px;
  padding: 34px 30px 30px;
  border: 1px solid var(--edge-strong);
  border-radius: 20px;
  background: linear-gradient(180deg, var(--surface-2), var(--surface));
  box-shadow:
    inset 0 1px 0 rgb(255 226 196 / 8%),
    0 30px 80px rgb(0 0 0 / 62%);
}

.auth__close {
  position: absolute;
  top: 14px;
  right: 14px;
  display: grid;
  width: 36px;
  height: 36px;
  place-items: center;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
  transition: color 0.2s, background 0.2s;
}

.auth__close:hover {
  background: rgb(255 255 255 / 6%);
  color: var(--text);
}

.auth__close :deep(.app-icon) {
  width: 18px;
  height: 18px;
}

.auth__title {
  margin: 0 0 8px;
  font-size: 30px;
}

.auth__lead {
  margin: 0 0 22px;
  font-size: 15px;
}

.auth__form {
  margin: 0;
}

.auth__submit {
  display: block;
  width: 100%;
  border: 0;
}

.auth__back {
  display: block;
  margin: 14px auto 0;
}

.auth__dev {
  margin: 16px 0 0;
  text-align: center;
}

.auth-enter-active,
.auth-leave-active {
  transition: opacity 0.22s ease;
}

.auth-enter-from,
.auth-leave-to {
  opacity: 0;
}

.auth-enter-active .auth__card {
  transition:
    transform 0.3s cubic-bezier(0.22, 1, 0.36, 1),
    opacity 0.3s ease;
}

.auth-enter-from .auth__card {
  opacity: 0;
  transform: translateY(18px) scale(0.97);
}

.auth-leave-active .auth__card {
  transition:
    transform 0.2s ease,
    opacity 0.2s ease;
}

.auth-leave-to .auth__card {
  opacity: 0;
  transform: translateY(8px) scale(0.98);
}

@media (prefers-reduced-motion: reduce) {
  .auth-enter-active,
  .auth-leave-active,
  .auth-enter-active .auth__card,
  .auth-leave-active .auth__card {
    transition: none;
  }
}
</style>
