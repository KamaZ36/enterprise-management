export default defineNuxtConfig({
  compatibilityDate: "2026-10-11",
  devServer: { port: 3001, host: "127.0.0.1" },
  css: ["~/assets/css/main.css"],
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
