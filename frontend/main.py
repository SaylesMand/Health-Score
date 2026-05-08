import streamlit as st

from frontend.services.session import restore_token_from_cookie
from frontend.ui.auth import render_sidebar_auth
from frontend.ui.billing import render_balance
from frontend.ui.gamification import render_gamification
from frontend.ui.predict import render_history, render_predict_form

st.set_page_config(page_title="Health Score UI", page_icon="🩺", layout="centered")

restore_token_from_cookie()


def main() -> None:
    """Главная функция отрисовки приложения."""
    st.title("Система анализа здоровья")
    st.markdown(
        "Оценка риска сердечно-сосудистых заболеваний с помощью ML. "
        "Повышайте лояльность, решайте задачи и открывайте доступ к более точным алгоритмам."
    )

    render_sidebar_auth()

    if st.session_state.get("token"):
        render_balance()
        st.divider()
        render_history()
        st.divider()
        render_predict_form()
        st.divider()
        render_gamification()
    else:
        st.info("👈 Пожалуйста, зарегистрируйтесь или войдите через боковое меню.")


if __name__ == "__main__":
    main()
