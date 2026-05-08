import streamlit as st
from streamlit_cookies_controller import CookieController

from frontend.core.config import LOYALTY_TIERS, TIER_BY_NAME, LoyaltyTier
from frontend.services.api_client import api_client

COOKIE_NAME = "auth_token"
COOKIE_TTL_SECONDS = 7 * 24 * 3600

_USER_STATE_KEYS: tuple[str, ...] = (
    "model_choice",
    "last_result",
    "current_challenge",
    "gamification_msg",
    "_profile",
    "_balance",
)


_cookie_controller = CookieController()


def restore_token_from_cookie() -> None:
    """Загружает токен из cookie в session_state."""
    if st.session_state.get("token"):
        return
    cookie_token = _cookie_controller.get(COOKIE_NAME)
    if cookie_token:
        st.session_state.token = cookie_token


def login(token: str) -> None:
    """Сохраняет токен в cookie и session_state."""
    _cookie_controller.set(COOKIE_NAME, token, max_age=COOKIE_TTL_SECONDS)
    st.session_state.token = token
    _clear_user_state()


def logout() -> None:
    """Удаляет токен и состояние пользователя."""
    try:
        _cookie_controller.remove(COOKIE_NAME)
    except KeyError:
        pass
    st.session_state.token = None
    _clear_user_state()


def _clear_user_state() -> None:
    for key in _USER_STATE_KEYS:
        st.session_state.pop(key, None)


def get_profile(force_refresh: bool = False) -> dict | None:
    """Кеш профиля - один HTTP-запрос на rerun."""
    if not force_refresh and "_profile" in st.session_state:
        return st.session_state._profile
    res = api_client.get("/auth/me")
    if res.status_code == 401:
        logout()
        return None
    if res.ok:
        st.session_state._profile = res.data
        return res.data
    return None


def get_balance(force_refresh: bool = False) -> dict | None:
    """Кеш баланса - один HTTP-запрос на rerun."""
    if not force_refresh and "_balance" in st.session_state:
        return st.session_state._balance
    res = api_client.get("/billing/balance")
    if res.status_code == 401:
        logout()
        return None
    if res.ok:
        st.session_state._balance = res.data
        return res.data
    return None


def invalidate_balance() -> None:
    """Удаляет кэш баланса."""
    st.session_state.pop("_balance", None)


def current_tier() -> LoyaltyTier:
    """Текущий уровень пользователя или Bronze по умолчанию."""
    bal = get_balance()
    name = (bal or {}).get("loyalty_level", "Bronze")
    return TIER_BY_NAME.get(name, LOYALTY_TIERS[0])
