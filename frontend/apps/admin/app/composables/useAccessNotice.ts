import { ElNotification } from "element-plus";
import "element-plus/es/components/notification/style/css";

const DEDUP_MS = 2500;
let lastShownAt = 0;


export function useAccessNotice() {
  function forbidden(
    message = "У вас нет прав на это действие. Обратитесь к администратору.",
  ): void {
    if (!import.meta.client) {
      return;
    }

    const now = Date.now();
    if (now - lastShownAt < DEDUP_MS) {
      return;
    }
    lastShownAt = now;

    ElNotification({
      title: "Недостаточно прав",
      message,
      type: "warning",
      duration: 4000,
      showClose: true,
      position: "top-right",
    });
  }

  return { forbidden };
}
