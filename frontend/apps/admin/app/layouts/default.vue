<template>
  <el-container class="shell">
    <el-aside width="236px" class="shell__aside">
      <div class="brand">
        <div class="brand__mark">МД</div>
        <div>
          <div class="brand__title">Мясная деревня</div>
          <div class="brand__subtitle">рабочее место</div>
        </div>
      </div>

      <el-menu :default-active="activeMenu" router class="shell__menu">
        <el-menu-item
          v-for="section in visibleSections"
          :key="section.path"
          :index="section.path"
        >
          <el-icon class="menu__icon">
            <component :is="ICONS[section.icon]" />
          </el-icon>
          {{ section.title }}
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="shell__header">
        <span class="shell__section">{{ sectionTitle }}</span>

        <div class="who">
          <div class="who__name">{{ currentName }}</div>
          <div class="who__position">{{ currentPosition }}</div>
        </div>

        <el-button text @click="openPassword">Сменить пароль</el-button>
        <el-button text @click="signOut">Выйти</el-button>
      </el-header>

      <el-main class="shell__main">
        <slot />
      </el-main>

      <el-dialog v-model="passwordOpen" title="Смена пароля" width="480">
        <el-form label-position="top">
          <el-form-item label="Текущий пароль">
            <el-input v-model="passwordForm.current_password" type="password" show-password />
          </el-form-item>
          <el-form-item label="Новый пароль">
            <el-input v-model="passwordForm.new_password" type="password" show-password />
            <span class="hint">не короче 8 символов</span>
          </el-form-item>

          <el-alert
            v-if="passwordError"
            :title="passwordError"
            type="error"
            :closable="false"
            show-icon
          />
          <el-alert
            v-else-if="passwordDone"
            title="Пароль изменён"
            description="На других устройствах сессии закрыты — там потребуется войти заново."
            type="success"
            :closable="false"
            show-icon
          />
        </el-form>

        <template #footer>
          <el-button @click="passwordOpen = false">
            {{ passwordDone ? "Закрыть" : "Отмена" }}
          </el-button>
          <el-button
            v-if="!passwordDone"
            type="primary"
            :loading="passwordSaving"
            :disabled="!passwordForm.current_password || passwordForm.new_password.length < 8"
            @click="changePassword"
          >
            Сменить
          </el-button>
        </template>
      </el-dialog>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { useAuth } from "~/composables/useAuth";
import { useCurrentUser } from "~/composables/useCurrentUser";

const route = useRoute();
const { signOut } = useAuth();
const { user, load, can, displayName } = useCurrentUser();

import { SECTIONS } from "~/utils/access";
import { MODULE_ICONS, MODULES } from "~/utils/modules";
import {
  Box,
  Document,
  Files,
  Goods,
  Grid,
  HomeFilled,
  Key,
  OfficeBuilding,
  User,
} from "@element-plus/icons-vue";
import type { Component } from "vue";

const ICONS = MODULE_ICONS;

const api = useApi();
const passwordOpen = ref(false);
const passwordSaving = ref(false);
const passwordError = ref("");
const passwordDone = ref(false);
const passwordForm = reactive({ current_password: "", new_password: "" });

function openPassword(): void {
  passwordError.value = "";
  passwordDone.value = false;
  passwordForm.current_password = "";
  passwordForm.new_password = "";
  passwordOpen.value = true;
}

async function changePassword(): Promise<void> {
  passwordError.value = "";
  passwordSaving.value = true;

  try {
    const { response, error: failure } = await api.POST("/api/auth/me/password", {
      body: {
        current_password: passwordForm.current_password,
        new_password: passwordForm.new_password,
      },
    });

    if (!response.ok) {
      const payload = failure as { message?: string } | undefined;
      const fallback =
        response.status === 401
          ? "Текущий пароль неверен"
          : `Не удалось сменить пароль: ${response.status}`;
      throw new Error(payload?.message ?? fallback);
    }

    passwordDone.value = true;
    passwordForm.current_password = "";
    passwordForm.new_password = "";
  } catch (cause) {
    passwordError.value = cause instanceof Error ? cause.message : "Ошибка смены пароля";
  } finally {
    passwordSaving.value = false;
  }
}


const sections = SECTIONS;



const visibleSections = computed(() => {
  const items: { path: string; title: string; icon: string }[] = [];

  for (const section of sections) {
    if (!("module" in section)) {
      items.push({
        path: section.path,
        title: section.title,
        icon: section.icon,
      });
      continue;
    }

    const module = MODULES.find((item) => item.code === section.module);

    if (!module) {
      continue;
    }

    const firstAvailable = module.tabs.find((tab) => canAll(tab.permissions));

    if (!firstAvailable) {
      continue;
    }

    items.push({
      path: firstAvailable.path,
      title: section.title,
      icon: section.icon,
    });
  }

  return items;
});

const current = computed(() =>
  visibleSections.value.find((section) => route.path.startsWith(section.path)),
);
const activeMenu = computed(() => current.value?.path ?? route.path);
const sectionTitle = computed(() => current.value?.title ?? "");
const currentName = computed(() => displayName());
const currentPosition = computed(() => user.value?.position ?? "");

onMounted(load);
</script>

<style scoped>
.shell {
  min-height: 100vh;
}

.shell__aside {
  background: #fff;
  border-right: 1px solid var(--md-border);
  display: flex;
  flex-direction: column;
}

.brand {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 18px 16px;
}

.brand__mark {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: #7f1d1d;
  color: #fff;
  display: grid;
  place-items: center;
  font-weight: 700;
  font-size: 13px;
}

.brand__title {
  font-weight: 600;
  font-size: 14px;
}

.brand__subtitle {
  color: #909399;
  font-size: 11px;
}

.shell__menu {
  border-right: none;
}

.shell__header {
  background: #fff;
  border-bottom: 1px solid var(--md-border);
  display: flex;
  align-items: center;
  gap: 16px;
}

.shell__section {
  font-weight: 600;
}

.who {
  margin-left: auto;
  text-align: right;
  line-height: 1.25;
}

.who__name {
  font-size: 13px;
  font-weight: 600;
}

.who__position {
  font-size: 11px;
  color: #909399;
}

.shell__main {
  padding: 0;
}
</style>

<style scoped>
.menu__icon {
  margin-right: 8px;
}
</style>
