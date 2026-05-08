import streamlit as st

from frontend.services.api_client import api_client
from frontend.services.session import invalidate_balance

_DIFFICULTY_OPTIONS = ["easy", "medium", "hard"]


def render_gamification() -> None:
    """Блок заработка кредитов через математические задачи."""
    st.subheader("🧠 Заработать кредиты")

    msg = st.session_state.pop("gamification_msg", None)
    if msg:
        msg_type, text = msg
        (st.success if msg_type == "success" else st.error)(text)

    diff = st.selectbox("Выберите сложность", _DIFFICULTY_OPTIONS)

    if st.button("Получить задачу"):
        res = api_client.post("/gamification/generate_challenge", json_data={"difficulty": diff})
        if res.ok:
            st.session_state.current_challenge = res.data
            st.rerun()
        else:
            st.error(res.error or "Не удалось получить задачу.")

    challenge = st.session_state.get("current_challenge")
    if not challenge:
        return

    st.info(f"**Задача:** {challenge['question']}  \n**Награда:** {challenge['reward']} кр.")
    answer = st.text_input("Ваш ответ:")

    if not st.button("Отправить ответ"):
        return

    sol = api_client.post(
        "/gamification/solve",
        json_data={"challenge_id": challenge["challenge_id"], "answer": answer},
    )

    if sol.ok and sol.data and sol.data.get("correct"):
        st.session_state.gamification_msg = ("success", sol.data["message"])
        st.session_state.pop("current_challenge", None)
        invalidate_balance()
    elif sol.ok:
        st.session_state.gamification_msg = (
            "error",
            (sol.data or {}).get("message", "Неверный ответ. Попробуйте еще раз."),
        )
    elif sol.status_code in (400, 409):
        st.session_state.gamification_msg = (
            "error",
            sol.error or "Задача не найдена или время вышло (5 минут).",
        )
        st.session_state.pop("current_challenge", None)
    else:
        st.session_state.gamification_msg = (
            "error",
            sol.error or "Не удалось проверить ответ.",
        )
    st.rerun()
