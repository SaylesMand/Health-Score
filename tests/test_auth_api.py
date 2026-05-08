async def test_register_creates_user(client):
    """Регистрация возвращает 201 и базовые данные."""
    res = await client.post(
        "/api/auth/register",
        json={"username": "bob", "email": "bob@example.com", "password": "secret123"},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["username"] == "bob"
    assert body["email"] == "bob@example.com"
    assert body["role"] == "user"
    assert body["balance"] == 0.0


async def test_register_rejects_duplicate_email(client):
    """Повторная регистрация с тем же email возвращает 400."""
    payload = {"username": "u1", "email": "dup@example.com", "password": "secret123"}
    await client.post("/api/auth/register", json=payload)
    res = await client.post(
        "/api/auth/register",
        json={"username": "u2", "email": "dup@example.com", "password": "secret123"},
    )
    assert res.status_code == 400


async def test_register_rejects_duplicate_username(client):
    """Повторная регистрация с тем же username возвращает 400."""
    payload = {"username": "samename", "email": "a@example.com", "password": "secret123"}
    await client.post("/api/auth/register", json=payload)
    res = await client.post(
        "/api/auth/register",
        json={"username": "samename", "email": "b@example.com", "password": "secret123"},
    )
    assert res.status_code == 400


async def test_login_success(client, registered_user):
    """Логин валидным пользователем возвращает access_token."""
    res = await client.post(
        "/api/auth/login",
        data={"username": "alice", "password": "secret123"},
    )
    assert res.status_code == 200
    assert res.json()["access_token"]


async def test_login_wrong_password(client, registered_user):
    """Неверный пароль возвращает 401."""
    res = await client.post(
        "/api/auth/login",
        data={"username": "alice", "password": "wrong"},
    )
    assert res.status_code == 401


async def test_me_returns_profile(client, registered_user):
    """/auth/me возвращает профиль авторизованного пользователя."""
    res = await client.get("/api/auth/me", headers=registered_user["auth"])
    assert res.status_code == 200
    assert res.json()["username"] == "alice"


async def test_me_without_token_unauthorized(client):
    """/auth/me без токена возвращает 401."""
    res = await client.get("/api/auth/me")
    assert res.status_code == 401


async def test_me_with_invalid_token(client):
    """Невалидный токен возвращает 401."""
    res = await client.get("/api/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert res.status_code == 401
