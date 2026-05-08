import time

import pandas as pd
import streamlit as st

from frontend.core.config import LOYALTY_TIERS, TIER_BY_MODEL, settings
from frontend.services.api_client import api_client
from frontend.services.session import current_tier, invalidate_balance

_STATUS_COLOR = {"completed": "green", "pending": "orange", "failed": "red"}


def render_history() -> None:
    """История прогнозов пользователя."""
    st.subheader("📜 История прогнозов")
    if st.button("🔄 Обновить статус прогнозов"):
        st.rerun()

    res = api_client.get("/predict/history")
    if not res.ok:
        st.error(res.error or "Не удалось загрузить историю прогнозов.")
        return

    history = res.data or []
    if not history:
        st.info("У вас еще нет прогнозов. Сделайте первый прогноз ниже!")
        return

    df = pd.DataFrame(history)
    df["№"] = range(1, len(df) + 1)
    df["Вероятность, %"] = df["probability"].apply(lambda x: x * 100 if pd.notnull(x) else None)
    df = df.rename(columns={"status": "Статус"})

    styled = df[["№", "Вероятность, %", "Статус"]].style.map(
        lambda v: f"color: {_STATUS_COLOR.get(v, 'gray')}", subset=["Статус"]
    )

    st.dataframe(
        styled,
        width="stretch",
        hide_index=True,
        column_config={
            "№": st.column_config.NumberColumn("№", alignment="right"),
            "Вероятность, %": st.column_config.NumberColumn(
                "Вероятность, %", format="%.2f %%", alignment="right"
            ),
            "Статус": st.column_config.TextColumn("Статус", alignment="center"),
        },
    )


def _render_model_picker(user_rank: int) -> None:
    """Выбор ML-модели на основе текущего уровня лояльности."""
    if "model_choice" not in st.session_state:
        st.session_state.model_choice = "bronze"

    chosen_tier = TIER_BY_MODEL.get(st.session_state.model_choice)
    if chosen_tier and chosen_tier.rank > user_rank:
        st.session_state.model_choice = "bronze"

    st.markdown("**Выбор ML-модели:**")
    cols = st.columns(len(LOYALTY_TIERS))
    for col, tier in zip(cols, LOYALTY_TIERS, strict=False):
        is_selected = st.session_state.model_choice == tier.model_tier
        is_locked = tier.rank > user_rank
        with col:
            if is_locked:
                st.button(
                    f"🔒 {tier.model_label.split(' ', 1)[1]}",
                    help=f"Потратьте {tier.min_spend} кредитов, чтобы открыть уровень {tier.name}",
                    disabled=True,
                    use_container_width=True,
                )
            else:
                if st.button(
                    tier.model_label,
                    use_container_width=True,
                    type="primary" if is_selected else "secondary",
                ):
                    st.session_state.model_choice = tier.model_tier
                    st.rerun()
    st.caption(f"Выбрана модель: **{st.session_state.model_choice.upper()}**")


def _render_input_form() -> dict | None:
    """Форма биометрии. Возвращает payload или None, если submit не было."""
    with st.form("predict_form"):
        col1, col2 = st.columns(2)
        age = col1.number_input("Возраст (лет)", min_value=1, max_value=120, value=30)
        gender = col2.selectbox(
            "Пол", [1, 2], format_func=lambda x: "Женский" if x == 1 else "Мужской"
        )
        height = col1.number_input("Рост (см)", min_value=50, max_value=250, value=170)
        weight = col2.number_input("Вес (кг)", min_value=30.0, max_value=300.0, value=70.0)
        ap_hi = col1.number_input("Верхнее давление", min_value=40, max_value=250, value=120)
        ap_lo = col2.number_input("Нижнее давление", min_value=30, max_value=180, value=80)
        cholesterol = col1.selectbox(
            "Холестерин",
            [1, 2, 3],
            format_func=lambda x: {
                1: "1 - Норма",
                2: "2 - Выше нормы",
                3: "3 - Высокий",
            }[x],
        )
        gluc = col2.selectbox(
            "Глюкоза",
            [1, 2, 3],
            format_func=lambda x: {
                1: "1 - Норма",
                2: "2 - Выше нормы",
                3: "3 - Высокий",
            }[x],
        )
        smoke = col1.selectbox("Курение", [0, 1], format_func=lambda x: "Нет" if x == 0 else "Да")
        alco = col2.selectbox("Алкоголь", [0, 1], format_func=lambda x: "Нет" if x == 0 else "Да")
        active = st.selectbox("Спорт", [0, 1], format_func=lambda x: "Нет" if x == 0 else "Да")

        if not st.form_submit_button("Сделать прогноз"):
            return None

        return {
            "age": age,
            "gender": gender,
            "height": height,
            "weight": weight,
            "ap_hi": ap_hi,
            "ap_lo": ap_lo,
            "cholesterol": cholesterol,
            "gluc": gluc,
            "smoke": smoke,
            "alco": alco,
            "active": active,
            "model_type": st.session_state.model_choice,
        }


@st.fragment(run_every=settings.PREDICT_POLL_INTERVAL)
def _poll_pending_prediction() -> None:
    """Фоновый опрос статуса предсказания."""
    pending = st.session_state.get("pending_prediction")
    if not pending:
        return

    pred_id: int = pending["id"]
    deadline: float = pending["deadline"]

    if time.time() > deadline:
        st.warning(
            f"Ответ не получен за {settings.PREDICT_POLL_TIMEOUT} секунд. "
            "Проверьте 'Историю прогнозов'."
        )
        st.session_state.pop("pending_prediction", None)
        return

    res = api_client.get("/predict/history")
    if not res.ok:
        st.info("🧠 ML-модель анализирует данные...")
        return

    target = next((p for p in (res.data or []) if p["prediction_id"] == pred_id), None)
    if target is None or target["status"] == "pending":
        st.info("🧠 ML-модель анализирует данные...")
        return

    if target["status"] == "completed":
        st.session_state.last_result = (
            "Последний прогноз: Вероятность заболевания " f"= {target['probability'] * 100:.2f}%"
        )
    else:
        st.session_state.last_result = "Ошибка при вычислениях на сервере."

    st.session_state.pop("pending_prediction", None)
    invalidate_balance()
    st.rerun(scope="app")


def render_predict_form() -> None:
    """Форма биометрии + выбор модели + неблокирующий polling статуса."""
    st.subheader("🩺 Анализ риска")

    user_tier = current_tier()
    _render_model_picker(user_tier.rank)

    if last_result := st.session_state.get("last_result"):
        st.success(last_result)

    if "pending_prediction" in st.session_state:
        _poll_pending_prediction()

    payload = _render_input_form()
    if payload is None:
        return

    res = api_client.post("/predict/predict", json_data=payload)
    if res.status_code == 403:
        st.error(f"Доступ запрещен: {res.error}")
        return
    if res.status_code == 402:
        st.error("Недостаточно кредитов! Решите математические задачи.")
        return
    if res.status_code == 503:
        st.error("Сервис очередей временно недоступен. Попробуйте позже.")
        return
    if not res.ok:
        st.error(res.error or f"Ошибка сервера: {res.status_code}")
        return

    invalidate_balance()
    pred_id = (res.data or {}).get("prediction_id")
    if pred_id is not None:
        st.session_state.pending_prediction = {
            "id": pred_id,
            "deadline": time.time() + settings.PREDICT_POLL_TIMEOUT,
        }
        st.session_state.pop("last_result", None)
    st.rerun()
