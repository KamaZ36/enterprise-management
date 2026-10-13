<template>
  <div class="module">
    <div class="module__tabs">
      <el-tabs :model-value="route.path" @tab-change="go">
        <el-tab-pane v-for="tab in tabs" :key="tab.path" :name="tab.path">
          <template #label>
            <span class="module__label">
              <el-icon><component :is="MODULE_ICONS[tab.icon]" /></el-icon>
              {{ tab.title }}
            </span>
          </template>
        </el-tab-pane>
      </el-tabs>
    </div>

    <NuxtPage />
  </div>
</template>

<script setup lang="ts">
import { MODULE_ICONS, MODULES } from "~/utils/modules";

const route = useRoute();
const router = useRouter();

const tabs = computed(() =>
  (MODULES.find((item) => item.code === "staff")?.tabs ?? []).filter((tab) =>
    canAll(tab.permissions),
  ),
);

function go(path: string | number): void {
  router.push(String(path));
}
</script>

<style scoped>
.module__tabs {
  padding: 16px 24px 0;
}

.module__label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
</style>
