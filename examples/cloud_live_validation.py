"""
Live validation for the official Tigo cloud API v3.

This script is intended to verify that the cloud integration still works end-to-end
against a real account, while explicitly reporting the known aggregate/combined
limitation observed on some systems.

Usage:
    TIGO_USERNAME=you@example.com TIGO_PASSWORD=*** python examples/cloud_live_validation.py

Optional env vars:
    TIGO_SYSTEM_ID   -- integer system ID to query (defaults to first system on account)
    TIGO_WINDOW_MIN  -- aggregate/combined validation window in minutes (default: 30)
"""

from __future__ import annotations

import os
import sys
import time
from datetime import UTC, datetime, timedelta

import requests

from pytigo import TigoClient


def _format_ok(ok: bool) -> str:
    return "OK" if ok else "FAIL"


def _retry_cloud_call(label: str, fn, retries: int = 4, base_sleep: int = 5):
    for attempt in range(1, retries + 1):
        try:
            return fn(), None, attempt
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            body = exc.response.text[:300] if exc.response is not None and exc.response.text else ""
            if status == 429 and attempt < retries:
                time.sleep(base_sleep * attempt)
                continue
            return None, f"HTTP {status}: {body}", attempt
        except Exception as exc:
            return None, f"{type(exc).__name__}: {exc}", attempt
    return None, "unknown error", retries


def main() -> None:
    username = os.environ.get("TIGO_USERNAME")
    password = os.environ.get("TIGO_PASSWORD")
    if not username or not password:
        print("ERROR: set TIGO_USERNAME and TIGO_PASSWORD environment variables")
        sys.exit(1)

    system_id_env = os.environ.get("TIGO_SYSTEM_ID")
    window_minutes = int(os.environ.get("TIGO_WINDOW_MIN", "30"))

    client = TigoClient(username=username, password=password, timeout=30)

    print("Cloud API live validation")
    print("=========================")

    auth = client.login()
    print(f"login: {_format_ok(True)}  user_id={auth.user_id} user_type={auth.user_type} expires={auth.expires}")

    page = client.list_systems()
    if not page.items:
        print("list_systems: FAIL  no systems found")
        sys.exit(1)
    system = client.get_system(int(system_id_env)) if system_id_env else page.items[0]
    system_id = system.system_id
    print(f"list_systems: {_format_ok(True)}  count={len(page.items)} selected_system={system_id} name={system.name!r}")

    system_detail = client.get_system(system_id)
    print(f"get_system: {_format_ok(True)}  timezone={system_detail.timezone} status={system_detail.status}")

    layout = client.get_layout(system_id)
    panel_object_ids: list[int] = []
    panel_count = 0
    for inverter in layout.inverters:
        for mppt in inverter.mppts:
            for string in mppt.strings:
                for panel in string.panels:
                    panel_count += 1
                    if panel.object_id is not None:
                        panel_object_ids.append(panel.object_id)
    print(f"get_layout: {_format_ok(True)}  inverters={len(layout.inverters)} panels={panel_count} panels_with_object_ids={len(panel_object_ids)}")

    objects = client.get_objects(system_id)
    print(f"get_objects: {_format_ok(True)}  count={len(objects)}")

    sources = client.get_sources(system_id)
    first_source = sources[0] if sources else None
    print(
        f"get_sources: {_format_ok(True)}  count={len(sources)}"
        + (f" first_last_checkin={first_source.last_checkin} panel_count={first_source.panel_count}" if first_source else "")
    )

    summary = client.get_summary(system_id)
    print(
        f"get_summary: {_format_ok(True)}  last_power_dc={summary.last_power_dc}"
        f" daily_energy_dc={summary.daily_energy_dc} updated_on={summary.updated_on}"
    )

    alerts = client.get_alerts(system_id, limit=5)
    print(f"get_alerts: {_format_ok(True)}  items={len(alerts.items)} total={alerts.total}")

    alert_types = client.get_alert_types()
    print(f"get_alert_types: {_format_ok(True)}  count={len(alert_types)}")

    end = datetime.now(UTC).replace(microsecond=0)
    start = end - timedelta(minutes=window_minutes)
    start_s = start.strftime("%Y-%m-%dT%H:%M:%S")
    end_s = end.strftime("%Y-%m-%dT%H:%M:%S")
    subset = panel_object_ids[:3]

    agg, agg_err, agg_attempt = _retry_cloud_call(
        "aggregate",
        lambda: client.get_aggregate(
            system_id,
            start=start_s,
            end=end_s,
            level="min",
            param="Pin",
            object_ids=subset or None,
            header="id",
        ),
    )
    if agg is None:
        print(f"get_aggregate: FAIL  attempts={agg_attempt}  {agg_err}")
    else:
        value_headers = [h for h in agg.headers if h != "Datetime"]
        limited = len(value_headers) == 0
        print(
            f"get_aggregate: {_format_ok(True)}  attempts={agg_attempt} rows={len(agg.rows)} headers={agg.headers[:10]}"
        )
        if limited:
            print("  NOTE: aggregate returned only 'Datetime' with no value columns. This is a known live limitation on some systems/accounts.")
        else:
            print(f"  value_headers={value_headers[:10]}")

    comb, comb_err, comb_attempt = _retry_cloud_call(
        "combined",
        lambda: client.get_combined(
            system_id,
            start=start_s,
            end=end_s,
            agg="min",
            object_ids=subset or None,
        ),
    )
    if comb is None:
        print(f"get_combined: FAIL  attempts={comb_attempt}  {comb_err}")
    else:
        value_headers = [h for h in comb.headers if h != "Datetime"]
        limited = len(value_headers) == 0
        print(
            f"get_combined: {_format_ok(True)}  attempts={comb_attempt} rows={len(comb.rows)} headers={comb.headers[:10]}"
        )
        if limited:
            print("  NOTE: combined returned only 'Datetime' with no value columns. This is a known live limitation on some systems/accounts.")
        else:
            print(f"  value_headers={value_headers[:10]}")

    client.logout()
    print("logout: OK")
    print("\nValidation complete.")


if __name__ == "__main__":
    main()
