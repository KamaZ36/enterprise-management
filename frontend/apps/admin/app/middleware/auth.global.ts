export default defineNuxtRouteMiddleware(async (to) => {
  const token = useAuth().restore();

  if (!token && to.path !== "/login") {
    return navigateTo("/login");
  }

  if (token && to.path === "/login") {
    return navigateTo("/");
  }

  const required = to.meta.permissions as readonly string[] | undefined;

  if (!token || !required?.length || to.path === "/no-access") {
    return;
  }

  const { can, load } = useCurrentUser();
  await load();

  if (required.every((permission) => can(permission))) {
    return;
  }

  return navigateTo("/no-access");
});
