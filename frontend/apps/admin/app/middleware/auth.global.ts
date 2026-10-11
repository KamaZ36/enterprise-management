export default defineNuxtRouteMiddleware((to) => {
  const token = useAuth().restore();

  if (!token && to.path !== "/login") {
    return navigateTo("/login");
  }

  if (token && to.path === "/login") {
    return navigateTo("/employees");
  }
});
