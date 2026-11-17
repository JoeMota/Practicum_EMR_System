import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import decode_access_payload
from app.db.session import get_db
from app.models.user import User
from app.services.auth import get_user_by_id, is_usable, permission_codes

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user_allow_password_change(
    db: DbSession, token: Annotated[str, Depends(oauth2_scheme)]
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_payload(token)
    if payload is None:
        raise unauthorized
    sub = payload.get("sub")
    if not isinstance(sub, str):
        raise unauthorized
    try:
        user_id = uuid.UUID(sub)
    except ValueError:
        raise unauthorized
    user = await get_user_by_id(db, user_id)
    if user is None or not is_usable(user):
        raise unauthorized
    # Touch activity so /auth/refresh can enforce idle logout (SEC-03).
    user.last_activity_at = datetime.now(timezone.utc)
    # ADM-05: the access token's role claim is the session acting role for this request.
    token_role = payload.get("role")
    if isinstance(token_role, str) and token_role:
        user.acting_role = token_role
    return user


async def get_current_user(
    user: Annotated[User, Depends(get_current_user_allow_password_change)],
) -> User:
    if user.must_change_password:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Password change required")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_permission(code: str):
    async def checker(user: CurrentUser) -> User:
        if code not in permission_codes(user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Missing permission: {code}")
        return user

    return checker
