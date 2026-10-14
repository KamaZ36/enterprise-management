import { fileURLToPath } from "node:url";

export default defineNuxtConfig({
  compatibilityDate: "2026-10-11",
  devServer: { port: 3001, host: "127.0.0.1" },
  vite: {
    server: {
      allowedHosts: [".tuna.am"],
    },
  },
  css: ["~/assets/css/main.css"],


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
