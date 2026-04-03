from __future__ import annotations

import json
import re
from datetime import date, datetime
from html import unescape
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlparse

from .models import (
    DailyEnergyPoint,
    TigoAdvancedData,
    TigoAlertsMetadata,
    TigoCloudConnect,
    TigoDateInfo,
    TigoInverter,
    TigoMinuteData,
    TigoModuleSummary,
    TigoObject,
    TigoOverview,
    TigoRangeCategory,
    TigoRangeData,
    TigoRangeSeries,
    TigoSummary,
    TigoSystemInfo,
    TigoSystemTopology,
    TigoSystemView,
)


def extract_csrf_token(html: str) -> str:
    match = re.search(r'name=["\']_csrf["\']\s+value=["\']([^"\']+)', html)
    if not match:
        raise ValueError("Could not find Tigo CSRF token in login page")
    return unescape(match.group(1))


def extract_default_system_id(url: str) -> int:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    for key in ("system_id", "sysid"):
        values = query.get(key)
        if values:
            return int(values[0])
    raise ValueError(f"Could not determine default system id from URL: {url}")


def _extract_js_object(html: str, variable_name: str) -> dict:
    match = re.search(rf"var\s+{re.escape(variable_name)}\s*=\s*(\{{.*?\}});", html, re.S)
    if not match:
        raise ValueError(f"Could not locate JavaScript object {variable_name}")
    raw_json = match.group(1).replace(r"\/", "/")
    return json.loads(raw_json)


def _extract_js_string(html: str, variable_name: str) -> str | None:
    match = re.search(rf'var\s+{re.escape(variable_name)}\s*=\s*"([^"]*)";', html)
    if not match:
        return None
    return match.group(1).replace(r"\/", "/")


def _parse_optional_datetime(value: str | None, fmt: str | None = None):
    if not value:
        return None
    if fmt:
        return datetime.strptime(value, fmt)
    return datetime.fromisoformat(value)


def parse_overview_page(html: str) -> TigoOverview:
    data = _extract_js_object(html, "GLOBALTIGONOCONFLICT")
    chart = data.get("chart", {})
    calendar = data.get("calendar", {})
    return TigoOverview(
        system_id=int(data["systemId"]),
        node_aggregate_url=data.get("nodeAggregateUrl"),
        node_system_view_url=data.get("nodeSystemViewUrl"),
        data_lifetime_url=data.get("dataLifetimeUrl"),
        weather_url=data.get("weatherUrl"),
        basic_charts_url=data.get("basicChartsUrl"),
        calendar_url=calendar.get("url"),
        timezone=calendar.get("timezone"),
        chart_view=chart.get("view"),
        chart_aggregation=chart.get("agg"),
        first_date=chart.get("firstDate"),
        last_date=chart.get("lastDate"),
        raw=data,
    )


class _TextCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tokens: list[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.tokens.append(text)


def _tokens(html: str) -> list[str]:
    parser = _TextCollector()
    parser.feed(html)
    normalized: list[str] = []
    for token in parser.tokens:
        for part in token.splitlines():
            part = part.strip()
            if part:
                normalized.append(part)
    return normalized


def _expect_after(tokens: list[str], label: str, offset: int = 1) -> str:
    idx = tokens.index(label)
    return tokens[idx + offset]


def parse_info_page(html: str) -> TigoSystemInfo:
    tokens = _tokens(html)
    system_name = _expect_after(tokens, "System Name")
    system_id = int(_expect_after(tokens, "ID"))
    install_date = _expect_after(tokens, "Install Date")
    peak_power = _expect_after(tokens, "Peak Power")
    location_idx = tokens.index("Location")
    location = tokens[location_idx + 1 : location_idx + 4]

    cloud_idx = tokens.index("Cloud Connect Advanced")
    cloud_connect = TigoCloudConnect(
        name=tokens[cloud_idx + 4],
        serial=tokens[cloud_idx + 5],
        check_in=tokens[cloud_idx + 6],
    )

    inverter_idx = tokens.index("Inverters")
    modules_idx = tokens.index("Modules")
    inverter_tokens = tokens[inverter_idx + 5 : modules_idx]
    inverters: list[TigoInverter] = []
    for chunk_start in range(0, len(inverter_tokens), 5):
        chunk = inverter_tokens[chunk_start : chunk_start + 5]
        if len(chunk) < 5:
            continue
        inverters.append(
            TigoInverter(
                serial="" if chunk[0] == "-" else chunk[0],
                label=chunk[1],
                model=chunk[2],
                manufacturer=chunk[3],
                max_power=chunk[4],
            )
        )

    module_tokens = tokens[modules_idx + 5 : modules_idx + 9]
    module_summary = TigoModuleSummary(
        model=module_tokens[0],
        manufacturer=module_tokens[1],
        max_power=module_tokens[2],
        count=int(module_tokens[3]),
    )

    return TigoSystemInfo(
        system_name=system_name,
        system_id=system_id,
        install_date=install_date,
        peak_power=peak_power,
        location=location,
        cloud_connect=cloud_connect,
        inverters=inverters,
        module_summary=module_summary,
    )


def parse_system_topology(payload: dict) -> TigoSystemTopology:
    system = payload["system"]
    labels = {int(key): value for key, value in system["object_labels"].items()}
    objects = [
        TigoObject(
            object_id=int(item["A"]),
            type_id=int(item["B"]),
            type_label=labels.get(int(item["B"]), f"Unknown-{item['B']}"),
            name=item.get("C", ""),
            parent_id=None if item.get("K") in (None, -1) else int(item["K"]),
            max_power_watts=float(item["J"]) if item.get("J") is not None else None,
            x=float(item["M"]) if item.get("M") is not None else None,
            y=float(item["L"]) if item.get("L") is not None else None,
            angle=float(item["D"]) if item.get("D") is not None else None,
            serial=item.get("T"),
            mac=item.get("V"),
            vendor_id=int(item["U"]) if item.get("U") is not None else None,
            raw=item,
        )
        for item in system["objects"]
    ]
    by_type: dict[str, list[TigoObject]] = {}
    for obj in objects:
        by_type.setdefault(obj.type_label, []).append(obj)
    roots = [obj for obj in objects if obj.parent_id is None]
    if not roots:
        raise ValueError("Topology payload did not contain a root system object")
    return TigoSystemTopology(
        labels=labels,
        root=roots[0],
        cloud_connects=by_type.get("Cloud Connect", []),
        inverters=by_type.get("Inverter", []),
        strings=by_type.get("String", []),
        panels=by_type.get("Panel", []),
        raw_objects=objects,
    )


def parse_daily_energy(payload: dict[str, float | int]) -> list[DailyEnergyPoint]:
    return [
        DailyEnergyPoint(date=date.fromisoformat(day), energy_wh=float(value))
        for day, value in sorted(payload.items())
    ]


def parse_summary(payload: dict) -> TigoSummary:
    stats = payload.get("dailyStats", {})
    return TigoSummary(
        last_data=_parse_optional_datetime(payload.get("lastData")),
        current_date=date.fromisoformat(payload["currentDate"]) if payload.get("currentDate") else None,
        data_date=date.fromisoformat(payload["dataDate"]) if payload.get("dataDate") else None,
        data_type=payload.get("dataType"),
        total_agg_energy_wh=float(stats["total_agg_energy"]) if stats.get("total_agg_energy") is not None else None,
        total_agg_reclaimed_wh=float(stats["total_agg_reclaimed"]) if stats.get("total_agg_reclaimed") is not None else None,
        raw=payload,
    )


def parse_range_data(payload: dict) -> TigoRangeData:
    categories = [TigoRangeCategory(timestamp=datetime.fromisoformat(item)) for item in payload.get("c", [])]
    series = [
        TigoRangeSeries(
            series_id=str(item.get("i", "")),
            name=item.get("n", ""),
            values=list(item.get("v", [])),
            percentages=list(item.get("p", [])),
            unit=item.get("u"),
            raw=item,
        )
        for item in payload.get("s", [])
    ]
    unit = series[0].unit if series else None
    return TigoRangeData(unit=unit, categories=categories, series=series, raw=payload)


def parse_date_info(payload: dict[str, dict]) -> TigoDateInfo:
    day, info = next(iter(payload.items()))
    return TigoDateInfo(
        date=date.fromisoformat(day),
        sunrise=info.get("sunrise"),
        sunset=info.get("sunset"),
        sunrise_time=info.get("sunrise_time"),
        sunset_time=info.get("sunset_time"),
        light=info.get("light"),
        dark=info.get("dark"),
        timezone=info.get("timezone"),
        raw=payload,
    )


def parse_minute_data(payload: dict) -> TigoMinuteData:
    return TigoMinuteData(
        last_data=_parse_optional_datetime(payload.get("lastData"), "%Y-%m-%d %H:%M:%S"),
        data_date=_parse_optional_datetime(payload.get("dataDate"), "%Y-%m-%d %H:%M:%S"),
        data_type=payload.get("dataType"),
        sunrise=payload.get("sunrise"),
        sunset=payload.get("sunset"),
        light=payload.get("light"),
        dark=payload.get("dark"),
        dataset=list(payload.get("dataset", [])),
        raw=payload,
    )


def parse_advanced_data(payload: dict) -> TigoAdvancedData:
    series = list(payload.get("s", []))
    headers = list(series[0].get("h", [])) if series else []
    return TigoAdvancedData(headers=headers, series=series, raw=payload)


def parse_system_view_page(html: str) -> TigoSystemView:
    config = _extract_js_object(html, "arrayConfig")
    return TigoSystemView(
        has_monitored_modules=bool(config.get("hasMonitoredModules")),
        date=_parse_optional_datetime(config.get("date"), "%Y-%m-%d %H:%M:%S"),
        latest=_parse_optional_datetime(config.get("latest"), "%Y-%m-%d %H:%M:%S"),
        channel=config.get("channel"),
        timeframe=config.get("timeframe"),
        timezone=config.get("timezone"),
        has_basic=config.get("has_basic"),
        first_day=_parse_optional_datetime(config.get("first_day")),
        last_day_with_data=_parse_optional_datetime(config.get("last_day_with_data"), "%Y-%m-%d %H:%M:%S"),
        config_url=_extract_js_string(html, "config_url"),
        range_data_url=_extract_js_string(html, "rangedata_url"),
        month_data_url=_extract_js_string(html, "monthdata_url"),
        date_info_url=_extract_js_string(html, "dateinfo_url"),
        minute_data_url=_extract_js_string(html, "minutedata_url"),
        summary_url=_extract_js_string(html, "datedata_url"),
        agg_energy_url=_extract_js_string(html, "aggEnergyUrl"),
        advanced_data_url=_extract_js_string(html, "chartdownload_url"),
        urgent_url=_extract_js_string(html, "urgent_url"),
        background_update_url=_extract_js_string(html, "background_update_url"),
        raw=config,
    )


def parse_alerts_page(html: str) -> TigoAlertsMetadata:
    tokens = _tokens(html)
    system_id_match = re.search(r'var\s+sysid\s*=\s*"(\d+)";', html)
    system_id = int(system_id_match.group(1)) if system_id_match else None
    raw = _extract_js_object(html, "ALERTSNOCONFLICT")
    return TigoAlertsMetadata(
        system_id=system_id,
        detail_url=raw.get("detail_url"),
        archive_url=raw.get("archive_url"),
        no_alerts="No alerts for this system" in tokens,
        raw=raw,
    )
