from uuid import UUID, uuid4


class Role:
    def __init__(
        self, id: UUID, name: str, code: str, grants_all: bool, permissions: set[str]
    ) -> None:
        self._id = id
        self._name = name
        self._code = code
        self._grants_all = grants_all
        self._permissions = permissions

    @classmethod
    def create(
        cls, name: str, code: str, grants_all: bool, permissions: set[str]
    ) -> Role:
        name = name.strip()
        return Role(
            id=uuid4(),
            name=name,
            code=code,
            grants_all=grants_all,
            permissions=permissions,
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def code(self) -> str:
        return self._code

    @property
    def grants_all(self) -> bool:
        return self._grants_all

    @property
    def permissions(self) -> frozenset[str]:
        return frozenset(self._permissions)

    def rename(self, name: str) -> None:
        name = name.strip()
        if not name:
            raise InvalidRole
        self._name = name

    def set_permissions(self, codes: set[str]) -> None:
        if self._grants_all:
            raise SystemRoleProtected  # у роли "всё" список прав не редактируется
        self._permissions = set(codes)

    def ensure_deletable(self) -> None:
        if self._is_system:
            raise SystemRoleProtected
