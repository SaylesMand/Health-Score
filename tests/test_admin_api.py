async def test_user_cannot_list_users(client, registered_user):
    """Обычный пользователь получает 403 на /admin/users."""
    res = await client.get("/api/admin/users", headers=registered_user["auth"])
    assert res.status_code == 403


async def test_admin_can_list_users(client, registered_user, admin_user):
    """Админ видит всех пользователей."""
    res = await client.get("/api/admin/users", headers=admin_user["auth"])
    assert res.status_code == 200
    usernames = {u["username"] for u in res.json()}
    assert "alice" in usernames
    assert "root" in usernames


async def test_admin_refill_increases_target_balance(client, registered_user, admin_user):
    """Админ может пополнить баланс другого пользователя поверх welcome-бонуса."""
    target_id = registered_user["user"]["id"]
    res = await client.post(
        f"/api/admin/users/{target_id}/refill",
        json={"amount": 333},
        headers=admin_user["auth"],
    )
    assert res.status_code == 200
    assert res.json()["new_balance"] == 533.0


async def test_admin_refill_404_on_unknown_user(client, admin_user):
    """Refill несуществующего пользователя возвращает 404."""
    res = await client.post(
        "/api/admin/users/999999/refill",
        json={"amount": 100},
        headers=admin_user["auth"],
    )
    assert res.status_code == 404


async def test_user_cannot_admin_refill(client, registered_user):
    """Обычный пользователь не может вызвать админский refill."""
    res = await client.post(
        f"/api/admin/users/{registered_user['user']['id']}/refill",
        json={"amount": 50},
        headers=registered_user["auth"],
    )
    assert res.status_code == 403
