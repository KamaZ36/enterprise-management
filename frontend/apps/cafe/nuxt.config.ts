export default defineNuxtConfig({
  compatibilityDate: "2026-10-11",
  devServer: { port: 3002, host: "127.0.0.1" },
  ssr: false,
  devtools: { enabled: false },
  css: ["~/assets/css/main.css", "~/assets/css/cafe.css"],
  build: {
    transpile: ["@md/api-client", "@md/money"],
  },
  vite: {
    server: {
      allowedHosts: [".tuna.am"],
    },
  },
  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE ?? "",

      landingUrl:
        process.env.NUXT_PUBLIC_LANDING_URL ?? "http://127.0.0.1:3001",
    },
  },
  nitro: {
    devProxy: {
      "/api": {
        target: process.env.NUXT_API_TARGET ?? "http://127.0.0.1:8000/api",
        changeOrigin: true,
      },

      "/media": {
        target: process.env.NUXT_MEDIA_TARGET ?? "http://127.0.0.1:8000/media",
        changeOrigin: true,
      },
    },
  },
  app: {
    head: {
      title: "Мясная деревня — кафе",
      htmlAttrs: { lang: "ru" },
      meta: [
        { name: "theme-color", content: "#17110e" },
        {
          name: "description",
          content: "Меню кафе «Мясная деревня»: заказ и самовывоз.",
        },
      ],
    },
  },
});
