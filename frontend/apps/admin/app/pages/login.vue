<template>
  <div class="login">
    <el-card class="login__card" shadow="never">
      <div class="login__brand">Мясная деревня</div>
      <p class="login__hint">Вход для сотрудников</p>

      <el-form label-position="top" @submit.prevent="submit">
        <el-form-item label="Логин">
          <el-input v-model="username" size="large" autocomplete="username" />
        </el-form-item>

        <el-form-item label="Пароль">
          <el-input
            v-model="password"
            type="password"
            size="large"
            show-password
            autocomplete="current-password"
            @keyup.enter="submit"
          />
        </el-form-item>

        <el-alert
          v-if="error"
          :title="error"
          type="error"
          :closable="false"
          show-icon
          class="login__error"
        />

        <el-button
          type="primary"
          size="large"
          class="login__submit"
          :loading="pending"
          @click="submit"
        >
          Войти
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: false });

const { signIn } = useAuth();

const username = ref("");
const password = ref("");
const error = ref("");
const pending = ref(false);

async function submit(): Promise<void> {
  error.value = "";
  pending.value = true;

  try {
    await signIn({ username: username.value.trim(), password: password.value });
    await navigateTo("/staff/employees");
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "Не удалось войти";
  } finally {
    pending.value = false;
  }
}
</script>

<style scoped>
.login {
  min-height: 100vh;
  display: grid;
  place-items: center;
  background: linear-gradient(140deg, #1f2329 0%, #3f1d1d 100%);
}

.login__card {
  width: 380px;
  border-radius: 14px;
  padding: 8px;
}

.login__brand {
  font-size: 20px;
  font-weight: 700;
}

.login__hint {
  margin: 4px 0 20px;
  color: #909399;
  font-size: 13px;
}

.login__error {
  margin-bottom: 16px;
}

.login__submit {
  width: 100%;
}
</style>
