async def test_balance_returns_zero_after_register(client, registered_user):
    """Свежезарегистрированный пользователь имеет нулевой баланс."""
    res = await client.get("/api/billing/balance", headers=registered_user["auth"])
    assert res.status_code == 200
    body = res.json()
    assert body["balance"] == 0.0
    assert body["loyalty_level"] == "Bronze"


async def test_refill_increases_balance(client, registered_user):
    """Refill пополняет баланс и возвращает новое значение."""
    res = await client.post(
        "/api/billing/refill", json={"amount": 250}, headers=registered_user["auth"]
    )
    assert res.status_code == 200
    assert res.json()["new_balance"] == 250.0

    res = await client.get("/api/billing/balance", headers=registered_user["auth"])
    assert res.json()["balance"] == 250.0


async def test_refill_rejects_negative_amount(client, registered_user):
    """Отрицательная сумма отклоняется валидатором."""
    res = await client.post(
        "/api/billing/refill", json={"amount": -10}, headers=registered_user["auth"]
    )
    assert res.status_code == 422


async def test_refill_requires_auth(client):
    """Без токена refill возвращает 401."""
    res = await client.post("/api/billing/refill", json={"amount": 100})
    assert res.status_code == 401
