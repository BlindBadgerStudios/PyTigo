from __future__ import annotations

import requests

from .models import TigoOverview, TigoSystemInfo, TigoSystemTopology
from .parsing import (
    extract_csrf_token,
    extract_default_system_id,
    parse_advanced_data,
    parse_agg_energy,
    parse_alerts_page,
    parse_calendar_optimized,
    parse_daily_energy,
    parse_date_info,
    parse_info_page,
    parse_minute_data,
    parse_overview_page,
    parse_range_data,
    parse_status_page,
    parse_summary,
    parse_system_inventory,
    parse_system_topology,
    parse_system_view_page,
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

    def _get(self, path: str, *, system_id: int | None = None, extra_query: str = ""):
        resolved = self._require_system_id(system_id)
        separator = "&" if "?" in path else "?"
        suffix = f"{separator}sysid={resolved}"
        if extra_query:
            suffix += f"&{extra_query.lstrip('&?')}"
        response = self.session.get(f"https://ei.tigoenergy.com{path}{suffix}", timeout=self.timeout)
        response.raise_for_status()
        return response

    def get_overview(self, system_id: int | None = None) -> TigoOverview:
        resolved = self._require_system_id(system_id)
        response = self.session.get(
            f"https://ei.tigoenergy.com/fleet/system/overview/index?system_id={resolved}",
            timeout=self.timeout,
        )
        response.raise_for_status()
        return parse_overview_page(response.text)

    def get_system_info(self, system_id: int | None = None) -> TigoSystemInfo:
        return parse_info_page(self._get("/fleet/system/info/index", system_id=system_id).text)

    def get_system_topology(self, system_id: int | None = None) -> TigoSystemTopology:
        return parse_system_topology(self._get("/config/editor", system_id=system_id).json())

    def get_system_inventory(self, system_id: int | None = None):
        inventory = parse_system_inventory(self._get("/config/editor", system_id=system_id).json())
        inventory.system_id = self._require_system_id(system_id)
        return inventory

    def get_daily_energy(self, system_id: int | None = None):
        return parse_daily_energy(self._get("/data/daily-energy", system_id=system_id).json())

    def get_calendar_optimized(self, system_id: int | None = None):
        return parse_calendar_optimized(self._get("/data/calendar-optimized", system_id=system_id).json())

    def get_summary(self, target_date: str | None = None, system_id: int | None = None):
        extra = f"date={target_date}" if target_date else ""
        return parse_summary(self._get("/data/summary", system_id=system_id, extra_query=extra).json())

    def get_range_data(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        system_id: int | None = None,
    ):
        params: list[str] = []
        if start_date:
            params.append(f"startDate={start_date}")
        if end_date:
            params.append(f"endDate={end_date}")
        return parse_range_data(self._get("/data/range-data", system_id=system_id, extra_query="&".join(params)).json())

    def get_date_info(self, target_date: str, system_id: int | None = None):
        return parse_date_info(self._get("/data/date-info", system_id=system_id, extra_query=f"date={target_date}").json())

    def get_minute_data(self, target_date: str, minute: str, system_id: int | None = None):
        extra = f"date={target_date}&minute={minute}"
        return parse_minute_data(self._get("/data/minute-data", system_id=system_id, extra_query=extra).json())

    def get_advanced_data(self, target_date: str, system_id: int | None = None):
        return parse_advanced_data(self._get("/data/advanced", system_id=system_id, extra_query=f"date={target_date}").json())

    def get_agg_energy(self, target_date: str, system_id: int | None = None):
        return parse_agg_energy(self._get("/data/agg-energy", system_id=system_id, extra_query=f"date={target_date}").json())

    def get_system_view(self, system_id: int | None = None):
        return parse_system_view_page(self._get("/fleet/system/view/index", system_id=system_id).text)

    def get_status(self, system_id: int | None = None):
        return parse_status_page(self._get("/fleet/system/status/index", system_id=system_id).text)

    def get_alerts_metadata(self, system_id: int | None = None):
        return parse_alerts_page(self._get("/fleet/system/alerts/index", system_id=system_id).text)
