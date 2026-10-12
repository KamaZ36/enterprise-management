import createClient from "openapi-fetch";

import type { components, paths } from "./schema";

export type { components, paths };

export type ApiClient = ReturnType<typeof createApiClient>;

export function createApiClient(options: {
  baseUrl: string;
  getToken?: () => string | null;
  onUnauthorized?: () => void;
}) {
  const client = createClient<paths>({ baseUrl: options.baseUrl });

  client.use({
    onRequest({ request }) {
      const token = options.getToken?.();
      if (token) {
        request.headers.set("Authorization", `Bearer ${token}`);
      }
      return request;
    },
    onResponse({ request, response }) {
      const isLogin = request.url.includes("/api/login");
      const isPasswordChange = request.url.includes("/api/me/password");
      const hadToken = Boolean(request.headers.get("Authorization"));
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
  const { data, response } = await client.POST("/api/login/password", {
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
  await client.POST("/api/logout", {});
}
