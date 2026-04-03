"""
Live integration smoke test: pull per-panel power production from the Tigo API.

Usage:
    TIGO_USERNAME=you@example.com TIGO_PASSWORD=secret python examples/live_panel_power.py

Optional env vars:
    TIGO_SYSTEM_ID   -- integer system ID to query (defaults to first system on account)
    TIGO_WINDOW_MIN  -- how many minutes of history to fetch (default: 15)
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

UTC = timezone.utc

from pytigo import TigoClient


def main() -> None:
    username = os.environ.get("TIGO_USERNAME")
    password = os.environ.get("TIGO_PASSWORD")
    if not username or not password:
        print("ERROR: set TIGO_USERNAME and TIGO_PASSWORD environment variables")
        sys.exit(1)

    system_id_env = os.environ.get("TIGO_SYSTEM_ID")
    window_minutes = int(os.environ.get("TIGO_WINDOW_MIN", "15"))

    client = TigoClient(username=username, password=password)

    # --- Login ---
    print("Logging in...")
    auth = client.login()
    print(f"  user_id={auth.user_id}  expires={auth.expires}")

    # --- Resolve system ---
    if system_id_env:
        system_id = int(system_id_env)
        system = client.get_system(system_id)
    else:
        page = client.list_systems()
        if not page.items:
            print("ERROR: no systems found on this account")
            sys.exit(1)
        system = page.items[0]
        system_id = system.system_id

    print(f"\nSystem: {system.name!r}  id={system_id}  tz={system.timezone}")
    if system.power_rating:
        print(f"  Rated DC capacity: {system.power_rating:,.0f} W")
    if system.power_rating_ac:
        print(f"  Rated AC capacity: {system.power_rating_ac:,.0f} W")

    # --- Current summary ---
    summary = client.get_summary(system_id)
    print(f"\n--- System Summary (as of {summary.updated_on}) ---")
    if summary.last_power_dc is not None:
        print(f"  Current power  : {summary.last_power_dc:>10,.1f} W")
    if summary.daily_energy_dc is not None:
        print(f"  Today energy   : {summary.daily_energy_dc / 1000:>10,.2f} kWh")
    if summary.ytd_energy_dc is not None:
        print(f"  YTD energy     : {summary.ytd_energy_dc / 1000:>10,.2f} kWh")
    if summary.lifetime_energy_dc is not None:
        print(f"  Lifetime energy: {summary.lifetime_energy_dc / 1000:>10,.2f} kWh")

    # --- Layout: collect panel object_ids ---
    print("\nFetching layout...")
    layout = client.get_layout(system_id)
    panels: list[dict] = []
    for inverter in layout.inverters:
        for mppt in inverter.mppts:
            for string in mppt.strings:
                for panel in string.panels:
                    if panel.object_id is not None:
                        panels.append({
                            "object_id": int(panel.object_id),
                            "label": panel.label or f"panel_{panel.panel_id}",
                            "serial": panel.serial or "",
                            "inverter": inverter.label or str(inverter.inverter_id),
                            "string": string.label or str(string.string_id),
                        })

    if not panels:
        print("No panels found in layout (object_id not set). Cannot fetch telemetry.")
        sys.exit(0)

    print(f"  Found {len(panels)} panels across {len(layout.inverters)} inverter(s)")

    # --- Telemetry: Pin (power) for each panel ---
    end = datetime.now(tz=UTC)
    start = end - timedelta(minutes=window_minutes)
    start_str = start.strftime("%Y-%m-%dT%H:%M:%S")
    end_str = end.strftime("%Y-%m-%dT%H:%M:%S")
    object_ids = [p["object_id"] for p in panels]

    print(f"\nFetching Pin telemetry ({window_minutes}-min window: {start_str} → {end_str})...")
    table = client.get_aggregate(
        system_id,
        start=start_str,
        end=end_str,
        level="min",
        param="Pin",
        object_ids=object_ids,
        header="id",
    )

    if not table.rows:
        print("No telemetry rows returned. The system may not have recent data.")
        sys.exit(0)

    # Walk rows in reverse to find the most recent non-null value per panel
    latest: dict[int, tuple[datetime | None, float]] = {}
    id_str_map = {str(p["object_id"]): p["object_id"] for p in panels}
    for row in reversed(table.rows):
        for col, oid in id_str_map.items():
            if oid in latest:
                continue
            val = row.values.get(col)
            if isinstance(val, float):
                latest[oid] = (row.timestamp, val)
        if len(latest) == len(panels):
            break

    panels_by_oid = {p["object_id"]: p for p in panels}

    print(f"\n--- Per-Panel Power (most recent sample in last {window_minutes} min) ---")
    header = f"{'Label':<12} {'Serial':<14} {'Inverter':<14} {'String':<12} {'Power (W)':>10}  {'Timestamp'}"
    print(header)
    print("-" * len(header))

    total_power = 0.0
    missing = []
    for panel in panels:
        oid = panel["object_id"]
        if oid in latest:
            ts, power = latest[oid]
            total_power += power
            ts_str = ts.strftime("%H:%M:%S") if ts else "?"
            print(f"  {panel['label']:<10} {panel['serial']:<14} {panel['inverter']:<14} {panel['string']:<12} {power:>10.1f}  {ts_str}")
        else:
            missing.append(panel["label"])

    print(f"\n  Total power (reporting panels): {total_power:,.1f} W")
    if missing:
        print(f"  No data for {len(missing)} panel(s): {', '.join(missing)}")

    print("\nDone.")


if __name__ == "__main__":
    main()
