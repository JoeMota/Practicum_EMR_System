from app.schemas.common import APIModel


class AccountUpdate(APIModel):
    full_name: str
    email: str
    university_id: str | None = None


class UserActivePatch(APIModel):
    is_active: bool


class UserActiveOut(APIModel):
    id: str
    is_active: bool


class DeleteAccount(APIModel):
    email: str