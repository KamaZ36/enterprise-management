from myasnaya_derevnya.core.errors import DomainError


class VeterinaryDomainError(DomainError):
    def __str__(self) -> str:
        return "Ошибка ветеринарного документа"


class EmptyVeterinaryDocumentError(VeterinaryDomainError):
    def __str__(self) -> str:
        return (
            "Укажите хотя бы один идентификатор ВСД: номер, GUID, "
            "номер партии или GUID позиции"
        )
