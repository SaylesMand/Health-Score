from dataclasses import dataclass
from typing import Any

import requests
import streamlit as st

from frontend.core.config import settings


@dataclass
class APIResponse:
    """Унифицированный ответ из APIClient. status_code=0 - сетевая/транспортная ошибка."""

    status_code: int
    data: Any = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        """Проверка статуса ответа."""
        return 200 <= self.status_code < 300

    @staticmethod
    def from_requests(resp: requests.Response) -> "APIResponse":
        """Преобразует объект ответа requests в APIResponse."""
        try:
            payload = resp.json() if resp.content else None
        except ValueError:
            payload = None

        if 200 <= resp.status_code < 300:
            return APIResponse(status_code=resp.status_code, data=payload)

        return APIResponse(
            status_code=resp.status_code,
            data=payload,
            error=_extract_error(payload, resp.status_code),
        )


def _extract_error(payload: Any, status_code: int) -> str:
    """Достаёт человекочитаемое сообщение из ответа FastAPI."""
    if not isinstance(payload, dict):
        return f"HTTP {status_code}"
    detail = payload.get("detail")
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list) and detail:
        msgs = [
            f"{'.'.join(str(x) for x in item.get('loc', [])[1:]) or 'field'}: {item.get('msg', '')}"
            for item in detail
            if isinstance(item, dict)
        ]
        return "; ".join(msgs) or f"HTTP {status_code}"
    return f"HTTP {status_code}"


class APIClient:
    """Клиент для общения с Health Score API."""

    def __init__(self):
        self.base_url = settings.API_URL
        self.timeout = settings.REQUEST_TIMEOUT

    def _headers(self) -> dict[str, str]:
        token = st.session_state.get("token")
        return {"Authorization": f"Bearer {token}"} if token else {}

    def _request(self, method: str, endpoint: str, **kwargs) -> APIResponse:
        url = f"{self.base_url}{endpoint}"
        try:
            resp = requests.request(
                method, url, headers=self._headers(), timeout=self.timeout, **kwargs
            )
        except requests.ConnectionError:
            return APIResponse(status_code=0, error="Сервер недоступен.")
        except requests.Timeout:
            return APIResponse(status_code=0, error="Превышено время ожидания.")
        except requests.RequestException as exc:
            return APIResponse(status_code=0, error=f"Сетевая ошибка: {exc}")
        return APIResponse.from_requests(resp)

    def get(self, endpoint: str) -> APIResponse:
        """GET-запрос к API."""
        return self._request("GET", endpoint)

    def post(
        self,
        endpoint: str,
        json_data: dict | None = None,
        data: dict | None = None,
    ) -> APIResponse:
        """POST-запрос к API."""
        return self._request("POST", endpoint, json=json_data, data=data)


api_client = APIClient()
