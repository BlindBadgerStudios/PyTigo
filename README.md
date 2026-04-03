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

## Install

```bash
pip install -e .
```

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

print(system_id)
print(info.system_name)
print(len(topology.panels))
print(daily_energy[-1])
print(summary.total_agg_energy_wh)
print(range_data.series[0].name)
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
