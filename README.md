# pytigo

pytigo is a small Python client for authenticating against the Tigo EI portal and pulling system, panel, and production data.

What it currently supports:
- portal login with the same CSRF + form flow used by https://ei.tigoenergy.com/
- automatic discovery of the default `system_id` from the post-login redirect
- system overview bootstrap parsing
- system info page parsing
- topology parsing from the layout editor config endpoint
- daily energy history
- summary data
- range chart data
- date-info data
- minute-data payloads
- advanced data headers/payloads
- system view bootstrap/config parsing
- alerts page metadata parsing

## Install

```bash
pip install -e .
```

Metadata polish included in this repo:
- MIT license
- package homepage / repository / issues links
- PyPI-friendly classifiers and keywords
- explicit author metadata

## Quick start

```python
from pytigo import TigoClient

client = TigoClient(email="you@example.com", password="super-secret")
system_id = client.login()

overview = client.get_overview()
info = client.get_system_info()
topology = client.get_system_topology()
daily_energy = client.get_daily_energy()
summary = client.get_summary(target_date="2026-03-31")
range_data = client.get_range_data(start_date="2026-03-31", end_date="2026-03-31")
date_info = client.get_date_info("2026-03-31")
minute_data = client.get_minute_data("2026-03-31", minute="12:00")
advanced_data = client.get_advanced_data("2026-03-31")
system_view = client.get_system_view()
alerts = client.get_alerts_metadata()

print(system_id)
print(info.system_name)
print(len(topology.panels))
print(daily_energy[-1])
print(summary.total_agg_energy_wh)
print(range_data.series[0].name)
print(date_info.sunrise_time)
print(minute_data.last_data)
print(advanced_data.headers[:3])
print(system_view.channel)
print(alerts.no_alerts)
```

## Notes

This library is modeled after the shape of pyemvue in spirit: a simple client object plus parsed Python models around a vendor API surface. Unlike pyemvue, Tigo's authenticated JSON API appears to be split between multiple surfaces, and the most reliable currently reachable endpoints are the EI portal's authenticated web endpoints.

The implementation currently leans on these EI portal paths:
- `/fleet/system/overview/index`
- `/fleet/system/info/index`
- `/config/editor`
- `/data/daily-energy`
- `/data/summary`
- `/data/range-data`

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
