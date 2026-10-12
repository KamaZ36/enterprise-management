export default defineNuxtRouteMiddleware(async (to) => {
  const required = to.meta.permissions as readonly string[] | undefined;

  if (!required || required.length === 0 || to.path === "/no-access") {
    return;
  }

  const { can, load } = useCurrentUser();
  await load();

  if (required.every((permission) => can(permission))) {
    return;
  }

  return navigateTo("/no-access");
});
