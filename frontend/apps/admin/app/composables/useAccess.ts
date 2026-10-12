export function canAll(permissions: readonly string[]): boolean {
  const { can } = useCurrentUser();

  return permissions.every((permission) => can(permission));
}
