export type ConfirmOptions = {
  title?: string;
  confirmText?: string;
  cancelText?: string;
  danger?: boolean;
};

const DEFAULT_TITLE = "Подтвердите действие";

/**
 * Единое окно подтверждения для любых критичных действий.
 *
 * Состояние держим на уровне модуля (админка без SSR), поэтому `confirm`
 * можно вызывать из любого компонента, а само окно отрисовывается один раз —
 * `<ConfirmDialog />` в `layouts/default.vue`.
 *
 * ```ts
 * if (await confirm({ title: "Удалить роль?", danger: true })) {
 *   await remove();
 * }
 * ```
 */
const open = ref(false);
const options = ref<ConfirmOptions>({});
let resolvePending: ((value: boolean) => void) | null = null;

export function useConfirm() {
  function confirm(opts: ConfirmOptions = {}): Promise<boolean> {
    // Если предыдущее окно ещё открыто — считаем его закрытым как «отмена».
    resolvePending?.(false);

    options.value = opts;
    open.value = true;

    return new Promise<boolean>((resolve) => {
      resolvePending = resolve;
    });
  }

  function settle(value: boolean): void {
    open.value = false;

    const resolve = resolvePending;
    resolvePending = null;
    resolve?.(value);
  }

  return { open, options, confirm, settle };
}
