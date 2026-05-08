import streamlit as st

from frontend.services.api_client import api_client
from frontend.services.session import get_balance, get_profile, login, logout


def _render_login_form() -> None:
    st.sidebar.title("🔑 Вход в систему")
    auth_mode = st.sidebar.radio("Действие", ["Логин", "Регистрация"])

    with st.sidebar.form("auth_form"):
        username = st.text_input("Имя пользователя")
        password = st.text_input("Пароль", type="password")

        if auth_mode == "Регистрация":
            email = st.text_input("Email")
            if st.form_submit_button("Зарегистрироваться"):
                res = api_client.post(
                    "/auth/register",
                    json_data={"username": username, "email": email, "password": password},
                )
                if res.status_code == 201:
                    st.success("Успешно! Теперь войдите.")
                else:
                    st.error(f"Ошибка: {res.error or 'Неизвестная ошибка'}")
        else:
            if st.form_submit_button("Войти"):
                res = api_client.post(
                    "/auth/login",
                    data={"username": username, "password": password},
                )
                if res.ok and res.data and res.data.get("access_token"):
                    login(res.data["access_token"])
                    st.rerun()
                else:
                    st.error(res.error or "Неверные данные")


def _render_profile() -> None:
    st.sidebar.title("👤 Профиль")
    profile = get_profile()
    if profile:
        st.sidebar.markdown(f"**Пользователь:** {profile.get('username')}")
        st.sidebar.markdown(f"**Email:** {profile.get('email')}")

    balance = get_balance()
    if balance:
        st.sidebar.markdown(f"**Баланс:** {balance.get('balance')} кр.")
        st.sidebar.markdown(f"**Уровень:** {balance.get('loyalty_level')}")

    st.sidebar.markdown("---")
    if st.sidebar.button("Выйти"):
        logout()
        st.rerun()


def render_sidebar_auth() -> None:
    """Сайдбар: либо форма входа, либо профиль с балансом."""
    if st.session_state.get("token"):
        _render_profile()
    else:
        _render_login_form()
