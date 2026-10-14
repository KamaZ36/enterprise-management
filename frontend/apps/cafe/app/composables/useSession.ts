
export function useSession() {
  const session = useCookie<string | null>("cafe_session", {
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 30,
  });

  const isAuthenticated = computed(() => Boolean(session.value));

  function set(value: string): void {
    session.value = value;
  }

  function clear(): void {
    session.value = null;
  }

  return { session, isAuthenticated, set, clear };
}
