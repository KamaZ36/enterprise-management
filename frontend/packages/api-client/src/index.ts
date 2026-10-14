import createClient from "openapi-fetch";

import type { components, paths } from "./schema";

export type { components, paths };

export type ApiClient = ReturnType<typeof createApiClient>;

export function createApiClient(options: {
  baseUrl: string;
  getToken?: () => string | null;
  getScopeId?: () => string | null;
  onUnauthorized?: () => void;
  onForbidden?: () => void;
}) {
  const client = createClient<paths>({ baseUrl: options.baseUrl });

  client.use({
    onRequest({ request }) {
      const token = options.getToken?.();
      if (token) {
        request.headers.set("Authorization", `Bearer ${token}`);
      }

      const scopeId = options.getScopeId?.();
      if (scopeId) {
        request.headers.set("X-Scope-Id", scopeId);
      }

      return request;
    },
    onResponse({ request, response }) {
      const isLogin = request.url.includes("/api/auth/login");
      const isPasswordChange = request.url.includes("/api/auth/me/password");
      const hadToken = Boolean(request.headers.get("Authorization"));


      if (response.status === 403 && hadToken && request.method !== "GET") {
        options.onForbidden?.();
      }

      if (
        response.status === 401 &&
        hadToken &&
        !isLogin &&
        !isPasswordChange
      ) {
        options.onUnauthorized?.();
      }
      return response;
    },
  });

  return client;
}

export type LoginResponse = { session: string };

export async function login(
  client: ApiClient,
  credentials: { username: string; password: string },
): Promise<string> {
  const { data, response } = await client.POST("/api/auth/login/password", {
    body: credentials,
  });

  if (!response.ok || !data) {
    throw new Error(
      response.status === 401
        ? "Неверный логин или пароль"
        : `Не удалось войти: ${response.status}`,
    );
  }

  return (data as unknown as LoginResponse).session;
}

export async function logout(client: ApiClient): Promise<void> {
  await client.POST("/api/auth/logout", {});
}
