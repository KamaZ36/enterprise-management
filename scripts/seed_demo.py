#!/usr/bin/env python3
"""Наполняет базу демонстрационными данными.

Складская локация — это само подразделение (типа ``shop``, ``cafe`` или
``production``). Структура подразделений:

    Магазины                           (группа)
        Магазин Грибановский на Советской  (shop)
        Магазин Рынок Борисоглебск         (shop)
    Кафе                               (группа)
        Кафе                           (cafe)
    Производство                       (группа)
        Основной цех                   (production, сырьё и готовая
                                        продукция хранятся вместе)

Дополнительно создаются категории и номенклатура, техкарты и начальные
остатки: поступления (с партиями и сроками годности), производственное
задание и перемещения готовой продукции по точкам.

Для витрины кафе дополнительно создаётся меню: категории разделов, блюда,
прайс-лист «Меню кафе» с ценами и привязка этого прайс-листа к точке
«Кафе» — без цены позиция на витрине не показывается.

Также создаются роли (кассир, менеджер кафе, мастер колбасного цеха,
директор) и сотрудники с назначенными ролями. Логины — латиницей
(см. ``STAFF_EMPLOYEES``), пароль у всех ``demo12345``.

Скрипт идемпотентен: справочники, роли и сотрудники переиспользуются, а
складские движения выполняются один раз — только если в подразделении
производства ещё нет остатков.

Бэкенд должен быть запущен (например, ``scripts/dev.sh up``).

Запуск из корня репозитория:

    DB_HOST=localhost uv run python scripts/seed_demo.py
    DB_HOST=localhost uv run python scripts/seed_demo.py --reset

``--reset`` стирает демонстрационные данные модулей (склад, производство,
заказы, каталог, клиенты), удаляет все некорневые подразделения, переносит
сотрудников и роли на новое подразделение того же типа и создаёт структуру
заново.
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
    orders.order_lines,
    orders.orders,
    orders.order_number_counters,
    catalog.prices,
    catalog.price_list_bindings,
    catalog.price_lists,
    catalog.nomenclatures,
    catalog.categories,
    customer.customers
cascade
"""

# --- Справочники -----------------------------------------------------------

# Дерево подразделений: группы верхнего уровня → точки. Точка (shop/cafe/
# production) и есть складская локация.
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
            },
            {
                "code": "SHOP_BORISOGLEBSK",
                "type": "shop",
                "name": "Магазин Рынок Борисоглебск",
                "address": "г. Борисоглебск, рынок",
                "phone_number": None,
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
            },
        ],
    },
]

CATEGORIES: list[dict[str, str]] = [
    {"key": "raw", "name": "Сырьё"},
    {"key": "finished", "name": "Готовая продукция"},
    {"key": "packaging", "name": "Упаковка"},
]

# key, sku, name, unit, category key
NOMENCLATURES: list[dict[str, str]] = [
    {
        "key": "pork",
        "sku": "RM-PORK",
        "name": "Свинина, лопатка",
        "unit": "kg",
        "category": "raw",
    },
    {
        "key": "beef",
        "sku": "RM-BEEF",
        "name": "Говядина, лопатка",
        "unit": "kg",
        "category": "raw",
    },
    {
        "key": "salt",
        "sku": "RM-SALT",
        "name": "Соль поваренная",
        "unit": "kg",
        "category": "raw",
    },
    {
        "key": "spice",
        "sku": "RM-SPICE",
        "name": "Смесь специй для колбас",
        "unit": "kg",
        "category": "raw",
    },
    {
        "key": "doctor",
        "sku": "FG-DOCTOR",
        "name": "Колбаса «Докторская»",
        "unit": "kg",
        "category": "finished",
    },
    {
        "key": "krakow",
        "sku": "FG-KRAKOW",
        "name": "Колбаса «Краковская»",
        "unit": "kg",
        "category": "finished",
    },
    {
        "key": "kotlet",
        "sku": "FG-KOTLET",
        "name": "Котлета «Домашняя»",
        "unit": "kg",
        "category": "finished",
    },
    {
        "key": "bag",
        "sku": "PK-BAG",
        "name": "Пакет фасовочный",
        "unit": "pcs",
        "category": "packaging",
    },
    {
        "key": "bottle",
        "sku": "PK-BOTTLE",
        "name": "Бутылка ПЭТ 0,5 л",
        "unit": "pcs",
        "category": "packaging",
    },
]

# Меню кафе: отдельные категории витрины и блюда-номенклатуры. Витрина кафе
# показывает позиции, у которых есть цена в прайс-листе, привязанном к точке
# (см. ``CAFE_PRICE_LIST_NAME``), поэтому для каждой позиции заводится цена.
# ``sort_order`` задаёт порядок разделов в кабинете кафе.
CAFE_CATEGORIES: list[dict[str, Any]] = [
    {"key": "snacks", "name": "Закуски", "sort_order": 30},
    {"key": "soups", "name": "Супы", "sort_order": 40},
    {"key": "hot", "name": "Горячее", "sort_order": 50},
    {"key": "deli", "name": "Мясные деликатесы", "sort_order": 60},
    {"key": "bakery", "name": "Выпечка", "sort_order": 70},
    {"key": "desserts", "name": "Десерты", "sort_order": 80},
    {"key": "drinks", "name": "Напитки", "sort_order": 90},
]

CAFE_PRICE_LIST_NAME = "Меню кафе"

# key, sku, name, unit, category key, price (руб. строкой), description
CAFE_MENU: list[dict[str, Any]] = [
    # Закуски
    {
        "key": "meat_platter",
        "sku": "MENU-MEAT-PLATTER",
        "name": "Мясное ассорти",
        "unit": "pcs",
        "category": "snacks",
        "price": "490.00",
        "description": "Домашние колбасы и деликатесы собственного производства",
    },
    {
        "key": "lard",
        "sku": "MENU-LARD",
        "name": "Сало с чесноком",
        "unit": "pcs",
        "category": "snacks",
        "price": "190.00",
        "description": "Солёное сало с чесноком и чёрным перцем",
    },
    {
        "key": "pickles",
        "sku": "MENU-PICKLES",
        "name": "Соленья домашние",
        "unit": "pcs",
        "category": "snacks",
        "price": "150.00",
        "description": "Огурцы и помидоры бочкового посола",
    },
    {
        "key": "cheese_plate",
        "sku": "MENU-CHEESE-PLATE",
        "name": "Сырная тарелка",
        "unit": "pcs",
        "category": "snacks",
        "price": "320.00",
        "description": "Выдержанные сыры с мёдом и орехами",
    },
    # Супы
    {
        "key": "borsch",
        "sku": "MENU-BORSCH",
        "name": "Борщ с говядиной",
        "unit": "pcs",
        "category": "soups",
        "price": "280.00",
        "description": "Со сметаной и пампушками",
    },
    {
        "key": "schi",
        "sku": "MENU-SCHI",
        "name": "Щи по-домашнему",
        "unit": "pcs",
        "category": "soups",
        "price": "260.00",
        "description": "Щи из свежей капусты на бульоне из свинины",
    },
    {
        "key": "solyanka",
        "sku": "MENU-SOLYANKA",
        "name": "Солянка мясная",
        "unit": "pcs",
        "category": "soups",
        "price": "320.00",
        "description": "Сборная солянка с колбасными изделиями",
    },
    {
        "key": "mushroom_soup",
        "sku": "MENU-MUSHROOM-SOUP",
        "name": "Крем-суп грибной",
        "unit": "pcs",
        "category": "soups",
        "price": "290.00",
        "description": "Бархатистый крем-суп из шампиньонов",
    },
    # Горячее
    {
        "key": "kotlet_puree",
        "sku": "MENU-KOTLET-PUREE",
        "name": "Котлета «Домашняя» с пюре",
        "unit": "pcs",
        "category": "hot",
        "price": "350.00",
        "description": "Котлета собственного производства с картофельным пюре",
    },
    {
        "key": "grill_sausage",
        "sku": "MENU-GRILL-SAUSAGE",
        "name": "Колбаски гриль",
        "unit": "pcs",
        "category": "hot",
        "price": "420.00",
        "description": "Домашние колбаски на гриле с овощами",
    },
    {
        "key": "pork_steak",
        "sku": "MENU-PORK-STEAK",
        "name": "Стейк из свинины",
        "unit": "pcs",
        "category": "hot",
        "price": "590.00",
        "description": "Сочный стейк из свиной шеи на гриле",
    },
    {
        "key": "zharkoe",
        "sku": "MENU-ZHARKOE",
        "name": "Жаркое по-домашнему",
        "unit": "pcs",
        "category": "hot",
        "price": "390.00",
        "description": "Свинина с картофелем, тушённая в горшочке",
    },
    {
        "key": "pelmeni",
        "sku": "MENU-PELMENI",
        "name": "Пельмени домашние",
        "unit": "pcs",
        "category": "hot",
        "price": "340.00",
        "description": "Ручная лепка, со сметаной",
    },
    {
        "key": "golubtsy",
        "sku": "MENU-GOLUBTSY",
        "name": "Голубцы",
        "unit": "pcs",
        "category": "hot",
        "price": "330.00",
        "description": "Голубцы с мясом и рисом в томатном соусе",
    },
    {
        "key": "shashlik",
        "sku": "MENU-SHASHLIK",
        "name": "Шашлык из свинины",
        "unit": "pcs",
        "category": "hot",
        "price": "480.00",
        "description": "Шашлык на углях с маринованным луком",
    },
    # Мясные деликатесы
    {
        "key": "doctor_100",
        "sku": "MENU-DOCTOR-100",
        "name": "Колбаса «Докторская», 100 г",
        "unit": "pcs",
        "category": "deli",
        "price": "160.00",
        "description": "Нарезка на тарелке, собственное производство",
    },
    {
        "key": "krakow_100",
        "sku": "MENU-KRAKOW-100",
        "name": "Колбаса «Краковская», 100 г",
        "unit": "pcs",
        "category": "deli",
        "price": "180.00",
        "description": "Нарезка на тарелке, собственное производство",
    },
    {
        "key": "buzhenina_100",
        "sku": "MENU-BUZHENINA-100",
        "name": "Буженина, 100 г",
        "unit": "pcs",
        "category": "deli",
        "price": "220.00",
        "description": "Запечённая свинина с пряностями",
    },
    {
        "key": "rulka_100",
        "sku": "MENU-RULKA-100",
        "name": "Рулька копчёная, 100 г",
        "unit": "pcs",
        "category": "deli",
        "price": "210.00",
        "description": "Копчёная свиная рулька",
    },
    # Выпечка
    {
        "key": "pirozhok_meat",
        "sku": "MENU-PIROZHOK-MEAT",
        "name": "Пирожок с мясом",
        "unit": "pcs",
        "category": "bakery",
        "price": "90.00",
        "description": "Дрожжевой пирожок с мясной начинкой",
    },
    {
        "key": "pirozhok_cabbage",
        "sku": "MENU-PIROZHOK-CABBAGE",
        "name": "Пирожок с капустой",
        "unit": "pcs",
        "category": "bakery",
        "price": "80.00",
        "description": "Дрожжевой пирожок с тушёной капустой",
    },
    {
        "key": "kurnik",
        "sku": "MENU-KURNIK",
        "name": "Курник",
        "unit": "pcs",
        "category": "bakery",
        "price": "140.00",
        "description": "Пирог с курицей и картофелем",
    },
    {
        "key": "belyash",
        "sku": "MENU-BELYASH",
        "name": "Беляш",
        "unit": "pcs",
        "category": "bakery",
        "price": "100.00",
        "description": "Жареный пирожок с мясом по-татарски",
    },
    {
        "key": "bliny_meat",
        "sku": "MENU-BLINY-MEAT",
        "name": "Блины с мясом",
        "unit": "pcs",
        "category": "bakery",
        "price": "210.00",
        "description": "Тонкие блины с мясной начинкой, 2 шт.",
    },
    # Десерты
    {
        "key": "medovik",
        "sku": "MENU-MEDOVIK",
        "name": "Медовик",
        "unit": "pcs",
        "category": "desserts",
        "price": "180.00",
        "description": "Медовый торт со сметанным кремом",
    },
    {
        "key": "napoleon",
        "sku": "MENU-NAPOLEON",
        "name": "Наполеон",
        "unit": "pcs",
        "category": "desserts",
        "price": "180.00",
        "description": "Слоёный торт с заварным кремом",
    },
    {
        "key": "syrniki",
        "sku": "MENU-SYRNIKI",
        "name": "Сырники со сметаной",
        "unit": "pcs",
        "category": "desserts",
        "price": "200.00",
        "description": "Творожные сырники с домашней сметаной",
    },
    {
        "key": "apple_pie",
        "sku": "MENU-APPLE-PIE",
        "name": "Пирог с яблоками",
        "unit": "pcs",
        "category": "desserts",
        "price": "150.00",
        "description": "Песочный пирог с корицей",
    },
    # Напитки
    {
        "key": "tea_black",
        "sku": "MENU-TEA-BLACK",
        "name": "Чай чёрный",
        "unit": "pcs",
        "category": "drinks",
        "price": "90.00",
        "description": "Чёрный чай в чайнике, 400 мл",
    },
    {
        "key": "tea_green",
        "sku": "MENU-TEA-GREEN",
        "name": "Чай зелёный",
        "unit": "pcs",
        "category": "drinks",
        "price": "90.00",
        "description": "Зелёный чай в чайнике, 400 мл",
    },
    {
        "key": "coffee",
        "sku": "MENU-COFFEE",
        "name": "Кофе чёрный",
        "unit": "pcs",
        "category": "drinks",
        "price": "120.00",
        "description": "Свежесваренный кофе, 200 мл",
    },
    {
        "key": "cappuccino",
        "sku": "MENU-CAPPUCCINO",
        "name": "Капучино",
        "unit": "pcs",
        "category": "drinks",
        "price": "180.00",
        "description": "Кофе с молочной пенкой, 250 мл",
    },
    {
        "key": "mors",
        "sku": "MENU-MORS",
        "name": "Морс клюквенный",
        "unit": "pcs",
        "category": "drinks",
        "price": "110.00",
        "description": "Домашний морс из клюквы, 300 мл",
    },
    {
        "key": "kompot",
        "sku": "MENU-KOMPOT",
        "name": "Компот из ягод",
        "unit": "pcs",
        "category": "drinks",
        "price": "100.00",
        "description": "Компот из сезонных ягод, 300 мл",
    },
    {
        "key": "lemonade",
        "sku": "MENU-LEMONADE",
        "name": "Лимонад домашний",
        "unit": "pcs",
        "category": "drinks",
        "price": "140.00",
        "description": "Лимонад с лимоном и мятой, 400 мл",
    },
    {
        "key": "water",
        "sku": "MENU-WATER",
        "name": "Вода минеральная, 0,5 л",
        "unit": "pcs",
        "category": "drinks",
        "price": "80.00",
        "description": "Негазированная минеральная вода",
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
        "unit": "PRODUCTION",
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
        "unit": "PRODUCTION",
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
        "unit": "PRODUCTION",
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
        "unit": "SHOP_GRBANOVSKY",
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
        "unit": "PRODUCTION",
        "tech_card": "TTK-DOCTOR",
        "batch_count": "1",
        "comment": "Замес и варка",
    },
]

# Перемещения идут после производства: развозим готовую продукцию по точкам.
TRANSFERS: list[dict[str, Any]] = [
    {
        "from_unit": "PRODUCTION",
        "to_unit": "CAFE",
        "comment": "Поставка в кафе",
        "lines": [
            {"nomenclature": "doctor", "quantity": "25"},
            {"nomenclature": "kotlet", "quantity": "15"},
        ],
    },
    {
        "from_unit": "PRODUCTION",
        "to_unit": "SHOP_GRBANOVSKY",
        "comment": "Поставка в магазин на Советской",
        "lines": [
            {"nomenclature": "doctor", "quantity": "20"},
            {"nomenclature": "krakow", "quantity": "15"},
        ],
    },
    {
        "from_unit": "PRODUCTION",
        "to_unit": "SHOP_BORISOGLEBSK",
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

    async def put(self, path: str, json: Any | None = None) -> Any:
        response = await self._client.put(path, json=json)

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
    """Убирает все некорневые подразделения (со складскими локациями).

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
) -> tuple[dict[str, str], dict[str, str]]:
    units = await api.get("/api/business/org-units")
    units_by_code = {unit["code"]: unit for unit in units}

    roots = [unit for unit in units if unit["parent_id"] is None]
    if not roots:
        raise SeedError(
            "Корневое подразделение не найдено — запустите приложение, "
            "чтобы прошёл bootstrap."
        )
    root_id = roots[0]["id"]

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

        for child in spec.get("children", []):
            await ensure_unit(child, unit_id)

        return unit_id

    for spec in ORG_STRUCTURE:
        await ensure_unit(spec, root_id)

    unit_ids_by_code["ROOT"] = root_id

    return unit_ids_by_type, unit_ids_by_code


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


async def ensure_cafe_menu(api: Api, unit_ids_by_code: dict[str, str]) -> None:
    """Заводит меню кафе: категории, блюда, прайс-лист и цены.

    Витрина кафе строится из цены в прайс-листе, привязанном к точке, поэтому
    одного каталога мало: нужен прайс-лист «Меню кафе», привязка к кафе и
    цена на каждое блюдо. Функция идемпотентна — позиции переиспользуются по
    артикулу, а цены перезаписываются.
    """
    categories = await api.get("/api/catalog/categories")
    categories_by_name = {item["name"]: item["id"] for item in categories}

    for category in CAFE_CATEGORIES:
        if category["name"] in categories_by_name:
            continue
        created = await api.post(
            "/api/catalog/categories",
            json={
                "name": category["name"],
                "parent_id": None,
                "sort_order": category["sort_order"],
            },
        )
        categories_by_name[category["name"]] = created["category_id"]
        print(f"  + категория меню «{category['name']}»")

    category_ids = {
        category["key"]: categories_by_name[category["name"]]
        for category in CAFE_CATEGORIES
    }

    nomenclature_ids: dict[str, str] = {}
    for spec in CAFE_MENU:
        found = await api.get(
            "/api/catalog/nomenclatures", search=spec["sku"], limit=100
        )
        existing = next(
            (item for item in found["items"] if item["sku"] == spec["sku"]), None
        )
        if existing is None:
            created = await api.post(
                "/api/catalog/nomenclatures",
                json={
                    "sku": spec["sku"],
                    "name": spec["name"],
                    "unit": spec["unit"],
                    "category_id": category_ids[spec["category"]],
                    "description": spec["description"],
                },
            )
            nomenclature_ids[spec["key"]] = created["nomenclature_id"]
            print(f"  + блюдо «{spec['name']}»")
        else:
            nomenclature_ids[spec["key"]] = existing["id"]

    price_lists = await api.get("/api/catalog/price-lists")
    price_list = next(
        (
            item
            for item in price_lists["items"]
            if item["name"] == CAFE_PRICE_LIST_NAME
        ),
        None,
    )
    if price_list is None:
        created = await api.post(
            "/api/catalog/price-lists", json={"name": CAFE_PRICE_LIST_NAME}
        )
        price_list_id = created["price_list_id"]
        print(f"  + прайс-лист «{CAFE_PRICE_LIST_NAME}»")
    else:
        price_list_id = price_list["id"]

    await api.put(
        f"/api/catalog/org-units/{unit_ids_by_code['CAFE']}/price-list",
        json={"price_list_id": price_list_id},
    )

    for spec in CAFE_MENU:
        await api.post(
            f"/api/catalog/price-lists/{price_list_id}/prices",
            json={
                "nomenclature_id": nomenclature_ids[spec["key"]],
                "price": spec["price"],
            },
        )

    print(
        f"  · прайс-лист «{CAFE_PRICE_LIST_NAME}» привязан к кафе, "
        f"цен выставлено: {len(CAFE_MENU)}"
    )


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
    unit_ids_by_code: dict[str, str],
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
                "org_unit_id": unit_ids_by_code[spec["unit"]],
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
    unit_ids_by_code: dict[str, str],
    tech_card_ids: dict[str, str],
) -> None:
    for spec in PRODUCTION_ORDERS:
        created = await api.post(
            "/api/production/orders",
            json={
                "org_unit_id": unit_ids_by_code[spec["unit"]],
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
    unit_ids_by_code: dict[str, str],
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
                "from_org_unit_id": unit_ids_by_code[spec["from_unit"]],
                "to_org_unit_id": unit_ids_by_code[spec["to_unit"]],
                "occurred_at": _now_iso(),
                "lines": lines,
                "comment": spec["comment"],
            },
        )
        await api.post(f"/api/inventory/transfers/{created['transfer_id']}/post")
        print(f"  + перемещение: {spec['comment']}")


async def has_stock(api: Api, org_unit_id: str) -> bool:
    balances = await api.get(f"/api/inventory/locations/{org_unit_id}/balances")

    return bool(balances["items"])


async def run(args: argparse.Namespace) -> None:
    moved_employees: list[tuple[Any, str]] = []
    moved_assignments: list[tuple[Any, str]] = []
    if args.reset:
        print("Сброс старых подразделений…")
        moved_employees, moved_assignments = await reset_demo_tree()

    api = Api(args.api_url)
    try:
        await api.login(args.username, args.password)

        print("Подразделения…")
        unit_ids_by_type, unit_ids_by_code = await ensure_org_structure(api)

        if args.reset:
            await reattach_staff(
                moved_employees, moved_assignments, unit_ids_by_type
            )

        print("Персонал…")
        await ensure_demo_staff(unit_ids_by_code)

        print("Каталог…")
        nomenclature_ids = await ensure_catalog(api)

        print("Меню кафе…")
        await ensure_cafe_menu(api, unit_ids_by_code)

        print("Техкарты…")
        tech_card_ids = await ensure_tech_cards(api, nomenclature_ids)

        if await has_stock(api, unit_ids_by_code["PRODUCTION"]):
            print("Остатки уже есть — складские движения пропущены.")
        else:
            print("Поступления…")
            await post_receipts(api, unit_ids_by_code, nomenclature_ids)
            print("Производство…")
            await post_production(api, unit_ids_by_code, tech_card_ids)
            print("Перемещения…")
            await post_transfers(api, unit_ids_by_code, nomenclature_ids)

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
