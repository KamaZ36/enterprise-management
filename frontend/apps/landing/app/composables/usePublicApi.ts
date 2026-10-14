
export function usePublicApi() {
  const config = useRuntimeConfig();
  const baseURL = import.meta.server
    ? String(config.apiBase)
    : String(config.public.apiBase);

  return $fetch.create({ baseURL });
}
