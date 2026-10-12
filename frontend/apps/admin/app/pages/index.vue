<template>
  <div class="page">
    <p class="page__subtitle">Открываем доступный раздел…</p>
  </div>
</template>

<script setup lang="ts">
import { SECTIONS } from "~/utils/access";

const router = useRouter();
const { can, load } = useCurrentUser();

onMounted(async () => {
  await load();

  const target = SECTIONS.find((section) =>
    section.permissions.every((permission) => can(permission)),
  );

  await router.replace(target?.path ?? "/no-access");
});
</script>
