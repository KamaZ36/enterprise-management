# Рабочее место — фронтенд

Короткая памятка для случая «что-то сломалось, а я не фронтендер».

## Что где лежит

```
apps/admin/app/pages/        страницы (одна папка = один раздел меню)
apps/admin/app/layouts/      общий каркас: меню, шапка, смена пароля
apps/admin/app/composables/  useApi, useAuth, useCurrentUser
apps/admin/app/utils/        access.ts (права и разделы), format.ts, labels.ts
apps/admin/app/middleware/   вход и проверка прав на маршруте
packages/api-client/         клиент API + СГЕНЕРИРОВАННЫЕ типы (schema.d.ts)
packages/money/              форматирование денег и количеств
apps/admin/nuxt.config.ts    настройки: прокси на бэкенд, заголовки, стили
```

## Запуск

```bash
# бэкенд (из корня проекта)
DB_HOST=localhost .venv/bin/uvicorn --factory myasnaya_derevnya.main:create_app --host 127.0.0.1 --port 8000

# фронтенд
cd frontend
pnpm install
pnpm dev:admin          # http://127.0.0.1:3000
```

Запросы к API идут на `/api` того же адреса, а на бэкенд их проксирует сервер Nuxt
(`nitro.devProxy` в `nuxt.config.ts`). Поэтому в браузере нет CORS.

## Как устроена страница

Один и тот же шаблон во всех разделах:

```vue
<template>
  <div class="page">            <!-- без class="page" не будет отступов -->
    <h1 class="page__title">Название</h1>
    <el-table :data="items">…</el-table>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ permissions: CAN.balancesOpen });   // что нужно для входа
const api = useApi();
const items = ref([]);
async function load() {
  const { data, response } = await api.GET("/api/…", { params: { query: { … } } });
  if (response.ok && data) items.value = data.items;
}
onMounted(load);
</script>
```

## Права

- Все наборы прав — в `app/utils/access.ts` (`CAN.*`), там же разделы меню.
- Проверка в разметке: `v-if="can('some.permission')"` или `v-if="canAll(CAN.documentsCreate)"`.
- Вход в раздел: `definePageMeta({ permissions: CAN.documentsOpen })`.
- Права проверяет и бэкенд — на каждый запрос. Фронт решает только, что показывать.
- Тест `tests/test_access_map.py` сверяет коды прав из карты с реестром на бэкенде:
  опечатка падает сразу.

## Что делать, если

| Симптом | Что смотреть |
|---|---|
| Белый экран вместо страницы | Консоль браузера (F12). Обычно там прямо написано, какой файл и переменная |
| Таблица «уехала», липнет к краям | У корневого `<div>` нет `class="page"` |
| Выкинуло на вход при перезагрузке | 401 на `/api/me` в сетевой панели → проверь, что токен восстанавливается до запроса (`middleware/auth.global.ts`) |
| Кнопка не работает / «нет прав» | Права роли в разделе «Роли». Фронт только отражает то, что отдаёт бэкенд |
| `typecheck` ругается на путь API | Схема устарела: `pnpm api:types` (нужен запущенный бэкенд) |
| Сборка или типы красные | Запусти `pnpm typecheck:admin` — покажет файл и строку |
| Раздел открывается, но пустой | Смотри, есть ли у роли все права из `CAN.*` для этого раздела |

## Чего не делать

- Не править `packages/api-client/src/schema.d.ts` руками — он генерируется из бэкенда.
- Не хардкодить права и роли в коде: они живут в базе, карта `access.ts` — только имена наборов.
- Не добавлять новые состояния и библиотеки без нужды: сейчас всё построено на `ref` + `api.GET`.
