import type { components } from "@md/api-client";

type CurrentUser = components["schemas"]["CurrentUserSchema"];

export function useCurrentUser() {
  const api = useApi();
  const user = useState<CurrentUser | null>("current.user", () => null);
  const loading = useState<boolean>("current.user.loading", () => false);
  const scopeId = useCookie<string | null>("scope_id", { default: () => null });

  async function load(force = false): Promise<CurrentUser | null> {
    if (user.value && !force) {
      return user.value;
    }
    if (loading.value) {
      return user.value;
    }

    loading.value = true;
    try {
      const { data, response } = await api.GET("/api/staff/me", {});
      if (response.ok && data) {
        user.value = data;
      }

      return user.value;
    } finally {
      loading.value = false;
    }
  }


  function permissions(): readonly string[] {
    const current = user.value;
    if (!current) {
      return [];
    }

    const selected = scopeId.value;
    if (selected) {
      const scope = (current.scopes ?? []).find((item) => item.id === selected);


      if (scope && Array.isArray(scope.permissions)) {
        return scope.permissions;
      }
    }

    return current.permissions ?? [];
  }

  function can(permission: string): boolean {
    return permissions().includes(permission);
  }

  function displayName(): string {
    if (!user.value) {
      return "";
    }

    const name = [user.value.last_name, user.value.first_name, user.value.middle_name]
      .filter(Boolean)
      .join(" ");

    return name || user.value.roles[0]?.name || "Пользователь";
  }

  return { user, load, can, displayName };
}
