import createClient from "openapi-fetch";

import type { components, paths } from "./schema";

export type { components, paths };

export type ApiClient = ReturnType<typeof createApiClient>;

const DEFAULT_TIMEOUT_MS = 30_000;

export function createApiClient(options: {
  baseUrl: string;
  getToken?: () => string | null;
  onUnauthorized?: () => void;
  onForbidden?: () => void;
  /**
   * Предельное время ожидания ответа. `0` — без ограничения (для долгих
   * операций вроде загрузки чеков из ОФД).
   */
  timeoutMs?: number;
}) {
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;

  const client = createClient<paths>({
    baseUrl: options.baseUrl,
    fetch: async (input: Request) => {
      const timeoutSignal =
        timeoutMs > 0 ? AbortSignal.timeout(timeoutMs) : undefined;
      const signal = timeoutSignal
        ? AbortSignal.any([input.signal, timeoutSignal])
        : input.signal;

      try {
        return await fetch(input, { signal });
      } catch (cause) {
        const aborted =
          typeof DOMException !== "undefined" &&
          cause instanceof DOMException &&
          (cause.name === "TimeoutError" || cause.name === "AbortError");

        if (aborted) {
          throw new Error("Сервер не ответил вовремя — попробуйте ещё раз");
        }

        throw cause;
      }
    },
  });

  client.use({
    onRequest({ request }) {
      const token = options.getToken?.();
      if (token) {
        request.headers.set("Authorization", `Bearer ${token}`);
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
