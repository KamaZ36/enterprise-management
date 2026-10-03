class AppError(Exception):
    pass


class UnauthorizedError(AppError): ...


class ForbiddenError(AppError): ...


class ValidationError(AppError): ...


class NotFoundError(AppError): ...
