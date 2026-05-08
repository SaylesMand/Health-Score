from datetime import timedelta

from jose import jwt

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password


def test_password_hash_roundtrip():
    """Хеш и проверка пароля совпадают."""
    pwd = "supersecret"
    hashed = get_password_hash(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed)


def test_password_verify_fails_on_wrong_password():
    """Неверный пароль не проходит проверку."""
    hashed = get_password_hash("right")
    assert not verify_password("wrong", hashed)


def test_create_access_token_contains_sub_and_exp():
    """Токен содержит sub и exp."""
    token = create_access_token({"sub": "alice"}, expires_delta=timedelta(minutes=5))
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload["sub"] == "alice"
    assert "exp" in payload
