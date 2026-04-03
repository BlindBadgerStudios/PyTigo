from __future__ import annotations

from datetime import date
from typing import Any

import requests

from .models import TigoOverview, TigoSystemInfo, TigoSystemTopology
from .parsing import (
    extract_csrf_token,
    extract_default_system_id,
    parse_daily_energy,
    parse_info_page,
    parse_overview_page,
    parse_range_data,
    parse_summary,
    parse_system_topology,
)


class TigoClient:
    portal_url = "https://ei.tigoenergy.com/"

    def __init__(
        self,
        email: str,
        password: str,
        *,
        session: requests.Session | None = None,
        timeout: int = 30,
    ) -> None:
        self.email = email
        self.password = password
        self.timeout = timeout
        self.session = session or requests.Session()
        self.default_system_id: int | None = None

    def login(self) -> int:
        login_page = self.session.get(self.portal_url, timeout=self.timeout)
        login_page.raise_for_status()
        csrf_token = extract_csrf_token(login_page.text)

        response = self.session.post(
            self.portal_url.rstrip("/") + "/site/login",
            data={
                "_csrf": csrf_token,
                "LoginFormModel[login]": self.email,
                "LoginFormModel[password]": self.password,
                "LoginFormModel[remember_me]": "1",
            },
            allow_redirects=True,
            timeout=self.timeout,
        )
        response.raise_for_status()
        self.default_system_id = extract_default_system_id(response.url)
        return self.default_system_id

    def _require_system_id(self, system_id: int | None = None) -> int:
        resolved = system_id or self.default_system_id
        if resolved is None:
            raise ValueError("No system_id provided and client is not logged in")
        return resolved

    def get_overview(self, system_id: int | None = None) -> TigoOverview:
        resolved = self._require_system_id(system_id)
        response = self.session.get(
            f"https://ei.tigoenergy.com/fleet/system/overview/index?system_id={resolved}",
            timeout=self.timeout,
        )
        response.raise_for_status()
        return parse_overview_page(response.text)

    def get_system_info(self, system_id: int | None = None) -> TigoSystemInfo:
        resolved = self._require_system_id(system_id)
        response = self.session.get(
            f"https://ei.tigoenergy.com/fleet/system/info/index?sysid={resolved}",
            timeout=self.timeout,
        )
        response.raise_for_status()
        return parse_info_page(response.text)

    def get_system_topology(self, system_id: int | None = None) -> TigoSystemTopology:
        resolved = self._require_system_id(system_id)
        response = self.session.get(
            f"https://ei.tigoenergy.com/config/editor?sysid={resolved}",
            timeout=self.timeout,
        )
        response.raise_for_status()
        return parse_system_topology(response.json())

    def get_daily_energy(self, system_id: int | None = None):
        resolved = self._require_system_id(system_id)
        response = self.session.get(
            f"https://ei.tigoenergy.com/data/daily-energy?sysid={resolved}",
            timeout=self.timeout,
        )
        response.raise_for_status()
        return parse_daily_energy(response.json())

    def get_summary(self, target_date: str | None = None, system_id: int | None = None):
        resolved = self._require_system_id(system_id)
        query_suffix = f"&date={target_date}" if target_date else ""
        response = self.session.get(
            f"https://ei.tigoenergy.com/data/summary?sysid={resolved}{query_suffix}",
            timeout=self.timeout,
        )
        response.raise_for_status()
        return parse_summary(response.json())

    def get_range_data(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        system_id: int | None = None,
    ):
        resolved = self._require_system_id(system_id)
        params = []
        if start_date:
            params.append(f"startDate={start_date}")
        if end_date:
            params.append(f"endDate={end_date}")
        suffix = ("&" + "&".join(params)) if params else ""
        response = self.session.get(
            f"https://ei.tigoenergy.com/data/range-data?sysid={resolved}{suffix}",
            timeout=self.timeout,
        )
        response.raise_for_status()
        return parse_range_data(response.json())
