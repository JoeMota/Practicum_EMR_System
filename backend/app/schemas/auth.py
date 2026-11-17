from pydantic import Field

from app.schemas.clinical import PublicUser
from app.schemas.common import APIModel


class Token(APIModel):
    access_token: str = Field(serialization_alias="access_token")
    refresh_token: str = Field(serialization_alias="refresh_token")
    token_type: str = Field(default="bearer", serialization_alias="token_type")
    must_change_password: bool
    user: PublicUser


class RefreshRequest(APIModel):
    refresh_token: str = Field(min_length=20, max_length=200)


class ChangePasswordRequest(APIModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class ActingRoleRequest(APIModel):
    role: str = Field(min_length=2, max_length=40)
