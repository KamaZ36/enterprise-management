from myasnaya_derevnya.core.errors import ValidationError


class InvalidReportPeriodError(ValidationError):
    def __str__(self) -> str:
        return "Дата начала не может быть позже даты окончания."
