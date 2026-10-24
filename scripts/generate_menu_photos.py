#!/usr/bin/env python3
"""Рисует абстрактные обложки блюд для витрины кафе.

Кабинет кафе ищет фото блюда в ``public/menu/<SKU>.jpg`` (порядок поиска
описан в ``frontend/apps/cafe/public/menu/README.md``). Скрипт заводит такие
файлы для каждой позиции меню из ``scripts/seed_demo.py``: тёмный тёплый фон
в палитре кафе, одно световое пятно-жест и зерно. Позиции переиспользуются,
поэтому картинки идут одним набором.

Рисунок детерминирован по артикулу: повторный запуск даёт те же файлы.

Запуск из корня репозитория:

    uv run python scripts/generate_menu_photos.py
    uv run python scripts/generate_menu_photos.py --width 1400 --force

Без ``--force`` уже существующие файлы не перезаписываются.
"""

from __future__ import annotations

import argparse
import hashlib
import random
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFilter

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from seed_demo import CAFE_MENU

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "frontend" / "apps" / "cafe" / "public" / "menu"

Rgb = tuple[int, int, int]

# Палитра витрины кафе из ``cafe.css``: почти чёрный тёплый фон и янтарный
# свет. Победы разных разделов различаются оттенком, но остаются тёмными и
# тёплыми, чтобы карточки читались как один набор.
PALETTES: dict[str, dict[str, Rgb]] = {
    "snacks": {
        "base": (20, 15, 12),
        "deep": (92, 44, 24),
        "warm": (198, 116, 56),
        "light": (233, 176, 122),
    },
    "soups": {
        "base": (22, 13, 11),
        "deep": (86, 32, 20),
        "warm": (176, 74, 40),
        "light": (228, 150, 96),
    },
    "hot": {
        "base": (19, 13, 11),
        "deep": (96, 38, 20),
        "warm": (204, 96, 44),
        "light": (238, 168, 106),
    },
    "deli": {
        "base": (24, 14, 13),
        "deep": (78, 28, 26),
        "warm": (168, 62, 48),
        "light": (226, 142, 110),
    },
    "bakery": {
        "base": (24, 18, 11),
        "deep": (110, 66, 26),
        "warm": (214, 150, 66),
        "light": (245, 208, 150),
    },
    "desserts": {
        "base": (22, 14, 16),
        "deep": (84, 34, 40),
        "warm": (176, 92, 84),
        "light": (238, 176, 156),
    },
    "drinks": {
        "base": (16, 17, 14),
        "deep": (56, 60, 38),
        "warm": (150, 132, 74),
        "light": (214, 196, 140),
    },
}

GESTURES = ("orb", "arc", "beam", "plume")


def _seed_for(sku: str) -> int:
    return int(hashlib.sha256(sku.encode()).hexdigest()[:16], 16)


def _scale(color: Rgb, factor: float) -> Rgb:
    return tuple(min(255, max(0, int(channel * factor))) for channel in color)  # type: ignore[return-value]


def _jitter(color: Rgb, rng: random.Random) -> Rgb:
    """Слегка уводит оттенок, чтобы карточки не сливались в один тон."""
    shifts = (rng.uniform(-16, 16), rng.uniform(-11, 11), rng.uniform(-11, 11))

    return tuple(  # type: ignore[return-value]
        min(255, max(0, int(channel + shift)))
        for channel, shift in zip(color, shifts, strict=True)
    )


def _blurred_mask(size: tuple[int, int], draw: Any, blur: float) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw(ImageDraw.Draw(mask))
    return mask.filter(ImageFilter.GaussianBlur(blur))


def _glow_mask(
    size: tuple[int, int],
    center: tuple[float, float],
    radius: tuple[float, float],
    blur: float,
) -> Image.Image:
    cx, cy = center
    rx, ry = radius

    def draw(draw: ImageDraw.ImageDraw) -> None:
        draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=255)

    return _blurred_mask(size, draw, blur)


def _gesture_mask(
    size: tuple[int, int], gesture: str, rng: random.Random, blur: float
) -> Image.Image:
    sw, sh = size

    def draw(draw: ImageDraw.ImageDraw) -> None:
        if gesture == "orb":
            cx = rng.uniform(0.34, 0.66) * sw
            cy = rng.uniform(0.3, 0.56) * sh
            r = rng.uniform(0.14, 0.2) * sw
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=235)
            halo = r * rng.uniform(1.8, 2.4)
            draw.ellipse([cx - halo, cy - halo, cx + halo, cy + halo], fill=70)
        elif gesture == "arc":
            cx = rng.uniform(0.15, 0.85) * sw
            cy = rng.uniform(0.78, 1.15) * sh
            r = rng.uniform(0.5, 0.72) * sw
            start = rng.uniform(196, 244)
            draw.arc(
                [cx - r, cy - r, cx + r, cy + r],
                start=start,
                end=start + rng.uniform(110, 165),
                fill=210,
                width=max(4, int(sw * 0.07)),
            )
            draw.arc(
                [cx - r, cy - r, cx + r, cy + r],
                start=start + 20,
                end=start + 95,
                fill=245,
                width=max(2, int(sw * 0.025)),
            )
        elif gesture == "beam":
            x0 = rng.uniform(-0.15, 0.35) * sw
            y0 = rng.uniform(0.6, 1.0) * sh
            angle = rng.uniform(0.28, 0.5)
            length = rng.uniform(0.75, 1.05) * sw
            x1 = x0 + length
            y1 = y0 - length * angle
            draw.line([(x0, y0), (x1, y1)], fill=150, width=max(8, int(sw * 0.16)))
            draw.line([(x0, y0), (x1, y1)], fill=245, width=max(3, int(sw * 0.045)))
        else:  # plume
            for step in range(4):
                cx = rng.uniform(0.28, 0.72) * sw + (step - 1.5) * sw * 0.05
                h = rng.uniform(0.4, 0.65) * sh
                w = rng.uniform(0.05, 0.1) * sw
                base_y = rng.uniform(0.85, 1.05) * sh
                draw.ellipse(
                    [cx - w, base_y - h, cx + w, base_y],
                    fill=int(210 - step * 30),
                )

    return _blurred_mask(size, draw, blur)


def render(sku: str, category: str, width: int, height: int) -> Image.Image:
    palette = PALETTES[category]
    rng = random.Random(_seed_for(sku))

    base = _jitter(palette["base"], rng)
    deep = _jitter(palette["deep"], rng)
    warm = _jitter(palette["warm"], rng)
    light = _jitter(palette["light"], rng)

    # Маски считаем на уменьшенной копии и растягиваем — так градиенты
    # получаются гладкими и без полос при сохранении в JPEG.
    sw = max(width // 6, 48)
    sh = max(height // 6, 36)
    small = (sw, sh)

    image = Image.new("RGB", small, base)

    # Вертикальное затемнение книзу.
    depth = Image.linear_gradient("L").resize(small)
    image = Image.composite(Image.new("RGB", small, deep), image, depth)

    # Широкое тёплое свечение под жестом.
    glow = _glow_mask(
        small,
        (rng.uniform(0.3, 0.7) * sw, rng.uniform(0.25, 0.6) * sh),
        (sw * 0.55, sh * 0.62),
        sw * 0.2,
    )
    image = Image.composite(
        Image.new("RGB", small, warm), image, glow.point(lambda v: int(v * 0.42))
    )

    # Один световой жест блюда.
    gesture = rng.choice(GESTURES)
    mask = _gesture_mask(small, gesture, rng, sw * 0.035).point(
        lambda v: int(v * 0.92)
    )
    image = Image.composite(Image.new("RGB", small, light), image, mask)

    image = image.resize((width, height), Image.Resampling.BICUBIC)

    # Зерно — убирает ступеньки на градиентах.
    noise = Image.effect_noise((width, height), 20).convert("RGB")
    image = Image.blend(image, ImageChops.overlay(image, noise), 0.16)

    # Виньетка по краям.
    vignette = _glow_mask(
        (width, height),
        (width * 0.5, height * 0.46),
        (width * 0.62, height * 0.62),
        width * 0.16,
    )
    dark = Image.new("RGB", (width, height), _scale(base, 0.5))
    image = Image.composite(image, dark, vignette)

    return image


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Абстрактные обложки меню кафе")
    parser.add_argument("--width", type=int, default=1000, help="ширина, по умолчанию 1000")
    parser.add_argument(
        "--force", action="store_true", help="перезаписать существующие файлы"
    )

    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    width = args.width
    height = round(width * 3 / 4)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    created = 0
    skipped = 0
    for spec in CAFE_MENU:
        target = OUT_DIR / f"{spec['sku']}.jpg"
        if target.exists() and not args.force:
            skipped += 1
            continue

        image = render(spec["sku"], spec["category"], width, height)
        image.save(target, "JPEG", quality=82, optimize=True, progressive=True)
        created += 1

    print(f"Готово: {created} создано, {skipped} пропущено → {OUT_DIR}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
