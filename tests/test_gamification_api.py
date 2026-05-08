async def _generate(client, auth, difficulty: str = "easy") -> dict:
    """Создаёт challenge и возвращает его данные."""
    res = await client.post(
        "/api/gamification/generate_challenge",
        json={"difficulty": difficulty},
        headers=auth,
    )
    assert res.status_code == 200
    return res.json()


async def _correct_answer_for(client, auth, fake_redis, challenge_id: str) -> str:
    """Достаёт правильный ответ напрямую из fake-redis."""
    user_id = (await client.get("/api/auth/me", headers=auth)).json()["id"]
    raw = await fake_redis.get(f"challenge:{user_id}:{challenge_id}")
    return raw.split("|", 1)[0]


async def test_generate_challenge_returns_question_and_reward(client, registered_user):
    """Generate возвращает задачу с непустым question и положительным reward."""
    body = await _generate(client, registered_user["auth"], "medium")
    assert body["question"]
    assert body["reward"] > 0


async def test_solve_correct_answer_credits_user(client, registered_user, _fake_redis):
    """Правильный ответ начисляет вознаграждение в баланс."""
    challenge = await _generate(client, registered_user["auth"], "easy")
    answer = await _correct_answer_for(
        client, registered_user["auth"], _fake_redis, challenge["challenge_id"]
    )

    res = await client.post(
        "/api/gamification/solve",
        json={"challenge_id": challenge["challenge_id"], "answer": answer},
        headers=registered_user["auth"],
    )
    assert res.status_code == 200
    body = res.json()
    assert body["correct"] is True
    assert body["reward"] == challenge["reward"]

    bal = await client.get("/api/billing/balance", headers=registered_user["auth"])
    assert bal.json()["balance"] == 200.0 + challenge["reward"]


async def test_solve_wrong_answer_returns_correct_false(client, registered_user):
    """Неверный ответ возвращает correct=False и не списывает попытку."""
    challenge = await _generate(client, registered_user["auth"])
    res = await client.post(
        "/api/gamification/solve",
        json={"challenge_id": challenge["challenge_id"], "answer": "definitely_wrong"},
        headers=registered_user["auth"],
    )
    assert res.status_code == 200
    assert res.json()["correct"] is False


async def test_solve_unknown_challenge_returns_400(client, registered_user):
    """Несуществующий challenge_id возвращает 400."""
    res = await client.post(
        "/api/gamification/solve",
        json={"challenge_id": "00000000-0000-0000-0000-000000000000", "answer": "1"},
        headers=registered_user["auth"],
    )
    assert res.status_code == 400


async def test_rate_limit_after_20_challenges(client, registered_user):
    """После 20 challenge'ей в час возвращается 429."""
    for _ in range(20):
        res = await client.post(
            "/api/gamification/generate_challenge",
            json={"difficulty": "easy"},
            headers=registered_user["auth"],
        )
        assert res.status_code == 200

    res = await client.post(
        "/api/gamification/generate_challenge",
        json={"difficulty": "easy"},
        headers=registered_user["auth"],
    )
    assert res.status_code == 429
