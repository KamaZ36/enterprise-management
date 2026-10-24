# Чеки ОФД

Модуль `fiscal` загружает чеки из интеграционного API ОФД, хранит их локально
и проводит приходные чеки по складу. Doka остаётся кассой и фискализатором:
складской учёт ведёт только наша система.

## Что поддерживается в MVP

- только операция `Income` (приход);
- один склад на кассу — по привязке кассы на дату чека;
- автоматическое сопоставление по сохранённому штрихкоду или GTIN;
- ручное сопоставление строк через очередь;
- проведение только целиком: если хотя бы одна строка не сопоставлена или
  не хватает остатка, чек не проводится;
- возвраты, коррекции и БСО сохраняются, но получают статус `ignored` и
  обрабатываются вручную;
- повторная загрузка идемпотентна по
  `(reg_number, fn_number, doc_number, fiscal_sign)`.

## Настройки

Добавьте в `.env`:

```dotenv
OFD_API_URL=https://ofd.ru/api/integration/v2
OFD_API_TOKEN=...
OFD_INN=...
OFD_TIMEZONE=Europe/Moscow
OFD_REQUEST_TIMEOUT=30
# дата перехода; чеки раньше неё не загружаются
OFD_CUTOVER_DATE=2026-11-01
```

`OFD_TIMEZONE` нужен потому, что `DocDateTime` в чеке приходит без часового
пояса. Это местное время кассы; для складского документа оно переводится в UTC.

Демо-контур: `OFD_API_URL=https://lk-demo.ofd.ru/api/integration/v2`,
токен и ИНН выдаются в демо-личном кабинете ОФД. Демо-токен нельзя
использовать в продакшене.

## Синхронизация

HTTP:

```http
POST /api/fiscal/ofd/receipts/sync
Authorization: Bearer <session-uuid>
Content-Type: application/json

{
  "reg_number": "0000000000051264",
  "date_from": "2026-10-24T00:00:00",
  "date_to": "2026-10-25T00:00:00"
}
```

CLI (подходит для cron/systemd):

```bash
# за последние 6 часов
.venv/bin/myasnaya-derevnya-ofd-sync \
  --reg-number 0000000000051264 \
  --last-hours 6

# явный период
.venv/bin/myasnaya-derevnya-ofd-sync \
  --reg-number 0000000000051264 \
  --date-from 2026-10-24T00:00:00 \
  --date-to 2026-10-25T00:00:00
```

На хосте без Docker добавьте `DB_HOST=localhost`. Внутри контейнера
используется `DB_HOST=postgres` из `.env`.

Ограничения API ОФД: не больше одного запроса в секунду и не больше 31 дня
за один запрос. Клиент сам выдерживает паузу между запросами; период
проверяется до обращения к ОФД.

Если привязку кассы к складу настроили позже, следующая синхронизация этой
кассы сама проставит склад чекам в статусе `needs_location` — повторно
загружать чеки из ОФД не нужно.

### cron

```cron
*/15 * * * * cd /opt/enterprise-management && DB_HOST=localhost .venv/bin/myasnaya-derevnya-ofd-sync --reg-number 0000000000051264 --last-hours 1 >> /var/log/myasnaya-ofd.log 2>&1
```

### systemd

`/etc/systemd/system/myasnaya-ofd-sync.service`:

```ini
[Unit]
Description=Myasnaya Derevnya: загрузка чеков ОФД
After=network-online.target

[Service]
Type=oneshot
WorkingDirectory=/opt/enterprise-management
Environment=DB_HOST=localhost
ExecStart=/opt/enterprise-management/.venv/bin/myasnaya-derevnya-ofd-sync --reg-number 0000000000051264 --last-hours 1
```

`/etc/systemd/system/myasnaya-ofd-sync.timer`:

```ini
[Unit]
Description=Каждые 15 минут загружать чеки ОФД

[Timer]
OnBootSec=2min
OnUnitActiveSec=15min
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
systemctl daemon-reload
systemctl enable --now myasnaya-ofd-sync.timer
```

## Проведение

- `POST /api/fiscal/ofd/receipts/{receipt_id}/post` — один чек;
- `POST /api/fiscal/ofd/receipts/post-ready` — пачка готовых чеков
  (не больше 100 за раз).

Проведение создаёт обычную продажу в `inventory` с
`document_id = ofd_receipts.id`. Уникальность `stock_postings`
`(document_type, document_id)` защищает от повторного списания.

Если остатка не хватает, чек получает статус `failed` с текстом ошибки.
После пополнения склада его можно провести повторно.

## Статусы

| Статус | Значение |
| --- | --- |
| `new` | чек только что сохранён |
| `needs_location` | касса не привязана к складу на дату чека |
| `needs_mapping` | есть несопоставленные строки |
| `ready` | все строки сопоставлены, можно проводить |
| `posted` | чек проведён по складу |
| `failed` | ошибка проведения, можно повторить |
| `ignored` | возврат, коррекция, БСО или пустой чек |

## Сверка

Количество по статусам:

```sql
select status, count(*)
from fiscal.ofd_receipts
group by status
order by status;
```

Проведённые чеки без складского проведения (не должно быть):

```sql
select r.id, r.reg_number, r.doc_number
from fiscal.ofd_receipts r
left join inventory.stock_postings p
  on p.document_id = r.id and p.document_type = 'sale'
where r.status = 'posted' and p.id is null;
```

Складские проведения без проведённого чека (не должно быть):

```sql
select p.id, p.document_id
from inventory.stock_postings p
join fiscal.ofd_receipts r on r.id = p.document_id
where p.document_type = 'sale' and r.status <> 'posted';
```

Сумма строк должна совпадать с итогом чека:

```sql
select r.id, r.total_kopecks, sum(l.total_kopecks) as lines_total
from fiscal.ofd_receipts r
join fiscal.ofd_receipt_lines l on l.receipt_id = r.id
group by r.id, r.total_kopecks
having r.total_kopecks <> sum(l.total_kopecks);
```

## Перед запуском в продакшене

1. Зафиксировать дату перехода и указать её в `OFD_CUTOVER_DATE`.
   Синхронизация более раннего периода будет отклонена.
2. Ввести физические остатки на дату перехода отдельным документом.
3. Привязать каждую кассу к складу на дату перехода.
4. Прогнать демо-контур и проверить сопоставление реальных товаров.
5. Решить политику нехватки: `failed` (по умолчанию) или отрицательный
   остаток. Сейчас реализован только `failed`.
