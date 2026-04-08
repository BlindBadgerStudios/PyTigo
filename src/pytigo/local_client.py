from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any, Literal

from requests import Session

from .models import (
    TigoAlert,
    TigoAuth,
    TigoCSVRow,
    TigoCSVTable,
    TigoInverterLayout,
    TigoMpptLayout,
    TigoObjectNode,
    TigoObjectUI,
    TigoPanelLayout,
    TigoPage,
    TigoSource,
    TigoSourceSet,
    TigoStringLayout,
    TigoSummary,
    TigoSystem,
    TigoSystemLayout,
)

logger = logging.getLogger(__name__)

_SYNTHETIC_SOURCE_ID = 1
_SYNTHETIC_USER_ID = 0


class TigoCCAClient:
    """
    Client for the Tigo CCA local HTTP API.

    Wraps the four CGI endpoints exposed by the CCA device on the local network
    and returns the same model types as TigoClient, satisfying TigoClientProtocol
    so that consumers like Prom_Tigo work unchanged against either backend.

    Limitations vs cloud (TigoClient):
    - lifetime_energy_dc and ytd_energy_dc are not available; both return None.
    - Pin (power, W), Vin (voltage, V), RSSI, and derived Iin telemetry are supported.
      In local mode, Iin is derived from Pin / Vin because the tested CCA's raw
      `temp=iin` payload matched `temp=pin` rather than exposing distinct current.
      Other local temp variants accepted by the device (Tmod, Tcell, Tamb,
      power) remain exploratory/debug-only.
    - The CCA has no MPPT layer; one synthetic MPPT is created per string.
    - get_alerts() always returns an empty page.
    - No serial numbers, panel types, or sw_version information is available.
    - All CCA timestamps are local device time with no timezone information.

    Timezone handling:
    tz_offset_seconds is the offset of the CCA's local clock from UTC, in seconds
    (positive = local time is ahead of UTC, e.g. UTC+1 → 3600; negative for west
    of UTC, e.g. UTC-5 → -18000).  Set this so that returned timestamps align with
    the UTC expectations of consumers.  Defaults to 0 (CCA clock treated as UTC).

    Raw temp variants:
    Some CCAs accept additional `temp=` values on `/cgi-bin/summary_data` such as
    `tmod`, `tcell`, `tamb`, and `power`. These are device-specific and, on the
    verified device, they returned the same payload as `pin`. They are therefore
    hidden by default. Set `enable_raw_temp_variants=True` to expose them via
    get_aggregate() for exploratory/debug use. Iin is treated separately and is
    derived from Pin / Vin in local mode.
    """

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        *,
        session: Session | None = None,
        timeout: int = 30,
        tz_offset_seconds: int = 0,
        enable_raw_temp_variants: bool = False,
    ) -> None:
        self.host = host.rstrip("/")
        self.username = username
        self.password = password
        self.timeout = timeout
        self.tz_offset_seconds = tz_offset_seconds
        self.enable_raw_temp_variants = enable_raw_temp_variants
        self.session = session or Session()
        self.session.auth = (username, password)
        # populated by _build_topology(), called during login()
        self._system_id: int | None = None
        self._system_name: str | None = None
        self._panel_object_ids: dict[str, int] = {}   # label → synthetic object_id
        self._object_id_to_label: dict[int, str] = {}  # synthetic object_id → label
        self._config_nodes: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _url(self, path: str) -> str:
        return f"http://{self.host}{path}"

    def _get(self, path: str, params: dict[str, str] | None = None) -> Any:
        response = self.session.get(self._url(path), params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def _local_to_utc(self, dt: datetime) -> datetime:
        return dt - timedelta(seconds=self.tz_offset_seconds)

    def _utc_to_local(self, dt: datetime) -> datetime:
        return dt + timedelta(seconds=self.tz_offset_seconds)

    def _build_topology(self) -> None:
        """
        Fetch summary_config and build the internal panel-label → object_id mapping.

        The CCA config is a flat list of component objects.  We walk it to find:
          type 1 = System root  (provides system_id and system name)
          type 4 = Inverter
          type 3 = String       (children are module labels, e.g. "A1")
        Panels are not full objects in the config; they appear only as string IDs
        in their parent string's children list.

        We assign each panel a stable sequential int object_id so that get_layout(),
        get_objects(), and get_aggregate() all agree on the same IDs.
        """
        nodes: list[dict[str, Any]] = self._get("/cgi-bin/summary_config")
        self._config_nodes = nodes
        nodes_by_id = {str(n["id"]): n for n in nodes}

        root = next((n for n in nodes if n.get("type") == 1), None)
        if root:
            self._system_id = int(root["id"])
            self._system_name = root.get("label") or f"system_{root['id']}"
        else:
            self._system_id = 1
            self._system_name = "CCA Local"

        # Walk all strings and collect panel labels in stable order
        panel_labels: list[str] = []
        for node in nodes:
            if node.get("type") != 3:
                continue
            for child_id in node.get("children", []):
                label = str(child_id)
                # A child that is itself a non-panel type node is not a panel
                child_node = nodes_by_id.get(label)
                if child_node and child_node.get("type") in (1, 3, 4):
                    continue
                if label not in panel_labels:
                    panel_labels.append(label)

        self._panel_object_ids = {label: i + 1 for i, label in enumerate(panel_labels)}
        self._object_id_to_label = {v: k for k, v in self._panel_object_ids.items()}
        logger.debug(
            "CCA topology built: system_id=%s name=%r panels=%d",
            self._system_id,
            self._system_name,
            len(panel_labels),
        )

    def _ensure_topology(self) -> None:
        if not self._config_nodes:
            self._build_topology()

    def _make_system(self) -> TigoSystem:
        self._ensure_topology()
        return TigoSystem(
            system_id=self._system_id or 1,
            external_id=None,
            name=self._system_name,
            street=None,
            city=None,
            state=None,
            zip_code=None,
            country=None,
            country_code=None,
            latitude=None,
            longitude=None,
            timezone=None,
            power_rating=None,
            power_rating_ac=None,
            created=None,
            commissioned=None,
            decommissioned=None,
            status="local",
            turn_on_date=None,
            has_monitored_modules=bool(self._panel_object_ids),
            recent_alerts_count=0,
            raw={},
        )

    # ------------------------------------------------------------------
    # Protocol methods
    # ------------------------------------------------------------------

    def login(self) -> TigoAuth:
        """Probe the CCA and build the topology cache."""
        logger.debug("CCA login: probing %s", self.host)
        data = self._get("/cgi-bin/summary_jsconfig")
        logger.debug("CCA date: %s", data.get("sDate"))
        self._build_topology()
        return TigoAuth(
            user_id=_SYNTHETIC_USER_ID,
            auth_token="local",
            expires=None,
            user_type="local",
            refresh_token=None,
            raw=data,
        )

    def list_systems(
        self,
        *,
        page: int | None = None,
        limit: int | None = None,
        sort: str | None = None,
    ) -> TigoPage[TigoSystem]:
        system = self._make_system()
        return TigoPage(items=[system], total=1, page=1, limit=1, raw={})

    def get_system(self, system_id: int, *, include: list[str] | None = None) -> TigoSystem:
        return self._make_system()

    def get_layout(self, system_id: int) -> TigoSystemLayout:
        self._ensure_topology()
        nodes_by_id = {str(n["id"]): n for n in self._config_nodes}

        root = next((n for n in self._config_nodes if n.get("type") == 1), None)
        inv_ids = root.get("children", []) if root else [
            n["id"] for n in self._config_nodes if n.get("type") == 4
        ]

        inverters: list[TigoInverterLayout] = []
        inverter_seq = 0
        string_seq = 0

        for inv_id in inv_ids:
            inv_node = nodes_by_id.get(str(inv_id))
            if not inv_node or inv_node.get("type") != 4:
                continue
            inverter_seq += 1

            mppts: list[TigoMpptLayout] = []
            for str_id in inv_node.get("children", []):
                str_node = nodes_by_id.get(str(str_id))
                if not str_node or str_node.get("type") != 3:
                    continue
                string_seq += 1
                str_label = str_node.get("label") or f"String {str_id}"

                panels: list[TigoPanelLayout] = []
                for child_id in str_node.get("children", []):
                    label = str(child_id)
                    object_id = self._panel_object_ids.get(label)
                    if object_id is None:
                        continue
                    panels.append(TigoPanelLayout(
                        panel_id=object_id,
                        label=label,
                        short_label=label,
                        serial=None,
                        panel_type=None,
                        source_id=_SYNTHETIC_SOURCE_ID,
                        object_id=object_id,
                        panel_type_id=None,
                        raw={},
                    ))

                # Synthesize one MPPT per string — the CCA has no MPPT layer
                mppts.append(TigoMpptLayout(
                    mppt_id=string_seq,
                    label=f"MPPT-{str_label}",
                    strings=[
                        TigoStringLayout(
                            string_id=string_seq,
                            label=str_label,
                            short_label=str_label,
                            object_id=None,
                            panels=panels,
                            raw=str_node,
                        )
                    ],
                    raw={},
                ))

            inverters.append(TigoInverterLayout(
                inverter_id=inverter_seq,
                inverter_type_id=None,
                label=inv_node.get("label") or f"Inverter {inverter_seq}",
                object_id=None,
                source_id=_SYNTHETIC_SOURCE_ID,
                serial=None,
                mppts=mppts,
                raw=inv_node,
            ))

        return TigoSystemLayout(system_id=system_id, inverters=inverters, raw={})

    def get_objects(self, system_id: int) -> list[TigoObjectNode]:
        self._ensure_topology()
        return [
            TigoObjectNode(
                object_id=object_id,
                label=label,
                object_type_id=0,
                parent_id=None,
                datasource=f"LOCAL.panels.{label}",
                children=[],
                ui=TigoObjectUI(),
                raw={},
            )
            for label, object_id in self._panel_object_ids.items()
        ]

    def get_sources(self, system_id: int) -> list[TigoSource]:
        self._ensure_topology()
        last_checkin: datetime | None = None
        try:
            local_today = self._utc_to_local(datetime.utcnow()).date()
            data = self._get("/cgi-bin/summary_data", params={"date": local_today.strftime("%Y-%m-%d")})
            raw_ts = data.get("lastData")
            if raw_ts:
                local_dt = _parse_cca_datetime(raw_ts)
                if local_dt:
                    last_checkin = self._local_to_utc(local_dt)
        except Exception:
            logger.debug("Could not fetch lastData for source checkin", exc_info=True)

        set_item = TigoSourceSet(
            set_name="local",
            last_min=last_checkin,
            last_day=last_checkin,
            last_raw=last_checkin,
            raw={},
        )
        return [
            TigoSource(
                source_id=_SYNTHETIC_SOURCE_ID,
                name=f"CCA @ {self.host}",
                serial=None,
                gateway_count=1,
                control_state=None,
                last_checkin=last_checkin,
                timezone=None,
                sw_version=None,
                created_on=None,
                sets=[set_item],
                system_id=system_id,
                object_id=None,
                panel_count=len(self._panel_object_ids),
                unit_type_id=None,
                is_discovery_complete=True,
                raw={},
            )
        ]

    def get_summary(self, system_id: int) -> TigoSummary:
        local_today = self._utc_to_local(datetime.utcnow()).date()
        daily_energy: float | None = None
        last_power: float | None = None
        updated_on: datetime | None = None

        try:
            energy_rows = self._get("/cgi-bin/summary_energy")
            today_str = local_today.strftime("%Y-%m-%d")
            for entry in energy_rows:
                if entry[0] == today_str:
                    daily_energy = float(entry[1])
                    break
        except Exception:
            logger.debug("Could not fetch summary_energy", exc_info=True)

        try:
            data = self._get("/cgi-bin/summary_data", params={"date": local_today.strftime("%Y-%m-%d"), "temp": "pin"})
            rows = self._parse_summary_data_rows(data, base_date=local_today, value_mode="power")
            for local_ts, values_by_label in reversed(rows):
                numeric = [v for v in values_by_label.values() if isinstance(v, (int, float)) and v >= 0]
                if not numeric:
                    continue
                total = sum(numeric)
                if total > 0:
                    last_power = float(total)
                    updated_on = self._local_to_utc(local_ts)
                    break
            if updated_on is None:
                raw_ts = data.get("lastData")
                if raw_ts:
                    local_dt = _parse_cca_datetime(raw_ts)
                    if local_dt:
                        updated_on = self._local_to_utc(local_dt)
        except Exception:
            logger.debug("Could not fetch summary_data for summary", exc_info=True)

        return TigoSummary(
            lifetime_energy_dc=None,  # Not available from local CCA
            ytd_energy_dc=None,       # Not available from local CCA
            daily_energy_dc=daily_energy,
            last_power_dc=last_power,
            updated_on=updated_on,
            raw={},
        )

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
    ) -> TigoCSVTable:
        """
        Return per-module telemetry for the given UTC time window.

        Supported params: Pin (power, W), Vin (voltage, V), RSSI, and derived
        Iin (amps, computed from Pin / Vin when voltage is available).
        When `enable_raw_temp_variants=True`, exploratory raw variants are also
        exposed: Tmod, Tcell, Tamb, and Power.
        Other params return an empty table.

        Timestamps in the returned table are adjusted from local CCA time to UTC
        using tz_offset_seconds.  level='hour' and level='day' are not natively
        supported; minute-resolution data is returned regardless.
        """
        param_specs: dict[str, tuple[str | None, str]] = {
            "Pin": ("pin", "power"),
            "Vin": ("vin", "vin"),
            "RSSI": ("rssi", "rssi"),
            "Iin": (None, "derived_iin"),
        }
        if self.enable_raw_temp_variants:
            param_specs.update({
                "Tmod": ("tmod", "raw"),
                "Tcell": ("tcell", "raw"),
                "Tamb": ("tamb", "raw"),
                "Power": ("power", "raw"),
            })
        spec = param_specs.get(param)
        if spec is None:
            logger.debug("Param %s not supported by local CCA; returning empty table", param)
            return TigoCSVTable(headers=[], rows=[], raw_text="")
        temp_name, value_mode = spec

        start_dt = _parse_iso(start)
        end_dt = _parse_iso(end)
        if start_dt is None or end_dt is None:
            logger.warning("Could not parse start=%r or end=%r", start, end)
            return TigoCSVTable(headers=[], rows=[], raw_text="")

        # Convert UTC window to local time for date/time filtering against CCA data
        local_start = self._utc_to_local(start_dt)
        local_end = self._utc_to_local(end_dt)

        all_rows: list[tuple[datetime, dict[str, float | None]]] = []
        query_date = local_start.date()
        while query_date <= local_end.date():
            try:
                if value_mode == "derived_iin":
                    pin_rows = self._fetch_day_rows(query_date, "pin", "power", local_start, local_end)
                    vin_rows = self._fetch_day_rows(query_date, "vin", "vin", local_start, local_end)
                    day_rows = self._derive_current_rows(pin_rows, vin_rows)
                else:
                    day_rows = self._fetch_day_rows(query_date, temp_name, value_mode, local_start, local_end)
                all_rows.extend(day_rows)
            except Exception:
                logger.debug("Failed to fetch %s data for %s", param, query_date, exc_info=True)
            query_date = date.fromordinal(query_date.toordinal() + 1)

        wanted_ids = object_ids if object_ids else sorted(self._object_id_to_label.keys())
        headers = ["Timestamp"] + [str(oid) for oid in wanted_ids]

        csv_rows: list[TigoCSVRow] = []
        for local_ts, values_by_label in all_rows:
            utc_ts = self._local_to_utc(local_ts)
            row_values: dict[str, float | None] = {
                str(oid): values_by_label.get(self._object_id_to_label[oid])
                if oid in self._object_id_to_label else None
                for oid in wanted_ids
            }
            csv_rows.append(TigoCSVRow(timestamp=utc_ts, values=row_values))

        return TigoCSVTable(headers=headers, rows=csv_rows, raw_text="")

    def _fetch_day_rows(
        self,
        query_date: date,
        temp_name: str,
        value_mode: str,
        local_start: datetime,
        local_end: datetime,
    ) -> list[tuple[datetime, dict[str, float | None]]]:
        """Fetch one day of CCA data and return rows within [local_start, local_end]."""
        data = self._get(
            "/cgi-bin/summary_data",
            params={"date": query_date.strftime("%Y-%m-%d"), "temp": temp_name},
        )
        rows = self._parse_summary_data_rows(data, base_date=query_date, value_mode=value_mode)
        return [
            (local_ts, values)
            for local_ts, values in rows
            if local_start <= local_ts <= local_end
        ]

    def _parse_summary_data_rows(
        self,
        data: dict[str, Any],
        *,
        base_date: date,
        value_mode: str,
    ) -> list[tuple[datetime, dict[str, float | None]]]:
        vin_scale = self._detect_local_vin_scale(data) if value_mode == "vin" else 1.0
        rows: list[tuple[datetime, dict[str, float | None]]] = []
        for dataset in data.get("dataset", []):
            order: list[str] = dataset.get("order", [])
            for row in dataset.get("data", []):
                t_str = row.get("t", "")
                if not t_str:
                    continue
                try:
                    h, m = map(int, t_str.split(":"))
                    local_ts = datetime(base_date.year, base_date.month, base_date.day, h, m)
                except (ValueError, TypeError):
                    continue

                d: list[Any] = row.get("d", [])
                values: dict[str, float | None] = {}
                for i, label in enumerate(order):
                    raw = d[i] if i < len(d) else None
                    if raw == "-" or raw is None:
                        values[label] = None
                    elif value_mode == "vin":
                        values[label] = float(raw) / vin_scale
                    else:
                        values[label] = float(raw) if isinstance(raw, (int, float)) else None
                rows.append((local_ts, values))
        rows.sort(key=lambda item: item[0])
        return rows

    def _detect_local_vin_scale(self, data: dict[str, Any]) -> float:
        max_positive = 0.0
        for dataset in data.get("dataset", []):
            for row in dataset.get("data", []):
                for raw in row.get("d", []):
                    if isinstance(raw, (int, float)) and raw > max_positive:
                        max_positive = float(raw)
        # Some CCAs return volts directly (e.g. 30-31), while others appear to
        # return tenths of a volt (e.g. 300-310). Auto-detect per payload.
        return 10.0 if max_positive >= 100.0 else 1.0

    def _derive_current_rows(
        self,
        pin_rows: list[tuple[datetime, dict[str, float | None]]],
        vin_rows: list[tuple[datetime, dict[str, float | None]]],
    ) -> list[tuple[datetime, dict[str, float | None]]]:
        vin_by_ts = {ts: values for ts, values in vin_rows}
        derived: list[tuple[datetime, dict[str, float | None]]] = []
        for ts, pin_values in pin_rows:
            voltage_values = vin_by_ts.get(ts)
            if voltage_values is None:
                continue
            derived_values: dict[str, float | None] = {}
            labels = set(pin_values) | set(voltage_values)
            for label in labels:
                watts = pin_values.get(label)
                volts = voltage_values.get(label)
                if watts is None or volts is None or volts <= 0:
                    derived_values[label] = None
                else:
                    derived_values[label] = watts / volts
            derived.append((ts, derived_values))
        return derived

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
        """Local CCA does not expose alerts; returns an empty page."""
        return TigoPage(items=[], total=0, page=1, limit=0, raw={})


# ------------------------------------------------------------------
# Private parsing helpers
# ------------------------------------------------------------------

def _parse_iso(value: str) -> datetime | None:
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(value)
        return dt.replace(tzinfo=None)  # strip tzinfo; treat as naive
    except ValueError:
        return None


def _parse_cca_datetime(value: str) -> datetime | None:
    """Parse a CCA datetime string such as '2026-04-06 23:59:59.000'."""
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None
