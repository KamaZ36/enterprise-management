import { useCurrentUser } from "~/composables/useCurrentUser";

export type ScopeOption = {
  id: string;
  title: string;
};


export function useCurrentScope() {
  const { user, load: loadUser } = useCurrentUser();
  const cookie = useCookie<string | null>("scope_id", { default: () => null });


  const scopes = computed<ScopeOption[]>(() =>
    (user.value?.scopes ?? []).map((scope) => ({
      id: scope.id,
      title: scope.title,
    })),
  );

  async function load(): Promise<void> {
    await loadUser();

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

  function setScope(id: string | null | undefined): void {

    cookie.value = id || null;
  }

  return { scopes, scopeId, hasChoice, setScope, load };
}
