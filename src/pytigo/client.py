from __future__ import annotations

from requests import Session

from .models import TigoAuth, TigoCSVTable, TigoSummary, TigoSystem, TigoSystemLayout, TigoUser
from .parsing import (
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

    def login(self) -> TigoAuth:
        response = self.session.get(
            f"{self.api_root}/users/login",
            auth=(self.username, self.password),
            timeout=self.timeout,
        )
        response.raise_for_status()
        self.auth = parse_login_response(response.json())
        return self.auth

    def logout(self) -> dict:
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
        response = self.session.get(
            f"{self.api_root}/users/{user_id}",
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return parse_user_response(response.json())

    def list_systems(self, *, page: int | None = None, limit: int | None = None, sort: str | None = None) -> list[TigoSystem]:
        params: dict[str, int | str] = {}
        if page is not None:
            params["page"] = page
        if limit is not None:
            params["limit"] = limit
        if sort is not None:
            params["sort"] = sort
        response = self.session.get(
            f"{self.api_root}/systems",
            headers=self._headers(),
            params=params or None,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return parse_systems_response(response.json())

    def get_system(self, system_id: int) -> TigoSystem:
        response = self.session.get(
            f"{self.api_root}/systems/view",
            headers=self._headers(),
            params={"id": system_id},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return parse_system_response(response.json())

    def get_layout(self, system_id: int) -> TigoSystemLayout:
        response = self.session.get(
            f"{self.api_root}/systems/layout",
            headers=self._headers(),
            params={"id": system_id},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return parse_layout_response(response.json())

    def get_objects(self, system_id: int):
        response = self.session.get(
            f"{self.api_root}/objects/system",
            headers=self._headers(),
            params={"system_id": system_id},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return parse_objects_response(response.json())

    def get_object_types(self):
        response = self.session.get(
            f"{self.api_root}/objects/types",
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return parse_object_types_response(response.json())

    def get_sources(self, system_id: int):
        response = self.session.get(
            f"{self.api_root}/sources/system",
            headers=self._headers(),
            params={"system_id": system_id},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return parse_sources_response(response.json())

    def get_summary(self, system_id: int) -> TigoSummary:
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
        level: str = "min",
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
        agg: str,
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
        response = self.session.get(
            f"{self.api_root}/data/combined",
            headers=self._headers(),
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return parse_csv_table(response.text)
