import { createApiClient } from "@md/api-client";

export function useApi() {
  const config = useRuntimeConfig();
  const router = useRouter();
  const token = useState<string | null>("auth.token", () => null);

  const baseUrl =
    (config.public.apiBase as string) ||
    (import.meta.client ? window.location.origin : "http://127.0.0.1:8000");

  return createApiClient({
    baseUrl,
    getToken: () => token.value,
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
