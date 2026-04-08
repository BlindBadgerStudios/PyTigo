"""
Live smoke test: pull per-panel power from a Tigo CCA on the local network.

Usage:
    TIGO_LOCAL_HOST=192.168.1.100 python examples/local_cca_power.py

Optional env vars:
    TIGO_LOCAL_USERNAME          -- CCA username (default: Tigo)
    TIGO_LOCAL_PASSWORD          -- CCA password (default: $olar)
    TIGO_LOCAL_TZ_OFFSET_SECONDS -- CCA local clock offset from UTC in seconds
                                    e.g. -18000 for UTC-5 (EST), 3600 for UTC+1
                                    (default: 0, treats CCA clock as UTC)
    TIGO_WINDOW_MIN              -- minutes of history to fetch (default: 15)
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

UTC = timezone.utc

from pytigo import TigoCCAClient


def _find_latest_nonzero_row(client: TigoCCAClient, system_id: int, object_ids: list[int], end: datetime) -> tuple[datetime | None, dict[str, float | None]]:
    """
    Find the latest timestamp with any non-zero Pin telemetry.

    The CCA's reported `lastData` timestamp can extend beyond the last row that
    actually contains module telemetry, so we scan from local midnight to `end`
    and then walk backward to locate the freshest populated row.
    """
    start_of_day = end.replace(hour=0, minute=0, second=0, microsecond=0)
    table = client.get_aggregate(
        system_id,
        start=start_of_day.strftime("%Y-%m-%dT%H:%M:%S"),
        end=end.strftime("%Y-%m-%dT%H:%M:%S"),
        level="min",
        param="Pin",
        object_ids=object_ids,
    )
    for row in reversed(table.rows):
        if any(isinstance(v, (int, float)) and v > 0 for v in row.values.values()):
            return row.timestamp, row.values
    return None, {}


def main() -> None:
    host = os.environ.get("TIGO_LOCAL_HOST")
    if not host:
        print("ERROR: set TIGO_LOCAL_HOST to the CCA device IP or hostname")
        sys.exit(1)

    username = os.environ.get("TIGO_LOCAL_USERNAME", "Tigo")
    password = os.environ.get("TIGO_LOCAL_PASSWORD", "$olar")
    tz_offset = int(os.environ.get("TIGO_LOCAL_TZ_OFFSET_SECONDS", "0"))
    window_minutes = int(os.environ.get("TIGO_WINDOW_MIN", "15"))

    client = TigoCCAClient(
        host=host,
        username=username,
        password=password,
        tz_offset_seconds=tz_offset,
    )

    # --- Login / probe ---
    print(f"Connecting to CCA at {host}...")
    auth = client.login()
    print(f"  auth_token={auth.auth_token}  user_type={auth.user_type}")

    # --- Resolve system ---
    page = client.list_systems()
    if not page.items:
        print("ERROR: no system found on CCA")
        sys.exit(1)
    system = page.items[0]
    system_id = system.system_id
    print(f"\nSystem: {system.name!r}  id={system_id}")

    # --- Current summary ---
    summary = client.get_summary(system_id)
    print(f"\n--- System Summary (as of {summary.updated_on}) ---")
    if summary.last_power_dc is not None:
        print(f"  Current power  : {summary.last_power_dc:>10,.1f} W")
    if summary.daily_energy_dc is not None:
        print(f"  Today energy   : {summary.daily_energy_dc / 1000:>10,.2f} kWh")
    # lifetime_energy_dc and ytd_energy_dc are not available from local CCA
    print("  Lifetime / YTD : not available (local mode)")

    # --- Layout ---
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
                            "inverter": inverter.label or str(inverter.inverter_id),
                            "string": string.label or str(string.string_id),
                        })

    if not panels:
        print("No panels found in layout.")
        sys.exit(0)

    print(f"  Found {len(panels)} panels across {len(layout.inverters)} inverter(s)")

    # --- Telemetry: Pin (power) ---
    object_ids = [p["object_id"] for p in panels]

    if summary.updated_on is not None:
        search_end = summary.updated_on
    else:
        search_end = datetime.now(tz=UTC).replace(tzinfo=None)

    latest_ts, _ = _find_latest_nonzero_row(client, system_id, object_ids, search_end)
    if latest_ts is None:
        print("No non-zero Pin telemetry found between local midnight and the latest device timestamp.")
        sys.exit(0)

    end = latest_ts
    start = end - timedelta(minutes=window_minutes)
    start_str = start.strftime("%Y-%m-%dT%H:%M:%S")
    end_str = end.strftime("%Y-%m-%dT%H:%M:%S")

    print(f"\nFetching Pin telemetry around latest populated sample ({window_minutes}-min window: {start_str} → {end_str} UTC)...")
    table = client.get_aggregate(
        system_id,
        start=start_str,
        end=end_str,
        level="min",
        param="Pin",
        object_ids=object_ids,
    )

    if not table.rows:
        print("No telemetry rows returned in the latest populated window.")
        sys.exit(0)

    # Walk rows in reverse to find the most recent non-null value per panel
    latest: dict[int, tuple[datetime | None, float]] = {}
    id_str_map = {str(p["object_id"]): p["object_id"] for p in panels}
    for row in reversed(table.rows):
        for col, oid in id_str_map.items():
            if oid in latest:
                continue
            val = row.values.get(col)
            if isinstance(val, (int, float)):
                latest[oid] = (row.timestamp, float(val))
        if len(latest) == len(panels):
            break

    print(f"\n--- Per-Panel Power (most recent sample in latest populated {window_minutes}-min window) ---")
    header = f"{'Label':<12} {'Inverter':<14} {'String':<12} {'Power (W)':>10}  {'Timestamp (UTC)'}"
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
            print(f"  {panel['label']:<10} {panel['inverter']:<14} {panel['string']:<12} {power:>10.1f}  {ts_str}")
        else:
            missing.append(panel["label"])

    print(f"\n  Total power (reporting panels): {total_power:,.1f} W")
    if missing:
        print(f"  No data for {len(missing)} panel(s): {', '.join(missing)}")

    print("\nDone.")


if __name__ == "__main__":
    main()
