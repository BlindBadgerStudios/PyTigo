from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass
class TigoAuth:
    user_id: int
    auth_token: str
    expires: datetime | None
    user_type: str | None
    refresh_token: str | None = None
    user_agreement: bool | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class TigoUser:
    user_id: int
    login: str | None
    first_name: str | None
    last_name: str | None
    email: str | None
    company: str | None
    street: str | None
    street2: str | None
    city: str | None
    state: str | None
    zip_code: str | None
    country: str | None
    mobile: str | None
    user_type: str | None
    avatar: str | None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class TigoSystem:
    system_id: int
    external_id: str | None
    name: str | None
    street: str | None
    city: str | None
    state: str | None
    zip_code: str | None
    country: str | None
    country_code: str | None
    latitude: float | None
    longitude: float | None
    timezone: str | None
    power_rating: float | None
    power_rating_ac: float | None
    created: datetime | None
    commissioned: datetime | None
    decommissioned: datetime | None
    status: str | None
    turn_on_date: date | None
    has_monitored_modules: bool | None
    recent_alerts_count: int | None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class TigoPanelLayout:
    panel_id: int
    label: str | None
    short_label: str | None
    serial: str | None
    panel_type: str | None
    source_id: int | None
    object_id: int | None
    panel_type_id: int | None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class TigoStringLayout:
    string_id: int
    label: str | None
    short_label: str | None
    object_id: int | None
    panels: list[TigoPanelLayout]
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class TigoMpptLayout:
    mppt_id: int
    label: str | None
    strings: list[TigoStringLayout]
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class TigoInverterLayout:
    inverter_id: int
    inverter_type_id: int | None
    label: str | None
    object_id: int | None
    source_id: int | None
    serial: str | None
    mppts: list[TigoMpptLayout]
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class TigoSystemLayout:
    system_id: int
    inverters: list[TigoInverterLayout]
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class TigoObjectUI:
    x: float | None = None
    y: float | None = None
    max_power: float | None = None
    label: str | None = None
    x1: float | None = None
    y1: float | None = None
    x2: float | None = None
    y2: float | None = None
    data_repeat_minutes: float | None = None
    scale: float | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class TigoObjectNode:
    object_id: int
    label: str | None
    object_type_id: int
    parent_id: int | None
    datasource: str | None
    children: list[int]
    ui: TigoObjectUI | None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class TigoObjectType:
    object_type_id: int
    label: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class TigoSourceSet:
    set_name: str
    last_min: datetime | None
    last_day: datetime | None
    last_raw: datetime | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class TigoSource:
    source_id: int
    name: str | None
    serial: str | None
    gateway_count: int | None
    control_state: str | None
    last_checkin: datetime | None
    timezone: str | None
    sw_version: str | None
    created_on: datetime | None
    sets: list[TigoSourceSet]
    system_id: int | None
    object_id: int | None
    panel_count: int | None
    unit_type_id: int | None
    is_discovery_complete: bool | None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class TigoSummary:
    lifetime_energy_dc: float | None
    ytd_energy_dc: float | None
    daily_energy_dc: float | None
    last_power_dc: float | None
    updated_on: datetime | None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class TigoAlert:
    alert_id: int
    added: datetime | None
    generated: datetime | None
    system_id: int | None
    unique_id: int | None
    title: str | None
    message: str | None
    description: str | None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class TigoAlertType:
    alert_type_id: int
    title: str | None
    description: str | None
    unique_id: int | None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class TigoPage(Generic[T]):
    items: list[T]
    total: int | None = None
    page: int | None = None
    limit: int | None = None
    links: dict[str, str] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class TigoCSVRow:
    timestamp: datetime | None
    values: dict[str, float | str | None]


@dataclass
class TigoCSVTable:
    headers: list[str]
    rows: list[TigoCSVRow]
    raw_text: str
