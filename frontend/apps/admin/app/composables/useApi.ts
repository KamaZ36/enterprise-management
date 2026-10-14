import { createApiClient } from "@md/api-client";

import { useAccessNotice } from "~/composables/useAccessNotice";

export function useApi() {
  const config = useRuntimeConfig();
  const router = useRouter();
  const token = useState<string | null>("auth.token", () => null);


  const scopeId = useCookie<string | null>("scope_id", { default: () => null });
  const { forbidden } = useAccessNotice();

  const baseUrl =
    (config.public.apiBase as string) ||
    (import.meta.client ? window.location.origin : "http://127.0.0.1:8000");

  return createApiClient({
    baseUrl,
    getToken: () => token.value,
    getScopeId: () => scopeId.value,
    onForbidden: () => forbidden(),
    onUnauthorized: () => {
      token.value = null;
      if (import.meta.client) {
        window.localStorage.removeItem("md.admin.session");
      }
      void router.push("/login");
    },
  });
}

export function useSessionToken() {
  return useState<string | null>("auth.token", () => null);
}
