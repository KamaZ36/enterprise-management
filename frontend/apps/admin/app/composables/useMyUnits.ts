import { useCurrentUser } from "~/composables/useCurrentUser";

export type UnitOption = {
  id: string;
  title: string;
  permissions: string[];
};

/**
 * Точки, в которых у пользователя есть назначения ролей (из `access_map`).
 *
 * У company-wide администратора этот список пуст — там доступ ко всем
 * подразделениям, поэтому такие страницы дополнительно берут полный список
 * из `/api/business/org-units` при наличии права `org_unit.read`.
 */
export function useMyUnits() {
  const { user, load: loadUser } = useCurrentUser();

  const units = computed<UnitOption[]>(() =>
    (user.value?.scopes ?? []).map((scope) => ({
      id: scope.id,
      title: scope.title,
      permissions: Array.isArray(scope.permissions) ? scope.permissions : [],
    })),
  );

  function withPermission(permission: string): UnitOption[] {
    return units.value.filter((unit) => unit.permissions.includes(permission));
  }

  async function load(): Promise<void> {
    await loadUser();
  }

  return { units, withPermission, load };
}
