class AppError(Exception):
    pass


class UnauthorizedError(AppError): ...


class ForbiddenError(AppError): ...


class NotFoundError(AppError): ...
