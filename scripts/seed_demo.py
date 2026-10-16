#!/usr/bin/env python3
"""Наполняет базу демонстрационными данными.

Структура подразделений и складов:

    Магазины                       (группа)
        Магазин Грибановский на Советской
            Основной склад         (shop)
        Магазин Рынок Борисоглебск
            Основной склад         (shop)
    Кафе                           (группа)
        Кафе
            Основной склад         (shop)
    Производство                   (группа)
        Основной цех
            Склад сырья            (raw)
            Склад готовой продукции (finished)

Дополнительно создаются категории и номенклатура, техкарты и начальные
остатки: поступления (с партиями и сроками годности), производственное
задание и перемещения готовой продукции по точкам.

Также создаются роли (кассир, менеджер кафе, мастер колбасного цеха,
директор) и сотрудники с назначенными ролями. Логины — латиницей
(см. ``STAFF_EMPLOYEES``), пароль у всех ``demo12345``.

Скрипт идемпотентен: справочники, роли и сотрудники переиспользуются, а
складские движения выполняются один раз — только если в складе сырья ещё
нет остатков.

Бэкенд должен быть запущен (например, ``scripts/dev.sh up``).

Запуск из корня репозитория:

    DB_HOST=localhost uv run python scripts/seed_demo.py
    DB_HOST=localhost uv run python scripts/seed_demo.py --reset

``--reset`` стирает демонстрационные данные модулей (склад, производство,
заказы, каталог, клиенты), удаляет все некорневые подразделения и склады,
переносит сотрудников и роли на новое подразделение того же типа и создаёт
структуру заново.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import text

from myasnaya_derevnya.core.database.connection import async_session_maker
from myasnaya_derevnya.core.database.transaction_manager.base import (
    TransactionManager,
)
from myasnaya_derevnya.core.dependencies import container
from myasnaya_derevnya.core.permissions import all_permissions
from myasnaya_derevnya.core.settings import settings
from myasnaya_derevnya.modules.auth.application.services.password_service import (
    PasswordService,
)
from myasnaya_derevnya.modules.auth.domain.entities.credential import (
    UserCredential,
    UserCredentialType,
)
from myasnaya_derevnya.modules.auth.domain.entities.identity import (
    UserIdentity,
    UserIdentityType,
)
from myasnaya_derevnya.modules.auth.domain.entities.user import User
from myasnaya_derevnya.modules.auth.infrastructure.repositories.credential.base import (
    CredentialRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.identity.base import (
    UserIdentityRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.user.base import (
    UserRepository,
)
from myasnaya_derevnya.modules.staff.domain.entities.employee import Employee
from myasnaya_derevnya.modules.staff.domain.entities.role import Role
from myasnaya_derevnya.modules.staff.domain.entities.role_assignment import (
    RoleAssignment,
)
from myasnaya_derevnya.modules.staff.infrastructure.repositories.employee.base import (
    EmployeeRepository,
)
from myasnaya_derevnya.modules.staff.infrastructure.repositories.role.base import (
    RoleRepository,
)
from myasnaya_derevnya.modules.staff.infrastructure.repositories.role_assignment.base import (
    RoleAssignmentRepository,
)

DEFAULT_API_URL = "http://127.0.0.1:8000"

# --reset стирает демонстрационные данные этих модулей (не трогает
# пользователей, роли и корневое подразделение), чтобы наполнить заново.
DEMO_TABLES_TRUNCATE = """
truncate table
    inventory.stock_movements,
    inventory.stock_lot_balances,
    inventory.stock_balances,
    inventory.receipt_lines,
    inventory.receipts,
    inventory.write_off_lines,
    inventory.write_offs,
    inventory.transfer_lines,
    inventory.transfers,
    inventory.stock_lots,
    inventory.stock_postings,
    production.production_order_lines,
    production.production_orders,
    production.tech_card_lines,
    production.tech_cards,
    sales.order_lines,
    sales.orders,
    sales.order_number_counters,
    catalog.prices,
    catalog.price_list_bindings,
    catalog.price_lists,
    catalog.nomenclatures,
    catalog.categories,
    customer.customers
cascade
"""

# --- Справочники -----------------------------------------------------------

# Дерево подразделений: группы верхнего уровня → точки (склады у точек).
ORG_STRUCTURE: list[dict[str, Any]] = [
    {
        "code": "GROUP_SHOPS",
        "type": "group",
        "name": "Магазины",
        "address": None,
        "phone_number": None,
        "children": [
            {
                "code": "SHOP_GRBANOVSKY",
                "type": "shop",
                "name": "Магазин Грибановский на Советской",
                "address": "с. Грибановский, ул. Советская",
                "phone_number": None,
                "warehouses": [
                    {
                        "code": "WAREHOUSE_GRBANOVSKY",
                        "name": "Основной склад",
                        "type": "shop",
                    },
                ],
            },
            {
                "code": "SHOP_BORISOGLEBSK",
                "type": "shop",
                "name": "Магазин Рынок Борисоглебск",
                "address": "г. Борисоглебск, рынок",
                "phone_number": None,
                "warehouses": [
                    {
                        "code": "WAREHOUSE_BORISOGLEBSK",
                        "name": "Основной склад",
                        "type": "shop",
                    },
                ],
            },
        ],
    },
    {
        "code": "GROUP_CAFE",
        "type": "group",
        "name": "Кафе",
        "address": None,
        "phone_number": None,
        "children": [
            {
                "code": "CAFE",
                "type": "cafe",
                "name": "Кафе",
                "address": None,
                "phone_number": None,
                "warehouses": [
                    {
                        "code": "WAREHOUSE_CAFE",
                        "name": "Основной склад",
                        "type": "shop",
                    },
                ],
            },
        ],
    },
    {
        "code": "GROUP_PRODUCTION",
        "type": "group",
        "name": "Производство",
        "address": None,
        "phone_number": None,
        "children": [
            {
                "code": "PRODUCTION",
                "type": "production",
                "name": "Основной цех",
                "address": None,
                "phone_number": None,
                "warehouses": [
                    {"code": "WAREHOUSE_RAW", "name": "Склад сырья", "type": "raw"},
                    {
                        "code": "WAREHOUSE_FINISHED",
                        "name": "Склад готовой продукции",
                        "type": "finished",
                    },
                ],
            },
        ],
    },
]

CATEGORIES: list[dict[str, str]] = [
    {"key": "raw", "name": "Сырьё"},
    {"key": "finished", "name": "Готовая продукция"},
    {"key": "packaging", "name": "Упаковка"},
]

# key, sku, name, unit, type, category key
NOMENCLATURES: list[dict[str, str]] = [
    {
        "key": "pork",
        "sku": "RM-PORK",
        "name": "Свинина, лопатка",
        "unit": "kg",
        "type": "raw_material",
        "category": "raw",
    },
    {
        "key": "beef",
        "sku": "RM-BEEF",
        "name": "Говядина, лопатка",
        "unit": "kg",
        "type": "raw_material",
        "category": "raw",
    },
    {
        "key": "salt",
        "sku": "RM-SALT",
        "name": "Соль поваренная",
        "unit": "kg",
        "type": "raw_material",
        "category": "raw",
    },
    {
        "key": "spice",
        "sku": "RM-SPICE",
        "name": "Смесь специй для колбас",
        "unit": "kg",
        "type": "raw_material",
        "category": "raw",
    },
    {
        "key": "doctor",
        "sku": "FG-DOCTOR",
        "name": "Колбаса «Докторская»",
        "unit": "kg",
        "type": "finished_good",
        "category": "finished",
    },
    {
        "key": "krakow",
        "sku": "FG-KRAKOW",
        "name": "Колбаса «Краковская»",
        "unit": "kg",
        "type": "finished_good",
        "category": "finished",
    },
    {
        "key": "kotlet",
        "sku": "FG-KOTLET",
        "name": "Котлета «Домашняя»",
        "unit": "kg",
        "type": "finished_good",
        "category": "finished",
    },
    {
        "key": "bag",
        "sku": "PK-BAG",
        "name": "Пакет фасовочный",
        "unit": "pcs",
        "type": "raw_material",
        "category": "packaging",
    },
    {
        "key": "bottle",
        "sku": "PK-BOTTLE",
        "name": "Бутылка ПЭТ 0,5 л",
        "unit": "pcs",
        "type": "raw_material",
        "category": "packaging",
    },
]

TECH_CARDS: list[dict[str, Any]] = [
    {
        "code": "TTK-DOCTOR",
        "name": "Колбаса «Докторская»",
        "basis": "input",
        "components": [
            ("pork", "60"),
            ("beef", "30"),
            ("salt", "2"),
            ("spice", "1"),
        ],
        "output": ("doctor", "90"),
    },
    {
        "code": "TTK-KOTLET",
        "name": "Котлета «Домашняя»",
        "basis": "input",
        "components": [
            ("pork", "40"),
            ("beef", "40"),
            ("salt", "1.5"),
            ("spice", "0.5"),
        ],
        "output": ("kotlet", "80"),
    },
]

DEMO_STAFF_PASSWORD = "demo12345"

# Роли и сотрудники демонстрационного стенда. Права проверяются по реестру
# `core.permissions.all_permissions()` перед созданием, чтобы не завести
# роль с опечаткой в коде права.
STAFF_ROLES: list[dict[str, Any]] = [
    {
        "code": "CASHIER",
        "name": "Кассир",
        "level": 40,
        "description": "Кассир магазина: заказы, каталог и остатки точки",
        "permissions": (
            "order.create",
            "order.read",
            "order.update",
            "order.cancel",
            "nomenclature.read",
            "category.read",
            "price.read",
            "price_list.read",
            "customer.read",
            "customer.update",
            "inventory.balance.read",
            "inventory.warehouse.read",
        ),
    },
    {
        "code": "CAFE_MANAGER",
        "name": "Менеджер кафе",
        "level": 60,
        "description": "Менеджер кафе: заказы, склад точки и просмотр цеха",
        "permissions": (
            "order.create",
            "order.read",
            "order.update",
            "order.cancel",
            "nomenclature.read",
            "category.read",
            "price.read",
            "price_list.read",
            "customer.read",
            "customer.update",
            "inventory.balance.read",
            "inventory.cost.read",
            "inventory.warehouse.read",
            "inventory.document.read",
            "inventory.document.create",
            "inventory.document.post",
            "production.order.read",
            "production.tech_card.read",
        ),
    },
    {
        "code": "SAUSAGE_MASTER",
        "name": "Мастер колбасного цеха",
        "level": 70,
        "description": "Мастер цеха: производство, техкарты и склад",
        "permissions": (
            "production.order.manage",
            "production.order.post",
            "production.order.read",
            "production.tech_card.manage",
            "production.tech_card.read",
            "inventory.balance.read",
            "inventory.cost.read",
            "inventory.warehouse.read",
            "inventory.document.read",
            "inventory.document.create",
            "inventory.document.post",
            "nomenclature.read",
            "category.read",
            "price.read",
        ),
    },
    {
        "code": "DIRECTOR",
        "name": "Директор",
        "level": 90,
        "description": "Директор: просмотр всей организации и себестоимости",
        "permissions": (
            "category.read",
            "customer.read",
            "inventory.balance.read",
            "inventory.cost.read",
            "inventory.document.read",
            "inventory.warehouse.read",
            "nomenclature.read",
            "order.read",
            "org_unit.read",
            "price.read",
            "price_list.read",
            "production.order.read",
            "production.tech_card.read",
            "staff.employee.read",
            "staff.role.read",
        ),
    },
]

# `unit` — код подразделения (или ROOT для директора), `role` — код роли.
STAFF_EMPLOYEES: list[dict[str, Any]] = [
    {
        "username": "kuznetsova",
        "first_name": "Ольга",
        "last_name": "Кузнецова",
        "position": "Кассир",
        "unit": "SHOP_GRBANOVSKY",
        "role": "CASHIER",
    },
    {
        "username": "morozova",
        "first_name": "Ирина",
        "last_name": "Морозова",
        "position": "Кассир",
        "unit": "SHOP_BORISOGLEBSK",
        "role": "CASHIER",
    },
    {
        "username": "volkov",
        "first_name": "Сергей",
        "last_name": "Волков",
        "position": "Менеджер кафе",
        "unit": "CAFE",
        "role": "CAFE_MANAGER",
    },
    {
        "username": "sokolov",
        "first_name": "Андрей",
        "last_name": "Соколов",
        "position": "Директор",
        "unit": "ROOT",
        "role": "DIRECTOR",
    },
    {
        "username": "ivanov",
        "first_name": "Пётр",
        "last_name": "Иванов",
        "position": "Мастер колбасного цеха",
        "unit": "PRODUCTION",
        "role": "SAUSAGE_MASTER",
    },
    {
        "username": "fedorov",
        "first_name": "Николай",
        "last_name": "Фёдоров",
        "position": "Мастер колбасного цеха",
        "unit": "PRODUCTION",
        "role": "SAUSAGE_MASTER",
    },
    {
        "username": "egorov",
        "first_name": "Дмитрий",
        "last_name": "Егоров",
        "position": "Мастер колбасного цеха",
        "unit": "PRODUCTION",
        "role": "SAUSAGE_MASTER",
    },
]

RECEIPTS: list[dict[str, Any]] = [
    {
        "warehouse": "WAREHOUSE_RAW",
        "supplier_name": "Мясокомбинат «Юбилейный»",
        "supplier_document_number": "SEED-ПН-0001",
        "comment": "Стартовые остатки сырья",
        "lines": [
            {
                "nomenclature": "pork",
                "quantity": "300",
                "unit_cost": "350.00",
                "lot_code": "PORK-001",
                "expires_in_days": 6,
            },
            {
                "nomenclature": "beef",
                "quantity": "150",
                "unit_cost": "420.00",
                "lot_code": "BEEF-001",
                "expires_in_days": 8,
            },
            {
                "nomenclature": "salt",
                "quantity": "50",
                "unit_cost": "25.00",
                "lot_code": "SALT-001",
                "expires_in_days": None,
            },
            {
                "nomenclature": "spice",
                "quantity": "20",
                "unit_cost": "850.00",
                "lot_code": "SPICE-001",
                "expires_in_days": None,
            },
        ],
    },
    {
        "warehouse": "WAREHOUSE_RAW",
        "supplier_name": "ООО «УпакТорг»",
        "supplier_document_number": "SEED-ПН-0002",
        "comment": "Тара и упаковка для производства",
        "lines": [
            {
                "nomenclature": "bag",
                "quantity": "2000",
                "unit_cost": "2.50",
                "lot_code": None,
                "expires_in_days": None,
            },
            {
                "nomenclature": "bottle",
                "quantity": "1000",
                "unit_cost": "12.00",
                "lot_code": None,
                "expires_in_days": None,
            },
        ],
    },
    {
        "warehouse": "WAREHOUSE_FINISHED",
        "supplier_name": "Кооператив «Домашние колбасы»",
        "supplier_document_number": "SEED-ПН-0003",
        "comment": "Закупная готовая продукция",
        "lines": [
            {
                "nomenclature": "krakow",
                "quantity": "40",
                "unit_cost": "520.00",
                "lot_code": "KRAKOW-001",
                "expires_in_days": 5,
            },
            {
                "nomenclature": "kotlet",
                "quantity": "30",
                "unit_cost": "380.00",
                "lot_code": "KOTLET-001",
                "expires_in_days": 4,
            },
        ],
    },
    {
        "warehouse": "WAREHOUSE_GRBANOVSKY",
        "supplier_name": "ООО «УпакТорг»",
        "supplier_document_number": "SEED-ПН-0004",
        "comment": "Упаковка для магазина",
        "lines": [
            {
                "nomenclature": "bag",
                "quantity": "1000",
                "unit_cost": "2.50",
                "lot_code": None,
                "expires_in_days": None,
            },
            {
                "nomenclature": "bottle",
                "quantity": "300",
                "unit_cost": "12.00",
                "lot_code": None,
                "expires_in_days": None,
            },
        ],
    },
]

PRODUCTION_ORDERS: list[dict[str, Any]] = [
    {
        "warehouse": "WAREHOUSE_RAW",
        "tech_card": "TTK-DOCTOR",
        "batch_count": "1",
        "comment": "Замес и варка",
    },
]

# Перемещения идут после производства: сначала готовую продукцию
# переносим из цеха на склад готовой продукции, затем развозим по точкам.
TRANSFERS: list[dict[str, Any]] = [
    {
        "from_warehouse": "WAREHOUSE_RAW",
        "to_warehouse": "WAREHOUSE_FINISHED",
        "comment": "Готовая продукция из цеха на склад",
        "lines": [{"nomenclature": "doctor", "quantity": "90"}],
    },
    {
        "from_warehouse": "WAREHOUSE_FINISHED",
        "to_warehouse": "WAREHOUSE_CAFE",
        "comment": "Поставка в кафе",
        "lines": [
            {"nomenclature": "doctor", "quantity": "25"},
            {"nomenclature": "kotlet", "quantity": "15"},
        ],
    },
    {
        "from_warehouse": "WAREHOUSE_FINISHED",
        "to_warehouse": "WAREHOUSE_GRBANOVSKY",
        "comment": "Поставка в магазин на Советской",
        "lines": [
            {"nomenclature": "doctor", "quantity": "20"},
            {"nomenclature": "krakow", "quantity": "15"},
        ],
    },
    {
        "from_warehouse": "WAREHOUSE_FINISHED",
        "to_warehouse": "WAREHOUSE_BORISOGLEBSK",
        "comment": "Поставка на рынок",
        "lines": [{"nomenclature": "doctor", "quantity": "15"}],
    },
]


class SeedError(RuntimeError):
    """Понятная пользователю ошибка наполнения."""


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _expiry(days: int | None) -> str | None:
    if days is None:
        return None

    return (date.today() + timedelta(days=days)).isoformat()


class Api:
    def __init__(self, base_url: str) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=30.0)

    async def login(self, username: str, password: str) -> None:
        response = await self._client.post(
            "/api/auth/login/password",
            json={"username": username, "password": password},
        )
        payload = self._json(response)
        token = payload.get("session")
        if not token:
            raise SeedError("Не удалось войти: сервер не вернул сессию")

        self._client.headers["Authorization"] = f"Bearer {token}"

    async def get(self, path: str, **params: Any) -> Any:
        response = await self._client.get(path, params=params or None)

        return self._json(response)

    async def post(self, path: str, json: Any | None = None) -> Any:
        response = await self._client.post(path, json=json)

        return self._json(response)

    async def aclose(self) -> None:
        await self._client.aclose()

    @staticmethod
    def _json(response: httpx.Response) -> Any:
        if response.status_code >= 400:
            request = response.request
            raise SeedError(
                f"{request.method} {request.url.path} → {response.status_code}: "
                f"{response.text[:400]}"
            )

        return response.json()


async def reset_demo_tree() -> tuple[list[tuple[Any, str]], list[tuple[Any, str]]]:
    """Убирает все некорневые подразделения и связанные с ними склады.

    Возвращает сотрудников и роли удаляемых подразделений, чтобы затем
    привязать их к новому подразделению того же типа.
    """
    async with async_session_maker() as session:
        root_id = (
            await session.execute(
                text(
                    "select id from business.org_units "
                    "where parent_id is null limit 1"
                )
            )
        ).scalar_one_or_none()

        if root_id is None:
            print("  · корневое подразделение не найдено — сброс пропущен")
            return [], []

        moved_employees = [
            (row[0], row[1])
            for row in (
                await session.execute(
                    text(
                        "select e.id, o.type from staff.employees e "
                        "join business.org_units o on o.id = e.org_unit_id "
                        "where o.parent_id is not null"
                    )
                )
            ).all()
        ]
        moved_assignments = [
            (row[0], row[1])
            for row in (
                await session.execute(
                    text(
                        "select ra.id, o.type from staff.role_assignments ra "
                        "join business.org_units o on o.id = ra.org_unit_id "
                        "where o.parent_id is not null"
                    )
                )
            ).all()
        ]

        await session.execute(text(DEMO_TABLES_TRUNCATE))

        await session.execute(
            text(
                "update staff.employees set org_unit_id = :root "
                "where org_unit_id is distinct from :root"
            ),
            {"root": root_id},
        )
        await session.execute(
            text(
                "update staff.role_assignments set org_unit_id = :root "
                "where org_unit_id is distinct from :root"
            ),
            {"root": root_id},
        )
        await session.execute(
            text(
                "delete from inventory.warehouses "
                "where org_unit_id is distinct from :root"
            ),
            {"root": root_id},
        )
        await session.execute(
            text(
                "delete from business.companies "
                "where org_unit_id is distinct from :root"
            ),
            {"root": root_id},
        )

        removed = 0
        while True:
            result = await session.execute(
                text(
                    "delete from business.org_units o "
                    "where o.parent_id is not null "
                    "and not exists ("
                    "  select 1 from business.org_units c "
                    "  where c.parent_id = o.id"
                    ")"
                )
            )
            removed += result.rowcount
            if result.rowcount == 0:
                break

        await session.commit()

    print(f"  · удалено подразделений: {removed}")

    return moved_employees, moved_assignments


async def reattach_staff(
    employees: list[tuple[Any, str]],
    assignments: list[tuple[Any, str]],
    unit_ids_by_type: dict[str, str],
) -> None:
    """Возвращает сотрудников и роли на новое подразделение того же типа."""
    if not employees and not assignments:
        return

    async with async_session_maker() as session:
        for table, rows in (
            ("staff.employees", employees),
            ("staff.role_assignments", assignments),
        ):
            for row_id, old_type in rows:
                target = unit_ids_by_type.get(old_type)
                if target is None:
                    continue
                await session.execute(
                    text(
                        f"update {table} set org_unit_id = :target "
                        "where id = :id"
                    ),
                    {"target": target, "id": row_id},
                )
        await session.commit()

    print(f"  · сотрудников перенесено: {len(employees)}")


async def ensure_org_structure(
    api: Api,
) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    units = await api.get("/api/business/org-units")
    units_by_code = {unit["code"]: unit for unit in units}

    roots = [unit for unit in units if unit["parent_id"] is None]
    if not roots:
        raise SeedError(
            "Корневое подразделение не найдено — запустите приложение, "
            "чтобы прошёл bootstrap."
        )
    root_id = roots[0]["id"]

    warehouses = await api.get("/api/inventory/warehouses")
    warehouses_by_code = {item["code"]: item["id"] for item in warehouses}

    warehouse_ids: dict[str, str] = {}
    unit_ids_by_type: dict[str, str] = {}
    unit_ids_by_code: dict[str, str] = {}

    async def ensure_unit(spec: dict[str, Any], parent_id: str) -> str:
        unit = units_by_code.get(spec["code"])
        if unit is None:
            created = await api.post(
                "/api/business/org-units",
                json={
                    "parent_id": parent_id,
                    "type": spec["type"],
                    "code": spec["code"],
                    "name": spec["name"],
                    "address": spec.get("address"),
                    "phone_number": spec.get("phone_number"),
                },
            )
            unit_id = created["org_unit_id"]
            print(f"  + подразделение «{spec['name']}»")
        else:
            unit_id = unit["id"]
            print(f"  · подразделение «{spec['name']}» уже есть")

        unit_ids_by_type.setdefault(spec["type"], unit_id)
        unit_ids_by_code[spec["code"]] = unit_id

        for warehouse in spec.get("warehouses", []):
            existing_w = warehouses_by_code.get(warehouse["code"])
            if existing_w is not None:
                warehouse_ids[warehouse["code"]] = existing_w
                print(f"      · склад «{warehouse['name']}» уже есть")
                continue

            created_w = await api.post(
                "/api/inventory/warehouses",
                json={
                    "org_unit_id": unit_id,
                    "code": warehouse["code"],
                    "name": warehouse["name"],
                    "type": warehouse["type"],
                },
            )
            warehouse_ids[warehouse["code"]] = created_w["warehouse_id"]
            print(f"      + склад «{warehouse['name']}» ({warehouse['type']})")

        for child in spec.get("children", []):
            await ensure_unit(child, unit_id)

        return unit_id

    for spec in ORG_STRUCTURE:
        await ensure_unit(spec, root_id)

    unit_ids_by_code["ROOT"] = root_id

    return warehouse_ids, unit_ids_by_type, unit_ids_by_code


async def ensure_demo_staff(unit_ids_by_code: dict[str, str]) -> None:
    """Создаёт роли и сотрудников демо-стенда (идемпотентно).

    Работает через контейнер приложения (как ``core/seed.py``) — так пароль
    демо-сотрудников фиксирован, а учётные записи можно завести с известным
    логином. Если сотрудник уже есть, ему восстанавливается нужное
    подразделение и назначение роли (например, после ``--reset``).
    """
    known_permissions = {permission.code for permission in all_permissions()}
    for role_spec in STAFF_ROLES:
        unknown = set(role_spec["permissions"]) - known_permissions
        if unknown:
            raise SeedError(
                f"В роли {role_spec['code']} неизвестные права: "
                f"{', '.join(sorted(unknown))}"
            )

    async with container() as context:
        user_repository = await context.get(UserRepository)
        identity_repository = await context.get(UserIdentityRepository)
        credential_repository = await context.get(CredentialRepository)
        employee_repository = await context.get(EmployeeRepository)
        role_repository = await context.get(RoleRepository)
        assignment_repository = await context.get(RoleAssignmentRepository)
        password_service = await context.get(PasswordService)
        transaction_manager = await context.get(TransactionManager)

        role_ids: dict[str, UUID] = {}
        for spec in STAFF_ROLES:
            role = await role_repository.get_by_code(spec["code"])
            if role is None:
                role = Role.create(
                    code=spec["code"],
                    name=spec["name"],
                    level=spec["level"],
                    description=spec["description"],
                    is_system=False,
                    is_assignable=True,
                    is_wildcard=False,
                    permission_codes=frozenset(spec["permissions"]),
                    grantable_role_ids=frozenset(),
                )
                await role_repository.add(role)
                print(f"  + роль «{spec['name']}»")
            else:
                print(f"  · роль «{spec['name']}» уже есть")

            role_ids[spec["code"]] = role.id

        admin_identity = await identity_repository.get_by_identifier_and_type(
            identifier=settings.initial_admin_username,
            identity_type=UserIdentityType.USERNAME,
        )
        grantor = admin_identity.user_id if admin_identity is not None else None

        managed_role_ids = frozenset(role_ids.values())

        for spec in STAFF_EMPLOYEES:
            target_unit_id = UUID(unit_ids_by_code[spec["unit"]])
            role_id = role_ids[spec["role"]]

            identity = await identity_repository.get_by_identifier_and_type(
                identifier=spec["username"],
                identity_type=UserIdentityType.USERNAME,
            )
            created_user = identity is None
            if identity is None:
                user = User.create()
                identity = UserIdentity.create(
                    user_id=user.id,
                    identity_type=UserIdentityType.USERNAME,
                    identifier=spec["username"],
                )
                credential = UserCredential.create(
                    user_id=user.id,
                    credential_type=UserCredentialType.PASSWORD,
                    secret=password_service.hash(DEMO_STAFF_PASSWORD),
                )
                await user_repository.add(user)
                await identity_repository.add(identity)
                await credential_repository.add(credential)

            user_id = identity.user_id

            employee = await employee_repository.get_by_user_id(user_id)
            if employee is None:
                employee = Employee.create(
                    user_id=user_id,
                    org_unit_id=target_unit_id,
                    first_name=spec["first_name"],
                    last_name=spec["last_name"],
                    middle_name=spec.get("middle_name"),
                    phone_number=None,
                    position=spec["position"],
                    hired_at=date.today(),
                )
                await employee_repository.add(employee)
            elif employee.org_unit_id != target_unit_id:
                employee.transfer_to(target_unit_id)
                await employee_repository.save(employee)

            resolved = await assignment_repository.load_active_for_user(
                user_id=user_id
            )
            has_expected = any(
                item.role.id == role_id
                and item.assignment.org_unit_id == target_unit_id
                and item.assignment.include_descendants
                for item in resolved
            )
            if not has_expected:
                for item in resolved:
                    if item.assignment.role_id in managed_role_ids:
                        item.assignment.revoke()
                        await assignment_repository.save(item.assignment)

                await assignment_repository.add(
                    RoleAssignment.create(
                        user_id=user_id,
                        role_id=role_id,
                        org_unit_id=target_unit_id,
                        include_descendants=True,
                        granted_by=grantor or user_id,
                    )
                )

            if created_user:
                print(
                    f"  + сотрудник «{spec['last_name']} {spec['first_name']}» "
                    f"— {spec['position']} (логин {spec['username']})"
                )
            else:
                print(
                    f"  · сотрудник «{spec['last_name']} {spec['first_name']}» "
                    f"уже есть (логин {spec['username']})"
                )

        await transaction_manager.commit()

    print(f"  · пароль всех демо-сотрудников: {DEMO_STAFF_PASSWORD}")


async def ensure_catalog(api: Api) -> dict[str, str]:
    categories = await api.get("/api/catalog/categories")
    categories_by_name = {item["name"]: item["id"] for item in categories}

    for category in CATEGORIES:
        if category["name"] in categories_by_name:
            continue
        created = await api.post(
            "/api/catalog/categories",
            json={"name": category["name"], "parent_id": None, "sort_order": 0},
        )
        categories_by_name[category["name"]] = created["category_id"]
        print(f"  + категория «{category['name']}»")

    nomenclatures = await api.get("/api/catalog/nomenclatures", limit=100)
    by_sku = {item["sku"]: item for item in nomenclatures["items"]}

    nomenclature_ids: dict[str, str] = {}
    for spec in NOMENCLATURES:
        existing = by_sku.get(spec["sku"])
        if existing is None:
            created = await api.post(
                "/api/catalog/nomenclatures",
                json={
                    "sku": spec["sku"],
                    "name": spec["name"],
                    "unit": spec["unit"],
                    "type": spec["type"],
                    "category_id": categories_by_name[
                        next(
                            category["name"]
                            for category in CATEGORIES
                            if category["key"] == spec["category"]
                        )
                    ],
                },
            )
            nomenclature_ids[spec["key"]] = created["nomenclature_id"]
            print(f"  + номенклатура «{spec['name']}»")
        else:
            nomenclature_ids[spec["key"]] = existing["id"]

    return nomenclature_ids


async def ensure_tech_cards(api: Api, nomenclature_ids: dict[str, str]) -> dict[str, str]:
    cards = await api.get("/api/production/tech-cards", limit=100)
    by_code = {card["code"]: card["id"] for card in cards["items"]}

    for spec in TECH_CARDS:
        if spec["code"] in by_code:
            print(f"  · техкарта «{spec['name']}» уже есть")
            continue

        lines = [
            {
                "role": "component",
                "quantity": quantity,
                "nomenclature_id": nomenclature_ids[key],
            }
            for key, quantity in spec["components"]
        ]
        output_key, output_quantity = spec["output"]
        lines.append(
            {
                "role": "output",
                "quantity": output_quantity,
                "nomenclature_id": nomenclature_ids[output_key],
                "output_kind": "main",
            }
        )

        created = await api.post(
            "/api/production/tech-cards",
            json={
                "code": spec["code"],
                "name": spec["name"],
                "basis": spec["basis"],
                "lines": lines,
            },
        )
        by_code[spec["code"]] = created["id"]
        print(f"  + техкарта «{spec['name']}»")

    return by_code


async def post_receipts(
    api: Api,
    warehouse_ids: dict[str, str],
    nomenclature_ids: dict[str, str],
) -> None:
    for spec in RECEIPTS:
        lines = [
            {
                "nomenclature_id": nomenclature_ids[line["nomenclature"]],
                "quantity": line["quantity"],
                "unit_cost": line["unit_cost"],
                "lot_code": line["lot_code"],
                "expires_at": _expiry(line["expires_in_days"]),
            }
            for line in spec["lines"]
        ]

        created = await api.post(
            "/api/inventory/receipts",
            json={
                "warehouse_id": warehouse_ids[spec["warehouse"]],
                "occurred_at": _now_iso(),
                "lines": lines,
                "supplier_name": spec["supplier_name"],
                "supplier_document_number": spec["supplier_document_number"],
                "comment": spec["comment"],
            },
        )
        await api.post(f"/api/inventory/receipts/{created['receipt_id']}/post")
        print(f"  + поступление «{spec['supplier_document_number']}»")


async def post_production(
    api: Api,
    warehouse_ids: dict[str, str],
    tech_card_ids: dict[str, str],
) -> None:
    for spec in PRODUCTION_ORDERS:
        created = await api.post(
            "/api/production/orders",
            json={
                "warehouse_id": warehouse_ids[spec["warehouse"]],
                "tech_card_id": tech_card_ids[spec["tech_card"]],
                "batch_count": spec["batch_count"],
                "occurred_at": _now_iso(),
                "comment": spec["comment"],
            },
        )
        await api.post(f"/api/production/orders/{created['id']}/post")
        print(f"  + производственное задание по {spec['tech_card']}")


async def post_transfers(
    api: Api,
    warehouse_ids: dict[str, str],
    nomenclature_ids: dict[str, str],
) -> None:
    for spec in TRANSFERS:
        lines = [
            {
                "nomenclature_id": nomenclature_ids[line["nomenclature"]],
                "quantity": line["quantity"],
            }
            for line in spec["lines"]
        ]

        created = await api.post(
            "/api/inventory/transfers",
            json={
                "from_warehouse_id": warehouse_ids[spec["from_warehouse"]],
                "to_warehouse_id": warehouse_ids[spec["to_warehouse"]],
                "occurred_at": _now_iso(),
                "lines": lines,
                "comment": spec["comment"],
            },
        )
        await api.post(f"/api/inventory/transfers/{created['transfer_id']}/post")
        print(f"  + перемещение: {spec['comment']}")


async def has_stock(api: Api, warehouse_id: str) -> bool:
    balances = await api.get(f"/api/inventory/warehouses/{warehouse_id}/balances")

    return bool(balances["items"])


async def run(args: argparse.Namespace) -> None:
    moved_employees: list[tuple[Any, str]] = []
    moved_assignments: list[tuple[Any, str]] = []
    if args.reset:
        print("Сброс старых подразделений и складов…")
        moved_employees, moved_assignments = await reset_demo_tree()

    api = Api(args.api_url)
    try:
        await api.login(args.username, args.password)

        print("Подразделения и склады…")
        warehouse_ids, unit_ids_by_type, unit_ids_by_code = (
            await ensure_org_structure(api)
        )

        if args.reset:
            await reattach_staff(
                moved_employees, moved_assignments, unit_ids_by_type
            )

        print("Персонал…")
        await ensure_demo_staff(unit_ids_by_code)

        print("Каталог…")
        nomenclature_ids = await ensure_catalog(api)

        print("Техкарты…")
        tech_card_ids = await ensure_tech_cards(api, nomenclature_ids)

        if await has_stock(api, warehouse_ids["WAREHOUSE_RAW"]):
            print("Остатки уже есть — складские движения пропущены.")
        else:
            print("Поступления…")
            await post_receipts(api, warehouse_ids, nomenclature_ids)
            print("Производство…")
            await post_production(api, warehouse_ids, tech_card_ids)
            print("Перемещения…")
            await post_transfers(api, warehouse_ids, nomenclature_ids)

        print("\nГотово.")
    finally:
        await api.aclose()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Демо-данные для Мясной деревни")
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="admin")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="стереть демо-данные и подразделения перед наполнением",
    )

    return parser.parse_args(argv)


def main() -> int:
    args = parse_args(sys.argv[1:])
    try:
        asyncio.run(run(args))
    except SeedError as error:
        print(f"\nОшибка: {error}", file=sys.stderr)

        return 1
    except (httpx.ConnectError, OSError) as error:
        print(
            f"\nНе удалось подключиться к API ({args.api_url}): {error}\n"
            "Убедитесь, что бэкенд запущен (scripts/dev.sh up).",
            file=sys.stderr,
        )

        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
