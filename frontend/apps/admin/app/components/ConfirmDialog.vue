<template>
  <el-dialog
    :model-value="open"
    width="420"
    align-center
    :show-close="false"
    append-to-body
    class="md-confirm"
    @update:model-value="onVisibility"
  >
    <div class="md-confirm__body">
      <span
        class="md-confirm__icon"
        :class="options.danger ? 'md-confirm__icon--danger' : 'md-confirm__icon--info'"
      >
        <el-icon :size="24">
          <WarningFilled v-if="options.danger" />
          <QuestionFilled v-else />
        </el-icon>
      </span>

      <p class="md-confirm__title">{{ options.title ?? DEFAULT_TITLE }}</p>
    </div>

    <template #footer>
      <el-button @click="settle(false)">
        {{ options.cancelText ?? "Отмена" }}
      </el-button>
      <el-button
        :type="options.danger ? 'danger' : 'primary'"
        @click="settle(true)"
      >
        {{ options.confirmText ?? "Подтвердить" }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { QuestionFilled, WarningFilled } from "@element-plus/icons-vue";

const DEFAULT_TITLE = "Подтвердите действие";

const { open, options, settle } = useConfirm();

function onVisibility(value: boolean): void {
  if (!value) {
    settle(false);
  }
}
</script>

<style>
/* Окно телепортируется в body, поэтому стили не scoped. */
.md-confirm {
  border-radius: 14px;
  overflow: hidden;
}

.md-confirm .el-dialog__header {
  display: none;
}

.md-confirm .el-dialog__body {
  padding: 24px 24px 8px;
}

.md-confirm__body {
  display: flex;
  gap: 14px;
  align-items: center;
}

.md-confirm__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 46px;
  height: 46px;
  flex: none;
  border-radius: 50%;
}

.md-confirm__icon--danger {
  color: #f56c6c;
  background: #fef0f0;
}

.md-confirm__icon--info {
  color: #409eff;
  background: #ecf5ff;
}

.md-confirm__title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  line-height: 1.4;
  color: #1f2329;
}

.md-confirm .el-dialog__footer {
  padding: 16px 24px 20px;
}
</style>
