import pandas as pd
import streamlit as st

from frontend.services.api_client import api_client
from frontend.services.session import invalidate_balance

_LEVEL_BY_ID = {1: "Bronze", 2: "Silver", 3: "Gold"}


def render_admin_panel() -> None:
    """Админ-панель: список пользователей и принудительное пополнение баланса."""
    st.subheader("🛠 Админ-панель")

    msg = st.session_state.pop("admin_refill_msg", None)
    if msg:
        msg_type, text = msg
        (st.success if msg_type == "success" else st.error)(text)

    res = api_client.get("/admin/users")
    if not res.ok:
        st.error(res.error or "Не удалось загрузить список пользователей.")
        return

    users = res.data or []
    if not users:
        st.info("Нет пользователей.")
        return

    df = pd.DataFrame(users)
    df["Уровень"] = df["loyalty_level_id"].map(_LEVEL_BY_ID).fillna("-")
    df = df.rename(
        columns={
            "id": "ID",
            "username": "Логин",
            "email": "Email",
            "role": "Роль",
            "balance": "Баланс",
        }
    )
    st.dataframe(
        df[["ID", "Логин", "Email", "Роль", "Баланс", "Уровень"]],
        width="stretch",
        hide_index=True,
    )

    st.markdown("**Пополнить баланс пользователю**")
    options = {f"{u['username']} (id={u['id']})": u["id"] for u in users}
    with st.form("admin_refill_form"):
        label = st.selectbox("Пользователь", list(options.keys()))
        amount = st.number_input("Сумма", min_value=1.0, max_value=100000.0, value=100.0, step=10.0)
        if not st.form_submit_button("Пополнить"):
            return

        user_id = options[label]
        resp = api_client.post(f"/admin/users/{user_id}/refill", json_data={"amount": amount})
        if resp.ok:
            invalidate_balance()
            st.session_state.admin_refill_msg = (
                "success",
                f"Баланс пользователя {label} пополнен. "
                f"Новый баланс: {(resp.data or {}).get('new_balance')}",
            )
        else:
            st.session_state.admin_refill_msg = (
                "error",
                resp.error or f"Ошибка: {resp.status_code}",
            )
        st.rerun()
