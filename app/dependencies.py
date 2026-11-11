import logging

from datetime import datetime

from fastapi import (
    Depends,
    HTTPException,
    status
)

from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials
)

from jose import jwt, JWTError

from sqlalchemy.orm import Session

from database import get_db

from models.users import User
from models.live_users import LiveUserSession


logger = logging.getLogger(__name__)


SECRET_KEY = "velora-super-secret-key-change-this"

ALGORITHM = "HS256"


bearer_scheme = HTTPBearer(
    auto_error=False
)


def get_user_id_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(
        bearer_scheme
    ),
    db: Session = Depends(get_db),
) -> int:

    if credentials is None:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token is missing",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    try:

        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        subject = payload.get("sub")

        if subject is None:

            raise HTTPException(
                status_code=401,
                detail="Token does not contain a user ID",
            )

        user_id = int(subject)

        session_id = payload.get(
            "session_id"
        )

    except HTTPException:

        raise

    except (
        JWTError,
        ValueError,
        TypeError
    ) as exc:

        logger.warning(
            "JWT validation failed: %s: %s",
            type(exc).__name__,
            str(exc),
        )

        raise HTTPException(
            status_code=401,
            detail="Invalid or expired authentication token",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    user = db.query(
        User
    ).filter(
        User.id == user_id
    ).first()

    if not user:

        raise HTTPException(
            status_code=401,
            detail="User associated with token was not found",
        )

    # -----------------------------------------------------
    # Update live session activity
    # -----------------------------------------------------

    if session_id:

        live_session = db.query(
            LiveUserSession
        ).filter(
            LiveUserSession.session_id == session_id,
            LiveUserSession.user_id == user_id
        ).first()

        if live_session:

            live_session.last_activity_at = datetime.utcnow()

            live_session.is_online = True

            live_session.logout_at = None

            db.commit()

    return user_id