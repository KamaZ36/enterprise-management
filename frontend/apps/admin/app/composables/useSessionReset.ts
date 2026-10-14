import type { components } from "@md/api-client";

type CurrentUser = components["schemas"]["CurrentUserSchema"];


export function useSessionReset() {
  function clearSessionState(): void {
    useState<CurrentUser | null>("current.user", () => null).value = null;
    useState<boolean>("current.user.loading", () => false).value = false;
    useCookie<string | null>("scope_id", { default: () => null }).value = null;
  }

  return { clearSessionState };
}
