import { createApiClient } from "@md/api-client";

export function useApi() {
  const config = useRuntimeConfig();
  const { session, clear } = useSession();

  return createApiClient({
    baseUrl: String(config.public.apiBase),
    getToken: () => session.value,

    onUnauthorized: () => clear(),
  });
}
