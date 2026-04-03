from __future__ import annotations

import csv
import io
import logging
from datetime import date, datetime
from typing import Any

from .models import (
    TigoAlert,
    TigoAlertType,
    TigoAuth,
    TigoCSVRow,
    TigoCSVTable,
    TigoInverterLayout,
    TigoMpptLayout,
    TigoObjectNode,
    TigoObjectType,
    TigoObjectUI,
    TigoPage,
    TigoPanelLayout,
    TigoSource,
    TigoSourceSet,
    TigoStringLayout,
    TigoSummary,
    TigoSystem,
    TigoSystemLayout,
    TigoUser,
)

logger = logging.getLogger(__name__)


def _parse_datetime(value: str | None) -> datetime | None:
    if not value or value in {"null", "None"}:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        for fmt in ("%Y/%m/%d %H:%M:%S.%f", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    logger.warning("Could not parse datetime value: %r", value)
    return None


def _parse_date(value: str | None) -> date | None:
    if not value or value in {"null", "None"}:
        return None
    return date.fromisoformat(value)


def _to_float(value: Any) -> float | None:
    if value in (None, "", "null"):
        return None
    return float(value)


def _to_int(value: Any) -> int | None:
    if value in (None, "", "null"):
        return None
    return int(value)


def parse_login_response(payload: dict[str, Any]) -> TigoAuth:
    user = payload["user"]
    return TigoAuth(
        user_id=int(user["user_id"]),
        auth_token=user["auth"],
        expires=_parse_datetime(user.get("expires")),
        user_type=user.get("user_type"),
        refresh_token=user.get("refresh_token"),
        user_agreement=user.get("user_agreement"),
        raw=payload,
    )


def parse_user_response(payload: dict[str, Any]) -> TigoUser:
    user = payload["user"]
    return TigoUser(
        user_id=int(user["user_id"]),
        login=user.get("login"),
        first_name=user.get("first_name"),
        last_name=user.get("last_name"),
        email=user.get("email"),
        company=user.get("company"),
        street=user.get("street"),
        street2=user.get("street2"),
        city=user.get("city"),
        state=user.get("state"),
        zip_code=str(user.get("zip")) if user.get("zip") is not None else None,
        country=user.get("country"),
        mobile=user.get("mobile"),
        user_type=user.get("user_type"),
        avatar=user.get("avatar"),
        raw=payload,
    )


def _parse_system(data: dict[str, Any]) -> TigoSystem:
    return TigoSystem(
        system_id=int(data["system_id"]),
        external_id=data.get("external_id"),
        name=data.get("name"),
        street=data.get("street"),
        city=data.get("city"),
        state=data.get("state"),
        zip_code=str(data.get("zip")) if data.get("zip") is not None else None,
        country=data.get("country"),
        country_code=data.get("country_code"),
        latitude=_to_float(data.get("latitude")),
        longitude=_to_float(data.get("longitude")),
        timezone=data.get("timezone"),
        power_rating=_to_float(data.get("power_rating")),
        power_rating_ac=_to_float(data.get("power_rating_ac")),
        created=_parse_datetime(data.get("created")),
        commissioned=_parse_datetime(data.get("commissioned")),
        decommissioned=_parse_datetime(data.get("decommissioned")),
        status=data.get("status"),
        turn_on_date=_parse_date(data.get("turn_on_date")),
        has_monitored_modules=data.get("has_monitored_modules"),
        recent_alerts_count=_to_int(data.get("recent_alerts_count")),
        raw=data,
    )


def _extract_page_meta(payload: dict[str, Any]) -> tuple[int | None, int | None, int | None, dict[str, str]]:
    meta = payload.get("_meta") or {}
    links_raw = payload.get("_links") or {}
    links = {k: v for k, v in links_raw.items() if isinstance(v, str)}
    return _to_int(meta.get("total")), _to_int(meta.get("page")), _to_int(meta.get("limit")), links


def parse_systems_response(payload: dict[str, Any]) -> TigoPage[TigoSystem]:
    total, page, limit, links = _extract_page_meta(payload)
    return TigoPage(
        items=[_parse_system(system) for system in payload.get("systems", [])],
        total=total,
        page=page,
        limit=limit,
        links=links,
        raw=payload,
    )


def parse_system_response(payload: dict[str, Any]) -> TigoSystem:
    return _parse_system(payload["system"])


def _parse_panel(panel: dict[str, Any]) -> TigoPanelLayout:
    return TigoPanelLayout(
        panel_id=int(panel["panel_id"]),
        label=panel.get("label"),
        short_label=str(panel.get("short_label")) if panel.get("short_label") is not None else None,
        serial=panel.get("serial"),
        panel_type=panel.get("type"),
        source_id=_to_int(panel.get("source_id")),
        object_id=_to_int(panel.get("object_id")),
        panel_type_id=_to_int(panel.get("panel_type_id")),
        raw=panel,
    )


def _parse_string(string: dict[str, Any]) -> TigoStringLayout:
    return TigoStringLayout(
        string_id=int(string["string_id"]),
        label=string.get("label"),
        short_label=str(string.get("short_label")) if string.get("short_label") is not None else None,
        object_id=_to_int(string.get("object_id")),
        panels=[_parse_panel(panel) for panel in string.get("panels", [])],
        raw=string,
    )


def _parse_mppt(mppt: dict[str, Any]) -> TigoMpptLayout:
    return TigoMpptLayout(
        mppt_id=int(mppt["mppt_id"]),
        label=mppt.get("label"),
        strings=[_parse_string(string) for string in mppt.get("strings", [])],
        raw=mppt,
    )


def _parse_inverter(inverter: dict[str, Any]) -> TigoInverterLayout:
    return TigoInverterLayout(
        inverter_id=int(inverter["inverter_id"]),
        inverter_type_id=_to_int(inverter.get("inverter_type_id")),
        label=inverter.get("label"),
        object_id=_to_int(inverter.get("object_id")),
        source_id=_to_int(inverter.get("source_id")),
        serial=inverter.get("serial") or inverter.get("inverter_serial"),
        mppts=[_parse_mppt(mppt) for mppt in inverter.get("mppts", [])],
        raw=inverter,
    )


def parse_layout_response(payload: dict[str, Any]) -> TigoSystemLayout:
    system = payload["system"]
    return TigoSystemLayout(
        system_id=int(system["system_id"]),
        inverters=[_parse_inverter(inv) for inv in system.get("inverters", [])],
        raw=payload,
    )


def _parse_ui(data: dict[str, Any] | None) -> TigoObjectUI | None:
    if not data:
        return None
    return TigoObjectUI(
        x=_to_float(data.get("X")),
        y=_to_float(data.get("Y")),
        max_power=_to_float(data.get("MP")),
        label=data.get("label") or data.get("Label"),
        x1=_to_float(data.get("X1")),
        y1=_to_float(data.get("Y1")),
        x2=_to_float(data.get("X2")),
        y2=_to_float(data.get("Y2")),
        data_repeat_minutes=_to_float(data.get("DR")),
        scale=_to_float(data.get("Z")),
        raw=data,
    )


def parse_objects_response(payload: dict[str, Any]) -> list[TigoObjectNode]:
    return [
        TigoObjectNode(
            object_id=int(obj["id"]),
            label=obj.get("label"),
            object_type_id=int(obj["object_type_id"]),
            parent_id=_to_int(obj.get("parent_id")),
            datasource=obj.get("datasource"),
            children=[int(child) for child in obj.get("children") or []],
            ui=_parse_ui(obj.get("ui")),
            raw=obj,
        )
        for obj in payload.get("objects", [])
    ]


def parse_object_types_response(payload: dict[str, Any]) -> list[TigoObjectType]:
    return [
        TigoObjectType(
            object_type_id=int(item["object_type_id"]),
            label=item["label"],
            raw=item,
        )
        for item in payload.get("object_types", [])
    ]


def parse_sources_response(payload: dict[str, Any]) -> list[TigoSource]:
    sources: list[TigoSource] = []
    for source in payload.get("sources", []):
        sets = [
            TigoSourceSet(
                set_name=item["set_name"],
                last_min=_parse_datetime(item.get("last_min")),
                last_day=_parse_datetime(item.get("last_day")),
                last_raw=_parse_datetime(item.get("last_raw")),
                raw=item,
            )
            for item in source.get("sets", [])
        ]
        sources.append(
            TigoSource(
                source_id=int(source["source_id"]),
                name=source.get("name"),
                serial=source.get("serial"),
                gateway_count=_to_int(source.get("gateway_count")),
                control_state=source.get("control_state"),
                last_checkin=_parse_datetime(source.get("last_checkin")),
                timezone=source.get("timezone"),
                sw_version=source.get("sw_version"),
                created_on=_parse_datetime(source.get("created_on")),
                sets=sets,
                system_id=_to_int(source.get("system_id")),
                object_id=_to_int(source.get("object_id")),
                panel_count=_to_int(source.get("panel_count")),
                unit_type_id=_to_int(source.get("unit_type_id")),
                is_discovery_complete=source.get("is_discovery_complete"),
                raw=source,
            )
        )
    return sources


def parse_summary_response(payload: dict[str, Any]) -> TigoSummary:
    summary = payload["summary"]
    return TigoSummary(
        lifetime_energy_dc=_to_float(summary.get("lifetime_energy_dc")),
        ytd_energy_dc=_to_float(summary.get("ytd_energy_dc")),
        daily_energy_dc=_to_float(summary.get("daily_energy_dc")),
        last_power_dc=_to_float(summary.get("last_power_dc")),
        updated_on=_parse_datetime(summary.get("updated_on")),
        raw=payload,
    )


def parse_alerts_response(payload: dict[str, Any]) -> TigoPage[TigoAlert]:
    total, page, limit, links = _extract_page_meta(payload)
    items = [
        TigoAlert(
            alert_id=int(item["alert_id"]),
            added=_parse_datetime(item.get("added")),
            generated=_parse_datetime(item.get("generated")),
            system_id=_to_int(item.get("system_id")),
            unique_id=_to_int(item.get("unique_id")),
            title=item.get("title"),
            message=item.get("message"),
            description=item.get("description"),
            raw=item,
        )
        for item in payload.get("alerts", [])
    ]
    return TigoPage(items=items, total=total, page=page, limit=limit, links=links, raw=payload)


def parse_alert_types_response(payload: dict[str, Any]) -> list[TigoAlertType]:
    return [
        TigoAlertType(
            alert_type_id=int(item["alert_type_id"]),
            title=item.get("title"),
            description=item.get("description"),
            unique_id=_to_int(item.get("unique_id")),
            raw=item,
        )
        for item in payload.get("alert_types", [])
    ]


def parse_csv_table(text: str) -> TigoCSVTable:
    reader = csv.reader(io.StringIO(text.strip()))
    rows = list(reader)
    if not rows:
        return TigoCSVTable(headers=[], rows=[], raw_text=text)
    headers = rows[0]
    parsed_rows: list[TigoCSVRow] = []
    for row in rows[1:]:
        if not row or len(row) != len(headers):
            continue
        timestamp = _parse_datetime(row[0])
        values: dict[str, float | str | None] = {}
        for header, value in zip(headers[1:], row[1:]):
            if value == "":
                values[header] = None
                continue
            try:
                values[header] = float(value)
            except ValueError:
                values[header] = value
        parsed_rows.append(TigoCSVRow(timestamp=timestamp, values=values))
    return TigoCSVTable(headers=headers, rows=parsed_rows, raw_text=text)
