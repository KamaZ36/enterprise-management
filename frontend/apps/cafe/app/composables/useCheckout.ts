export function useCheckout() {
  const api = useApi();
  const { active } = useCafe();
  const { lines, fulfillment, clear } = useCart();
  const { push } = useCartServer();
  const { isAuthenticated } = useSession();
  const { show: showAuthModal } = useAuthModal();

  const saving = ref(false);
  const error = ref("");

  async function checkout(): Promise<void> {
    error.value = "";

    if (!lines.value.length) {
      error.value = "Корзина пуста";
      return;
    }

    if (fulfillment.value === "delivery") {
      error.value = "Доставка пока в разработке — выберите самовывоз";
      return;
    }

    if (!isAuthenticated.value) {
      showAuthModal();
      return;
    }

    const cafe = active.value;
    if (!cafe) {
      error.value = "Сначала выберите кафе";
      return;
    }

    saving.value = true;

    try {
      const saved = await push(cafe.id);
      if (!saved) {
        error.value = "Не удалось сохранить корзину";
        return;
      }

      const { data, response, error: failure } = await api.POST(
        "/api/me/cart/submit",
        { body: { org_unit_id: cafe.id } },
      );

      if (!response.ok || !data) {
        const payload = failure as { message?: string } | undefined;
        error.value =
          payload?.message ?? `Не удалось оформить заказ: ${response.status}`;
        return;
      }

      const orderId = data.order_id;
      clear();
      await navigateTo(orderId ? `/orders/${orderId}` : "/orders");
    } finally {
      saving.value = false;
    }
  }

  return { checkout, saving, error };
}
