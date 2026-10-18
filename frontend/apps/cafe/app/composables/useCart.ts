import type { components } from "@md/api-client";

import { lineTotal, trimQuantity } from "~/utils/money";

type AssortmentItem = components["schemas"]["AssortmentItemSchema"];

export type CartLine = {
  nomenclature_id: string;
  name: string;
  unit: string;
  unit_price: number;
  quantity: number;
  sku: string;
  image_url: string | null;
};

export type Fulfillment = "pickup" | "delivery";

const STORAGE_KEY = "cafe_cart";
const FULFILLMENT_KEY = "cafe_fulfillment";


export function stepFor(unit: string | null | undefined): number {
  return unit === "pcs" ? 1 : 0.1;
}


export function firstQuantityFor(unit: string | null | undefined): number {
  return unit === "pcs" ? 1 : 0.5;
}


export function useCart() {
  const lines = useState<CartLine[]>("cafe-cart", () => []);
  const fulfillment = useState<Fulfillment>("cafe-fulfillment", () => "pickup");

  if (import.meta.client) {
    onMounted(() => {
      try {
        const raw = window.localStorage.getItem(STORAGE_KEY);
        if (raw) {
          lines.value = JSON.parse(raw) as CartLine[];
        }
      } catch {
        lines.value = [];
      }

      const storedFulfillment = window.localStorage.getItem(FULFILLMENT_KEY);
      if (storedFulfillment === "pickup" || storedFulfillment === "delivery") {
        fulfillment.value = storedFulfillment;
      }
    });

    watch(
      lines,
      (value) => {
        try {
          window.localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
        } catch {

        }
      },
      { deep: true },
    );

    watch(fulfillment, (value) => {
      try {
        window.localStorage.setItem(FULFILLMENT_KEY, value);
      } catch {

      }
    });
  }


  const count = computed(() => lines.value.length);

  const total = computed(() =>
    lines.value.reduce(
      (sum, line) => sum + lineTotal(line.quantity, line.unit_price),
      0,
    ),
  );

  function add(item: AssortmentItem): void {
    const existing = lines.value.find(
      (line) => line.nomenclature_id === item.nomenclature_id,
    );

    if (existing) {
      lines.value = lines.value.map((line) =>
        line.nomenclature_id === item.nomenclature_id
          ? {
              ...line,
              quantity: trimQuantity(
                line.quantity + stepFor(line.unit),
              ),
            }
          : line,
      );
      return;
    }

    lines.value = [
      ...lines.value,
      {
        nomenclature_id: item.nomenclature_id,
        name: item.name,
        unit: item.unit,
        unit_price: item.value,
        quantity: firstQuantityFor(item.unit),
        sku: item.sku,
        image_url: item.image_url ?? null,
      },
    ];
  }

  function setQuantity(nomenclatureId: string, quantity: number): void {
    const trimmed = trimQuantity(quantity);

    lines.value = lines.value
      .map((line) =>
        line.nomenclature_id === nomenclatureId
          ? { ...line, quantity: trimmed }
          : line,
      )
      .filter((line) => line.quantity > 0);
  }

  function increase(nomenclatureId: string): void {
    const line = lines.value.find((item) => item.nomenclature_id === nomenclatureId);
    if (!line) {
      return;
    }

    setQuantity(nomenclatureId, line.quantity + stepFor(line.unit));
  }

  function decrease(nomenclatureId: string): void {
    const line = lines.value.find((item) => item.nomenclature_id === nomenclatureId);
    if (!line) {
      return;
    }

    setQuantity(nomenclatureId, line.quantity - stepFor(line.unit));
  }

  function remove(nomenclatureId: string): void {
    lines.value = lines.value.filter(
      (line) => line.nomenclature_id !== nomenclatureId,
    );
  }

  function clear(): void {
    lines.value = [];
  }

  function hydrate(next: CartLine[]): void {
    lines.value = next;
  }

  const apiLines = computed(() =>
    lines.value.map((line) => ({
      nomenclature_id: line.nomenclature_id,
      quantity: String(trimQuantity(line.quantity)),
    })),
  );

  return {
    lines,
    count,
    total,
    fulfillment,
    apiLines,
    add,
    setQuantity,
    increase,
    decrease,
    remove,
    clear,
    hydrate,
  };
}
