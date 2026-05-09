async def test_balance_after_register_includes_welcome_bonus(client, registered_user):
    """Свежезарегистрированный пользователь получает welcome-бонус."""
    res = await client.get("/api/billing/balance", headers=registered_user["auth"])
    assert res.status_code == 200
    body = res.json()
    assert body["balance"] == 200.0
    assert body["loyalty_level"] == "Bronze"


async def test_balance_requires_auth(client):
    """Без токена /balance возвращает 401."""
    res = await client.get("/api/billing/balance")
    assert res.status_code == 401


async def test_user_cannot_self_refill(client, registered_user):
    """Эндпоинта самостоятельного refill больше нет, ответ 404."""
    res = await client.post(
        "/api/billing/refill", json={"amount": 100}, headers=registered_user["auth"]
    )
    assert res.status_code == 404
