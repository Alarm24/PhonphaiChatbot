import datetime

import jwt


def encode_token(
    *,
    user_id: str,
    username: str,
    role: str,
    staff_id: int | None,
    secret: str,
    algorithm: str,
    expires_hours: int,
) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "staff_id": staff_id,
        "iat": int(now.timestamp()),
        "exp": int((now + datetime.timedelta(hours=expires_hours)).timestamp()),
    }
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_token(token: str, secret: str, algorithm: str) -> dict:
    return jwt.decode(token, secret, algorithms=[algorithm])
