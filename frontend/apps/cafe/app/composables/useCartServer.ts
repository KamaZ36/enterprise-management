import type { components } from "@md/api-client";

import type { CartLine } from "~/composables/useCart";

type Cart = components["schemas"]["CartSchema"];
type CartLineDto = Cart["lines"][number];
type AssortmentItem = components["schemas"]["AssortmentItemSchema"];

export function useCartServer() {
  const api = useApi();
  const { active } = useCafe();
  const { isAuthenticated } = useSession();
  const { lines, fulfillment, apiLines, hydrate } = useCart();

  async function loadAssortment(
    orgUnitId: string,
  ): Promise<Map<string, AssortmentItem>> {
    const { data, response } = await api.GET(
      "/api/catalog/org-units/{org_unit_id}/assortment",
      { params: { path: { org_unit_id: orgUnitId } } },
    );

    const byId = new Map<string, AssortmentItem>();

    if (response.ok && data) {
      for (const item of data.items) {
        byId.set(item.nomenclature_id, item);
      }
    }

    return byId;
  }

  function toCartLine(
    line: CartLineDto,
    item: AssortmentItem | undefined,
  ): CartLine {
    return {
      nomenclature_id: line.nomenclature_id,
      name: item?.name ?? "Позиция меню",
      unit: item?.unit ?? "pcs",
      unit_price: line.unit_price,
      quantity: Number(line.quantity),
      sku: item?.sku ?? "",
      image_url: item?.image_url ?? null,
    };
  }

  /** Забирает корзину с сервера, если локальная пуста. */
  async function pull(orgUnitId: string): Promise<void> {
    const { data, response } = await api.GET("/api/sales/me/cart", {
      params: { query: { org_unit_id: orgUnitId } },
    });

    if (!response.ok || !data || !data.lines.length) {
      return;
    }

    const assortment = await loadAssortment(orgUnitId);

    hydrate(
      data.lines.map((line) =>
        toCartLine(line, assortment.get(line.nomenclature_id)),
      ),
    );
    fulfillment.value =
      data.fulfillment_type === "delivery" ? "delivery" : "pickup";
  }

  /** Сохраняет локальную корзину на сервере (локальная побеждает). */
  async function push(orgUnitId: string, comment: string | null = null): Promise<boolean> {
    const { response } = await api.PUT("/api/sales/me/cart", {
      body: {
        org_unit_id: orgUnitId,
        fulfillment_type: fulfillment.value,
        comment,
        lines: apiLines.value,
      },
    });

    return response.ok;
  }

  /**
   * Слияние при входе: если локальная корзина непустая — она заменяет
   * серверную, иначе подтягиваем серверную.
   */
  async function sync(): Promise<void> {
    if (!isAuthenticated.value) {
      return;
    }

    const cafe = active.value;
    if (!cafe) {
      return;
    }

    if (lines.value.length) {
      await push(cafe.id);
      return;
    }

    await pull(cafe.id);
  }

  return { sync, pull, push };
}
