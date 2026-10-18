import logging
from dataclasses import dataclass
from uuid import uuid7

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.core.media.images import ImageTooLargeError, normalize_image
from myasnaya_derevnya.core.media.storage import MediaStorage
from myasnaya_derevnya.core.settings.media import MediaSettings
from myasnaya_derevnya.modules.catalog.domain.permissions import UPLOAD_IMAGE
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI

FOLDER = "menu"

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class UploadImageCommand:
    data: bytes


@dataclass(frozen=True, slots=True)
class UploadedImage:
    url: str
    width: int
    height: int
    size_bytes: int


class UploadImageInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        staff_api: StaffAPI,
        media_storage: MediaStorage,
        media_settings: MediaSettings,
    ) -> None:
        self._identity_provider = identity_provider
        self._staff_api = staff_api
        self._media_storage = media_storage
        self._media_settings = media_settings

    async def __call__(self, command: UploadImageCommand) -> UploadedImage:
        current_user_id = await self._identity_provider.get_current_user_id()

        allowed = await self._staff_api.can_anywhere(
            user_id=current_user_id, permission=UPLOAD_IMAGE
        )
        if not allowed:
            raise ForbiddenError()

        if len(command.data) > self._media_settings.media_max_bytes:
            raise ImageTooLargeError(self._media_settings.media_max_bytes)

        image = normalize_image(
            command.data,
            max_side=self._media_settings.media_max_side,
            quality=self._media_settings.media_webp_quality,
        )

        url = await self._media_storage.save(
            folder=FOLDER,
            filename=f"{uuid7().hex}.{image.extension}",
            data=image.data,
        )

        logger.info(
            "Загружено изображение",
            extra={"url": url, "size_bytes": image.size_bytes},
        )

        return UploadedImage(
            url=url,
            width=image.width,
            height=image.height,
            size_bytes=image.size_bytes,
        )
