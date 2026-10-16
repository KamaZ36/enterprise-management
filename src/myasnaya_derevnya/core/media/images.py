import io
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError

from myasnaya_derevnya.core.errors import ValidationError


class UnsupportedImageError(ValidationError):
    def __str__(self) -> str:
        return "Не удалось прочитать изображение: нужен JPG, PNG или WebP."


class ImageTooLargeError(ValidationError):
    def __init__(self, max_bytes: int) -> None:
        self._max_bytes = max_bytes

    def __str__(self) -> str:
        limit = self._max_bytes // (1024 * 1024)

        return f"Файл больше {limit} МБ — загрузите фото меньшего размера."


@dataclass(frozen=True, slots=True)
class NormalizedImage:
    data: bytes
    extension: str
    content_type: str
    width: int
    height: int

    @property
    def size_bytes(self) -> int:
        return len(self.data)


def normalize_image(data: bytes, *, max_side: int, quality: int) -> NormalizedImage:
    if not data:
        raise UnsupportedImageError()

    try:
        with Image.open(io.BytesIO(data)) as opened:
            image = ImageOps.exif_transpose(opened)
            image.thumbnail((max_side, max_side))

            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGBA" if "A" in image.getbands() else "RGB")

            buffer = io.BytesIO()
            image.save(buffer, format="WEBP", quality=quality, method=4)

            width, height = image.size
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise UnsupportedImageError() from exc

    return NormalizedImage(
        data=buffer.getvalue(),
        extension="webp",
        content_type="image/webp",
        width=width,
        height=height,
    )
