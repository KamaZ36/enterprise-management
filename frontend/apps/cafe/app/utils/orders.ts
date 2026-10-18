export const ORDER_STATUS_TITLES: Record<string, string> = {
  draft: "Черновик",
  new: "Принят, ждёт подтверждения",
  confirmed: "Подтверждён",
  preparing: "Готовится",
  ready: "Можно забирать",
  completed: "Выдан",
  cancelled: "Отменён",
};

const STATUS_CLASSES: Record<string, string> = {
  draft: "pill--info",
  new: "pill--info",
  confirmed: "pill--warning",
  preparing: "pill--warning",
  ready: "pill--success",
  completed: "pill--success",
  cancelled: "pill--danger",
};

export function orderStatusClass(status: string): string {
  return `pill ${STATUS_CLASSES[status] ?? "pill--info"}`;
}

export function formatOrderTime(value: string): string {
  return new Date(value).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}
