import streamlit as st

from frontend.core.config import LOYALTY_TIERS
from frontend.services.session import get_balance


def _render_loyalty_help() -> None:
    with st.expander("Как повысить уровень лояльности?"):
        lines = [
            "Уровни пересчитываются автоматически раз в месяц на основе ваших трат. "
            "Чем больше предсказаний вы делаете, тем выше уровень и больше скидка!\n"
        ]
        for tier in LOYALTY_TIERS:
            if tier.min_spend == 0:
                lines.append(
                    f"* **{tier.name}:** Базовый уровень (скидка {tier.discount_percent}%). "
                    "Дается при регистрации."
                )
            else:
                lines.append(
                    f"* **{tier.name}:** Требуется потратить **{tier.min_spend} кредитов**. "
                    f"Дает скидку **{tier.discount_percent}%** на все предсказания."
                )
        st.markdown("\n".join(lines))


def render_balance() -> None:
    """Плашка с текущим балансом и уровнем."""
    balance = get_balance()
    if balance is None:
        st.error("Не удалось загрузить баланс.")
        return

    cols = st.columns(2)
    cols[0].metric("Баланс", f"{balance['balance']} кр.")
    cols[1].metric("Уровень лояльности", balance["loyalty_level"])
    _render_loyalty_help()
