import { fileURLToPath } from "node:url";

export default defineNuxtConfig({
  compatibilityDate: "2026-10-11",
  devServer: { port: 3001, host: "127.0.0.1" },
  vite: {
    server: {
      allowedHosts: [".tuna.am"],
    },
  },
  css: [
    // Кириллица + латиница, только нужные начертания. Self-hosted, без внешних запросов.
    "@fontsource/lora/cyrillic-400.css",
    "@fontsource/lora/cyrillic-500.css",
    "@fontsource/lora/cyrillic-600.css",
    "@fontsource/lora/latin-400.css",
    "@fontsource/lora/latin-500.css",
    "@fontsource/lora/latin-600.css",
    "@fontsource/golos-text/cyrillic-400.css",
    "@fontsource/golos-text/cyrillic-500.css",
    "@fontsource/golos-text/cyrillic-600.css",
    "@fontsource/golos-text/latin-400.css",
    "@fontsource/golos-text/latin-500.css",
    "@fontsource/golos-text/latin-600.css",
    "~/assets/css/main.css",
  ],


  alias: {
    "@md/money": fileURLToPath(
      new URL("../../packages/money/src/index.ts", import.meta.url),
    ),
    "@md/api-client": fileURLToPath(
      new URL("../../packages/api-client/src/schema.d.ts", import.meta.url),
    ),
  },
  nitro: {
    devProxy: {
      "/api": {
        target: process.env.NUXT_API_TARGET ?? "http://127.0.0.1:8000/api",
        changeOrigin: true,
      },
    },
  },
  runtimeConfig: {

    apiBase: process.env.NUXT_API_BASE ?? "http://127.0.0.1:8000",
    public: {

      apiBase: process.env.NUXT_PUBLIC_API_BASE ?? "",

      cafeAppUrl:
        process.env.NUXT_PUBLIC_CAFE_APP_URL ?? "http://127.0.0.1:3002",
    },
  },
  app: {
    head: {
      title: "Мясная деревня — производство, магазины, кафе",
      htmlAttrs: { lang: "ru" },
      meta: [
        { name: "theme-color", content: "#17110e" },
        {
          name: "description",
          content:
            "Мясная деревня: собственное производство, свежее мясо и полуфабрикаты, кафе при производстве.",
        },
      ],
    },
  },
});
