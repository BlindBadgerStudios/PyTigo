from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


@dataclass(slots=True)
class DailyEnergyPoint:
    date: date
    energy_wh: float


@dataclass(slots=True)
class TigoOverview:
    system_id: int
    node_aggregate_url: str | None = None
    node_system_view_url: str | None = None
    data_lifetime_url: str | None = None
    weather_url: str | None = None
    basic_charts_url: str | None = None
    calendar_url: str | None = None
    timezone: str | None = None
    chart_view: str | None = None
    chart_aggregation: str | None = None
    first_date: str | None = None
    last_date: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TigoCloudConnect:
    name: str
    serial: str
    check_in: str


@dataclass(slots=True)
class TigoInverter:
    serial: str
    label: str
    model: str
    manufacturer: str
    max_power: str


@dataclass(slots=True)
class TigoModuleSummary:
    model: str
    manufacturer: str
    max_power: str
    count: int


@dataclass(slots=True)
class TigoSystemInfo:
    system_name: str
    system_id: int
    install_date: str
    peak_power: str
    location: list[str]
    cloud_connect: TigoCloudConnect
    inverters: list[TigoInverter]
    module_summary: TigoModuleSummary


@dataclass(slots=True)
class TigoObject:
    object_id: int
    type_id: int
    type_label: str
    name: str
    parent_id: int | None = None
    max_power_watts: float | None = None
    x: float | None = None
    y: float | None = None
    angle: float | None = None
    serial: str | None = None
    mac: str | None = None
    vendor_id: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TigoSystemTopology:
    labels: dict[int, str]
    root: TigoObject
    cloud_connects: list[TigoObject]
    inverters: list[TigoObject]
    strings: list[TigoObject]
    panels: list[TigoObject]
    raw_objects: list[TigoObject]


@dataclass(slots=True)
class TigoSummary:
    last_data: datetime | None
    current_date: date | None
    data_date: date | None
    data_type: str | None
    total_agg_energy_wh: float | None
    total_agg_reclaimed_wh: float | None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TigoRangeCategory:
    timestamp: datetime

    @property
    def hour(self) -> int:
        return self.timestamp.hour


@dataclass(slots=True)
class TigoRangeSeries:
    series_id: str
    name: str
    values: list[float | int | None]
    percentages: list[float | int | None]
    unit: str | None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TigoRangeData:
    unit: str | None
    categories: list[TigoRangeCategory]
    series: list[TigoRangeSeries]
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TigoDateInfo:
    date: date
    sunrise: float | None
    sunset: float | None
    sunrise_time: str | None
    sunset_time: str | None
    light: float | None
    dark: float | None
    timezone: str | None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TigoMinuteData:
    last_data: datetime | None
    data_date: datetime | None
    data_type: str | None
    sunrise: float | None
    sunset: float | None
    light: float | None
    dark: float | None
    dataset: list[Any]
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TigoAdvancedData:
    headers: list[str]
    series: list[dict[str, Any]]
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TigoSystemView:
    has_monitored_modules: bool
    date: datetime | None
    latest: datetime | None
    channel: str | None
    timeframe: int | None
    timezone: str | None
    has_basic: bool | None
    first_day: datetime | None
    last_day_with_data: datetime | None
    config_url: str | None
    range_data_url: str | None
    month_data_url: str | None
    date_info_url: str | None
    minute_data_url: str | None
    summary_url: str | None
    agg_energy_url: str | None
    advanced_data_url: str | None
    urgent_url: str | None
    background_update_url: str | None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TigoAlertsMetadata:
    system_id: int | None
    detail_url: str | None
    archive_url: str | None
    no_alerts: bool
    raw: dict[str, Any] = field(default_factory=dict)
