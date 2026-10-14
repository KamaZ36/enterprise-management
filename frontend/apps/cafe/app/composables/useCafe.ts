import type { components } from "@md/api-client";

export type Cafe = components["schemas"]["CafeOrgUnitSchema"];


export function useCafe() {
  const api = useApi();
  const route = useRoute();
  const code = useCookie<string | null>("cafe_code", {
    sameSite: "lax",
    path: "/",
  });

  const { data, pending } = useAsyncData(
    "cafes",
    async () => {
      const { data, response } = await api.GET("/api/business/org-units/cafe");

      return response.ok && data ? data : [];
    },
    { default: () => [] as Cafe[] },
  );

  const cafes = computed<Cafe[]>(() => data.value ?? []);

  const active = computed<Cafe | null>(() => {
    const list = cafes.value;
    if (!list.length) {
      return null;
    }

    const selected = list.find((cafe) => cafe.code === code.value);
    if (selected) {
      return selected;
    }

    return list.length === 1 ? (list[0] ?? null) : null;
  });

  watchEffect(() => {
    const queryCode =
      typeof route.query.cafe === "string" ? route.query.cafe : null;

    if (
      queryCode &&
      code.value !== queryCode &&
      cafes.value.some((cafe) => cafe.code === queryCode)
    ) {
      code.value = queryCode;
    }
  });

  function select(cafe: Cafe): void {
    code.value = cafe.code;
  }

  return { cafes, active, select, code, pending };
}
