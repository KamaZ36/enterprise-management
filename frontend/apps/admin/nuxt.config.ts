export default defineNuxtConfig({
  compatibilityDate: "2026-10-11",
  ssr: false,
  devtools: { enabled: false },
  modules: ["@element-plus/nuxt"],
  css: ["~/assets/css/main.css"],
  build: {
    transpile: ["@md/api-client", "@md/money"],
  },
  vite: {
    server: {
      allowedHosts: [".tuna.am"],
    },
    optimizeDeps: {
      include: [
        "dayjs",
        "dayjs/plugin/*.js",
        "lodash-unified",
        "openapi-fetch",
      ],
    },
  },
  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE ?? "",
    },
  },
  nitro: {
    devProxy: {
      "/api": {
        target: process.env.NUXT_API_TARGET ?? "http://127.0.0.1:8000/api",
        changeOrigin: true,
      },
    },
  },
  app: {
    head: {
      title: "Мясная деревня — рабочее место",
      htmlAttrs: { lang: "ru" },
    },
  },
});
