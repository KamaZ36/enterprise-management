export function useAuthModal() {
  const open = useState<boolean>("cafe-auth-modal-open", () => false);

  function show(): void {
    open.value = true;
  }

  function hide(): void {
    open.value = false;
  }

  return { open, show, hide };
}
