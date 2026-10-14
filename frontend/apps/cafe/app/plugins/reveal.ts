type RevealElement = HTMLElement & { __revealObserver?: IntersectionObserver };

export default defineNuxtPlugin((nuxtApp) => {
  nuxtApp.vueApp.directive("reveal", {
    mounted(element: RevealElement, binding: { value?: number }) {
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        return;
      }

      element.classList.add("reveal");

      if (typeof binding.value === "number") {
        element.style.transitionDelay = `${binding.value}ms`;
      }

      const observer = new IntersectionObserver(
        (entries) => {
          for (const entry of entries) {
            if (!entry.isIntersecting) {
              continue;
            }

            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        },
        { rootMargin: "0px 0px -60px 0px", threshold: 0.1 },
      );

      element.__revealObserver = observer;
      observer.observe(element);
    },
    unmounted(element: RevealElement) {
      element.__revealObserver?.disconnect();
    },
  });
});
