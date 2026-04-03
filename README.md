# pytigo

pytigo is a Python client for the documented Tigo REST API v3.

It is now centered on the official API described in Tigo-API-V3.pdf, using:
- base URL: https://api2.tigoenergy.com/api/v3/
- token auth from `users/login`
- documented systems, objects, sources, and data endpoints

Supported official API areas:
- users/login
- users/logout
- users/get
- systems/list
- systems/view
- systems/layout
- objects/system
- objects/types
- sources/system
- data/summary
- data/aggregate
- data/combined
- alerts/system
- alerts/types

## Install

```bash
pip install -e .
```

## Quick start

```python
from pytigo import TigoClient

client = TigoClient(username="you@example.com", password="super-secret")
auth = client.login()

systems = client.list_systems()
system = systems[0]

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

print(auth.user_id)
print(system.name)
print(layout.inverters[0].label if layout.inverters else None)
print(len(objects))
print(sources[0].serial if sources else None)
print(summary.daily_energy_dc)
print(aggregate.rows[0].values)
print(combined.rows[0].values)
print(alerts[0].title if alerts else None)
print(alert_types[0].title if alert_types else None)
```

## Notes

The library returns typed Python models for JSON endpoints and a parsed table model for CSV-style telemetry endpoints like `data/aggregate` and `data/combined`.

`data/aggregate` and `data/combined` are especially useful for exporter/monitoring use cases because they preserve timestamped telemetry in a table-shaped format that is easy to flatten for Prometheus, Grafana, or ETL pipelines.

## Development

```bash
python -m pytest -q
```

## PyPI-ready validation

Before publishing, build and validate the package locally:

```bash
python -m pip install -e '.[dev]'
python -m build
python -m twine check dist/*
```

This repo is prepared for that flow, but it has not been published yet.
