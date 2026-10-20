from app.schemas.common import APIModel


class UserActivePatch(APIModel):
    is_active: bool


class UserActiveOut(APIModel):
    id: str
    is_active: bool