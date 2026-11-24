import { createApiClient } from "@md/api-client";

export function useApi(options: { timeoutMs?: number } = {}) {
  const config = useRuntimeConfig();
  const { session, clear } = useSession();

  return createApiClient({
    baseUrl: String(config.public.apiBase),
    getToken: () => session.value,
    timeoutMs: options.timeoutMs,

    onUnauthorized: () => clear(),
  });
}
