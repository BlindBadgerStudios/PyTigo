from __future__ import annotations

import logging
from typing import Literal

from requests import Session

from .models import (
    TigoAlert,
    TigoAlertType,
    TigoAuth,
    TigoCSVTable,
    TigoObjectNode,
    TigoObjectType,
    TigoPage,
    TigoSource,
    TigoSummary,
    TigoSystem,
    TigoSystemLayout,
    TigoUser,
)
from .parsing import (
    parse_alert_types_response,
    parse_alerts_response,
    parse_csv_table,
    parse_layout_response,
    parse_login_response,
    parse_object_types_response,
    parse_objects_response,
    parse_sources_response,
    parse_summary_response,
    parse_system_response,
    parse_systems_response,
    parse_user_response,
)

logger = logging.getLogger(__name__)


class TigoClient:
    api_root = "https://api2.tigoenergy.com/api/v3"

    def __init__(
        self,
        username: str,
        password: str,
        *,
        session: Session | None = None,
        timeout: int = 30,
    ) -> None:
        self.username = username
        self.password = password
        self.timeout = timeout
        self.session = session or Session()
        self.auth: TigoAuth | None = None

    def _headers(self) -> dict[str, str]:
        if not self.auth:
            raise ValueError("Not authenticated. Call login() first.")
        return {"Authorization": f"Bearer {self.auth.auth_token}"}

    def __enter__(self) -> TigoClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.session.close()

    def login(self) -> TigoAuth:
        logger.debug("GET /users/login user=%s", self.username)
        response = self.session.get(
            f"{self.api_root}/users/login",
            auth=(self.username, self.password),
            timeout=self.timeout,
        )
        response.raise_for_status()
        self.auth = parse_login_response(response.json())
        logger.debug("login successful user_id=%s", self.auth.user_id)
        return self.auth

    def logout(self) -> dict:
        logger.debug("GET /users/logout")
        response = self.session.get(
            f"{self.api_root}/users/logout",
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        self.auth = None
        return payload

    def get_current_user(self, user_id: int | None = None) -> TigoUser:
        if user_id is None:
            if not self.auth:
                raise ValueError("user_id is required before login; after login it defaults to auth.user_id")
            user_id = self.auth.user_id
        logger.debug("GET /users/%s", user_id)
        response = self.session.get(
            f"{self.api_root}/users/{user_id}",
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return parse_user_response(response.json())

    def list_systems(self, *, page: int | None = None, limit: int | None = None, sort: str | None = None) -> TigoPage[TigoSystem]:
        params: dict[str, int | str] = {}
        if page is not None:
            params["page"] = page
        if limit is not None:
            params["limit"] = limit
        if sort is not None:
            params["sort"] = sort
        logger.debug("GET /systems params=%s", params)
        response = self.session.get(
            f"{self.api_root}/systems",
            headers=self._headers(),
            params=params or None,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return parse_systems_response(response.json())

    def get_system(self, system_id: int, *, include: list[str] | None = None) -> TigoSystem:
        params: dict[str, str | int] = {"id": system_id}
        if include:
            params["include"] = ",".join(include)
        logger.debug("GET /systems/view system_id=%s", system_id)
        response = self.session.get(
            f"{self.api_root}/systems/view",
            headers=self._headers(),
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return parse_system_response(response.json())

    def get_layout(self, system_id: int) -> TigoSystemLayout:
        logger.debug("GET /systems/layout system_id=%s", system_id)
        response = self.session.get(
            f"{self.api_root}/systems/layout",
            headers=self._headers(),
            params={"id": system_id},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return parse_layout_response(response.json())

    def get_objects(self, system_id: int) -> list[TigoObjectNode]:
        logger.debug("GET /objects/system system_id=%s", system_id)
        response = self.session.get(
            f"{self.api_root}/objects/system",
            headers=self._headers(),
            params={"system_id": system_id},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return parse_objects_response(response.json())

    def get_object_types(self) -> list[TigoObjectType]:
        logger.debug("GET /objects/types")
        response = self.session.get(
            f"{self.api_root}/objects/types",
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return parse_object_types_response(response.json())

    def get_sources(self, system_id: int) -> list[TigoSource]:
        logger.debug("GET /sources/system system_id=%s", system_id)
        response = self.session.get(
            f"{self.api_root}/sources/system",
            headers=self._headers(),
            params={"system_id": system_id},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return parse_sources_response(response.json())

    def get_summary(self, system_id: int) -> TigoSummary:
        logger.debug("GET /data/summary system_id=%s", system_id)
        response = self.session.get(
            f"{self.api_root}/data/summary",
            headers=self._headers(),
            params={"system_id": system_id},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return parse_summary_response(response.json())

    def get_aggregate(
        self,
        system_id: int,
        *,
        start: str,
        end: str,
        level: Literal["min", "hour", "day"] = "min",
        param: str = "Pin",
        object_ids: list[int] | None = None,
        header: str | None = None,
        sensors: bool | None = None,
    ) -> TigoCSVTable:
        params: dict[str, str] = {
            "system_id": str(system_id),
            "start": start,
            "end": end,
            "level": level,
            "param": param,
        }
        if object_ids:
            params["object_ids"] = ",".join(str(i) for i in object_ids)
        if header:
            params["header"] = header
        if sensors is not None:
            params["sensors"] = "true" if sensors else "false"
        logger.debug("GET /data/aggregate system_id=%s param=%s level=%s", system_id, param, level)
        response = self.session.get(
            f"{self.api_root}/data/aggregate",
            headers=self._headers(),
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return parse_csv_table(response.text)

    def get_combined(
        self,
        system_id: int,
        *,
        start: str,
        end: str,
        agg: Literal["min", "hour", "day"],
        object_ids: list[int] | None = None,
    ) -> TigoCSVTable:
        params: dict[str, str] = {
            "system_id": str(system_id),
            "start": start,
            "end": end,
            "agg": agg,
        }
        if object_ids:
            params["object_ids"] = ",".join(str(i) for i in object_ids)
        logger.debug("GET /data/combined system_id=%s agg=%s", system_id, agg)
        response = self.session.get(
            f"{self.api_root}/data/combined",
            headers=self._headers(),
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return parse_csv_table(response.text)

    def get_alerts(
        self,
        system_id: int,
        *,
        language: str | None = None,
        start_added: str | None = None,
        end_added: str | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> TigoPage[TigoAlert]:
        params: dict[str, str | int] = {"system_id": system_id}
        if language:
            params["language"] = language
        if start_added:
            params["start_added"] = start_added
        if end_added:
            params["end_added"] = end_added
        if page is not None:
            params["page"] = page
        if limit is not None:
            params["limit"] = limit
        logger.debug("GET /alerts/system system_id=%s", system_id)
        response = self.session.get(
            f"{self.api_root}/alerts/system",
            headers=self._headers(),
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return parse_alerts_response(response.json())

    def get_alert_types(self, *, language: str | None = None) -> list[TigoAlertType]:
        params: dict[str, str] = {}
        if language:
            params["language"] = language
        logger.debug("GET /alerts/types")
        response = self.session.get(
            f"{self.api_root}/alerts/types",
            headers=self._headers(),
            params=params or None,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return parse_alert_types_response(response.json())
