import { login as apiLogin, logout as apiLogout } from "@md/api-client";

const TOKEN_KEY = "md.admin.session";

export function useAuth() {
  const token = useSessionToken();
  const api = useApi();
  const router = useRouter();

  function restore(): string | null {
    if (!token.value && import.meta.client) {
      token.value = window.localStorage.getItem(TOKEN_KEY);
    }

    return token.value;
  }

  async function signIn(credentials: {
    username: string;
    password: string;
  }): Promise<void> {
    const session = await apiLogin(api, credentials);

    token.value = session;
    if (import.meta.client) {
      window.localStorage.setItem(TOKEN_KEY, session);
    }
  }

  async function signOut(): Promise<void> {
    try {
      await apiLogout(api);
    } catch {

    }

    token.value = null;
    if (import.meta.client) {
      window.localStorage.removeItem(TOKEN_KEY);
    }

    await router.push("/login");
  }

  return { token, restore, signIn, signOut };
}
