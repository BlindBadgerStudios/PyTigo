# pytigo

pytigo is a Python client for Tigo solar monitoring systems, focused on near-real-time monitoring for time-series systems like Prometheus.

Two backends are provided, both satisfying `TigoClientProtocol`:

| | `TigoClient` (cloud) | `TigoCCAClient` (local) |
|---|---|---|
| Transport | HTTPS to `api2.tigoenergy.com` | HTTP to CCA device on LAN |
| Auth | Bearer token (username + password login) | HTTP Basic Auth |
| System ID | From cloud account | Read from device `summary_config` |
| Telemetry params | Pin, Vin, Iin, RSSI, Temp, Tmod, Tcell, Tamb | **Pin, Vin, RSSI, derived Iin** |
| Lifetime energy | Yes | **Not available (returns `None`)** |
| YTD energy | Yes | **Not available (returns `None`)** |
| Daily energy | Yes | Yes (~12-day rolling window) |
| MPPT layer | Yes (from cloud layout) | **Synthesized — one per string** |
| Alerts | Yes | **Not available (empty page)** |
| Serial / panel type | Yes | **Not available** |
| Timestamps | UTC-aware from cloud | Local device time; adjust with `tz_offset_seconds` |

## Install

```bash
pip install pytigo
```

## Quick start — cloud

```python
from pytigo import TigoClient

client = TigoClient(username="you@example.com", password="super-secret")
auth = client.login()

systems = client.list_systems()
system = systems.items[0]

layout = client.get_layout(system.system_id)
objects = client.get_objects(system.system_id)
sources = client.get_sources(system.system_id)
summary = client.get_summary(system.system_id)
aggregate = client.get_aggregate(
    system.system_id,
    start="2026-03-31T00:00:00",
    end="2026-03-31T23:59:59",
    level="day",
    param="Pin",
)
combined = client.get_combined(
    system.system_id,
    start="2026-03-31T00:00:00",
    end="2026-03-31T23:59:59",
    agg="day",
)
alerts = client.get_alerts(system.system_id, limit=10)
alert_types = client.get_alert_types()
```

## Quick start — local CCA

```python
from pytigo import TigoCCAClient

# tz_offset_seconds = local clock offset from UTC
# e.g. UTC-5 (EST) = -18000, UTC+1 = 3600, UTC = 0
client = TigoCCAClient(
    host="192.168.1.100",
    username="Tigo",
    password="$olar",
    tz_offset_seconds=-18000,
    # opt-in exploratory mode for raw temp variants like Iin/Tmod/Tcell/Tamb/Power
    enable_raw_temp_variants=False,
)
client.login()  # probes the device and builds topology cache

systems = client.list_systems()
system = systems.items[0]  # always one entry for the local device

layout = client.get_layout(system.system_id)
summary = client.get_summary(system.system_id)

# Pin (power), Vin (voltage), RSSI, and derived Iin are available locally
aggregate = client.get_aggregate(
    system.system_id,
    start="2026-04-06T12:00:00",
    end="2026-04-06T12:15:00",
    param="Pin",
)
rssi = client.get_aggregate(
    system.system_id,
    start="2026-04-06T12:00:00",
    end="2026-04-06T12:15:00",
    param="RSSI",
)
iin = client.get_aggregate(
    system.system_id,
    start="2026-04-06T12:00:00",
    end="2026-04-06T12:15:00",
    param="Iin",
)
```

## Writing code against both backends

Use `TigoClientProtocol` as the type hint so your code works with either client:

```python
from pytigo import TigoClient, TigoCCAClient, TigoClientProtocol

def build_client(mode: str, **kwargs) -> TigoClientProtocol:
    if mode == "local":
        return TigoCCAClient(**kwargs)
    return TigoClient(**kwargs)

def fetch_summary(client: TigoClientProtocol, system_id: int):
    client.login()
    return client.get_summary(system_id)
```

## Cloud API areas supported (TigoClient)

- users/login, users/logout, users/get
- systems/list, systems/view, systems/layout
- objects/system, objects/types
- sources/system
- data/summary, data/aggregate, data/combined
- alerts/system, alerts/types

## Local CCA status (verified against a live device)

Verified with local credentials `Tigo` / `$olar` on a CCA at `192.168.192.114`:

Available local data endpoints:
- `/cgi-bin/summary_jsconfig`
- `/cgi-bin/summary_config`
- `/cgi-bin/summary_energy`
- `/cgi-bin/summary_data?date=YYYY-MM-DD`
- `/cgi-bin/summary` -> redirects to `/summary/`
- `/summary/` -> authenticated UI page that uses the endpoints above

Known endpoints currently blocked by available credentials:
- `/cgi-bin/info` -> returns `Access Denied.`
- `/cgi-bin/network` -> returns `Access Denied.`

These should be re-checked in the future if higher-privilege credentials become available.

## Local summary_data temp variants

The local CCA accepts `temp=` variants on `/cgi-bin/summary_data`.

Verified distinct variants:
- `pin` -> power-like panel telemetry used by local power example/client
- `vin` -> panel voltage telemetry
- `rssi` -> panel wireless signal telemetry

Derived variant exposed by the library:
- `Iin` -> panel current derived from `Pin / Vin` because the tested device's raw `temp=iin` payload matched `temp=pin`

For local `Vin`, the library auto-detects whether the CCA payload is already in volts (e.g. `30-31`) or in tenths of a volt (e.g. `300-310`) and scales accordingly.

For local summary/source freshness, the library now prefers the device-reported date from `/cgi-bin/summary_jsconfig` (`sDate`) instead of assuming the current UTC-derived day. This avoids a verified failure mode where the CCA still serves valid telemetry for the prior device day while naive `utcnow()`-based lookup lands on the wrong date. Local summary power also preserves legitimate `0.0 W` values from the latest populated sample instead of dropping the metric entirely after sunset.

Accepted but not distinct on the tested device:
- `tmod`
- `tcell`
- `tamb`
- `power`

On the tested CCA, those variants returned the same payload as `pin`.
They are available only in opt-in exploratory mode by constructing `TigoCCAClient(..., enable_raw_temp_variants=True)` and calling:
- `param="Tmod"`
- `param="Tcell"`
- `param="Tamb"`
- `param="Power"`

Because these were not distinct on the verified device, they should be treated as raw/debug data rather than stable semantic metrics.

Observed but empty on the tested device:
- `temp` -> HTTP 200 with empty body

## Local examples

- `examples/local_cca_power.py` -> auto-finds the latest populated Pin window and prints per-panel power
- `examples/local_cca_endpoints.py` -> probes local summary/info/network endpoints and enumerates `temp=` variants

## Cloud live validation example

- `examples/cloud_live_validation.py` -> validates the official API v3 end-to-end against a real account and explicitly reports the known `aggregate` / `combined` limitation when those endpoints return only `Datetime`

## Notes

The library returns typed Python dataclasses for JSON endpoints and a parsed `TigoCSVTable` for timestamped telemetry (`data/aggregate`, `data/combined`).  The table format is designed for easy flattening into Prometheus, Grafana, or ETL pipelines.

For local CCA use, `lifetime_energy_dc` and `ytd_energy_dc` on `TigoSummary` will always be `None` — this data is not exposed by the device.  Consumers should handle `None` gracefully for these fields when operating in local mode.

