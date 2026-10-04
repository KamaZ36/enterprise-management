from myasnaya_derevnya.core.errors import NotFoundError


class RoleNotFound(NotFoundError): ...


class UserNotFound(NotFoundError): ...


class IncorrectCredentials(NotFoundError): ...
