import type { components } from "@md/api-client";

type CurrentUser = components["schemas"]["CurrentUserSchema"];

/**
 * Сбрасывает всё, что зависит от сессии.
 *
 * Кэш Nuxt живёт всё время работы приложения, а cookie — 30 дней. Без сброса
 * следующий вошедший человек наследовал бы права и точки предыдущего.
 */
export function useSessionReset() {
  function clearSessionState(): void {
    useState<CurrentUser | null>("current.user", () => null).value = null;
    useState<boolean>("current.user.loading", () => false).value = false;
    useState<unknown[]>("scope_options", () => []).value = [];
    useCookie<string | null>("scope_id", { default: () => null }).value = null;
  }

  return { clearSessionState };
}
