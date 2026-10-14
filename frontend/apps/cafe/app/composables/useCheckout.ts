
import { trimQuantity } from "~/utils/money";

export function useCheckout() {
  const api = useApi();
  const { active } = useCafe();
  const { lines, clear } = useCart();
  const { isAuthenticated } = useSession();

  const saving = ref(false);
  const error = ref("");

  async function checkout(): Promise<void> {
    error.value = "";

    if (!lines.value.length) {
      error.value = "Корзина пуста";
      return;
    }

    if (!isAuthenticated.value) {
      await navigateTo("/login?next=/");
      return;
    }

    const cafe = active.value;
    if (!cafe) {
      error.value = "Сначала выберите кафе";
      return;
    }

    saving.value = true;

    try {
      const {
        data,
        response,
        error: failure,
      } = await api.POST("/api/sales/me/orders", {
        body: {
          org_unit_id: cafe.id,
          channel: "site",
          planned_at: null,
          comment: null,
          lines: lines.value.map((line) => ({
            nomenclature_id: line.nomenclature_id,


            quantity: String(trimQuantity(line.quantity)),
          })),
        },
      });

      if (!response.ok || !data) {
        const payload = failure as { message?: string } | undefined;
        error.value =
          payload?.message ?? `Не удалось оформить заказ: ${response.status}`;
        return;
      }

      const orderId = (data as { order_id?: string }).order_id;
      clear();
      await navigateTo(orderId ? `/orders/${orderId}` : "/orders");
    } finally {
      saving.value = false;
    }
  }

  return { checkout, saving, error };
}
