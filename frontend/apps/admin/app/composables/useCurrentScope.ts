export type ScopeOption = {
  id: string;
  title: string;
};

/**
 * Текущий контекст работы: точка, в которой сотрудник сейчас смотрит данные.
 * Незаполненный контекст означает «все доступные точки» — так работает директор.
 */
export function useCurrentScope() {
  const api = useApi();

  const cookie = useCookie<string | null>("scope_id", { default: () => null });
  const scopes = useState<ScopeOption[]>("scope_options", () => []);

  async function load(): Promise<void> {
    // Всегда спрашиваем заново: после смены пользователя кэш держал бы чужие точки.
    const { data } = await api.GET("/api/staff/me", {});

    // Точки и их названия приходят с сервера: клиент ничего не додумывает.
    scopes.value = (data?.scopes ?? []).map((scope) => ({
      id: scope.id,
      title: scope.title,
    }));
    const ids = scopes.value.map((scope) => scope.id);

    if (cookie.value && !ids.includes(cookie.value)) {
      cookie.value = null;
    }

    if (!cookie.value && ids.length === 1) {
      cookie.value = ids[0]!;
    }
  }

  const scopeId = computed(() => cookie.value);
  const hasChoice = computed(() => scopes.value.length > 1);

  function setScope(id: string | null): void {
    cookie.value = id;
  }

  return { scopes, scopeId, hasChoice, setScope, load };
}
