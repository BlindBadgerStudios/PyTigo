# pytigo

pytigo is a Python client for Tigo solar monitoring systems, focused on near-real-time monitoring for time-series systems like Prometheus.

Two backends are provided, both satisfying `TigoClientProtocol`:

| | `TigoClient` (cloud) | `TigoCCAClient` (local) |
|---|---|---|
| Transport | HTTPS to `api2.tigoenergy.com` | HTTP to CCA device on LAN |
| Auth | Bearer token (username + password login) | HTTP Basic Auth |
| System ID | From cloud account | Read from device `summary_config` |
| Telemetry params | Pin, Vin, Iin, RSSI, Temp, Tmod, Tcell, Tamb | **Pin and Vin only** |
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
)
client.login()  # probes the device and builds topology cache

systems = client.list_systems()
system = systems.items[0]  # always one entry for the local device

layout = client.get_layout(system.system_id)
summary = client.get_summary(system.system_id)

# Only Pin (power) and Vin (voltage) are available locally
aggregate = client.get_aggregate(
    system.system_id,
    start="2026-04-06T12:00:00",
    end="2026-04-06T12:15:00",
    param="Pin",
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

## Notes

The library returns typed Python dataclasses for JSON endpoints and a parsed `TigoCSVTable` for timestamped telemetry (`data/aggregate`, `data/combined`).  The table format is designed for easy flattening into Prometheus, Grafana, or ETL pipelines.

For local CCA use, `lifetime_energy_dc` and `ytd_energy_dc` on `TigoSummary` will always be `None` — this data is not exposed by the device.  Consumers should handle `None` gracefully for these fields when operating in local mode.

