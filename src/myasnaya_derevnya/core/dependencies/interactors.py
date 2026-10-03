from dishka import Provider, Scope, provide

from myasnaya_derevnya.modules.auth.application.interactors.login.password import (
    LoginByPasswordInteractor,
)


class InteractorDepProvider(Provider):
    scope = Scope.REQUEST

    # MODULE AUTH
    login_by_password_interactor = provide(LoginByPasswordInteractor)
