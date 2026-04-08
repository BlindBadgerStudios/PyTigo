"""
Probe a local Tigo CCA and report which local endpoints are available.

Usage:
    TIGO_LOCAL_HOST=192.168.1.100 python examples/local_cca_endpoints.py

Optional env vars:
    TIGO_LOCAL_USERNAME -- CCA username (default: Tigo)
    TIGO_LOCAL_PASSWORD -- CCA password (default: $olar)
    TIGO_LOCAL_DATE     -- date for summary_data/temp probes (default: device date if available, else today UTC)
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

import requests
from requests.auth import HTTPBasicAuth

UTC = timezone.utc


def _preview(text: str, limit: int = 140) -> str:
    text = " ".join(text.split())
    return text[:limit]


def main() -> None:
    host = os.environ.get("TIGO_LOCAL_HOST")
    if not host:
        print("ERROR: set TIGO_LOCAL_HOST to the CCA device IP or hostname")
        sys.exit(1)

    username = os.environ.get("TIGO_LOCAL_USERNAME", "Tigo")
    password = os.environ.get("TIGO_LOCAL_PASSWORD", "$olar")
    auth = HTTPBasicAuth(username, password)
    base = f"http://{host}"

    device_date = None
    try:
        r = requests.get(f"{base}/cgi-bin/summary_jsconfig", auth=auth, timeout=15)
        r.raise_for_status()
        device_date = r.json().get("sDate")
    except Exception:
        pass

    probe_date = os.environ.get("TIGO_LOCAL_DATE") or device_date or datetime.now(tz=UTC).strftime("%Y-%m-%d")

    endpoint_paths = [
        "/cgi-bin/summary",
        "/summary/",
        "/cgi-bin/summary_jsconfig",
        "/cgi-bin/summary_config",
        "/cgi-bin/summary_energy",
        f"/cgi-bin/summary_data?date={probe_date}",
        "/cgi-bin/info",
        "/cgi-bin/network",
    ]

    print(f"Probing local CCA at {host} with date={probe_date}\n")
    print("Endpoint status:")
    for path in endpoint_paths:
        url = f"{base}{path}"
        try:
            response = requests.get(url, auth=auth, timeout=15)
            body = response.text or ""
            print(f"- {path}: {response.status_code} {response.headers.get('Content-Type')}")
            if body:
                print(f"  preview: {_preview(body)}")
        except Exception as exc:
            print(f"- {path}: ERROR {type(exc).__name__}: {exc}")

    print("\nTemp variant probes for /cgi-bin/summary_data:")
    for temp in ["pin", "vin", "rssi", "iin", "tmod", "tcell", "tamb", "power", "temp"]:
        url = f"{base}/cgi-bin/summary_data"
        try:
            response = requests.get(url, params={"date": probe_date, "temp": temp}, auth=auth, timeout=20)
            body = response.text or ""
            print(f"- temp={temp}: {response.status_code} {response.headers.get('Content-Type')} bytes={len(body)}")
            if response.ok and body:
                payload = response.json()
                datasets = payload.get("dataset", [])
                last_data = payload.get("lastData")
                first_order = datasets[0].get("order", [])[:5] if datasets else []
                print(f"  lastData={last_data} datasets={len(datasets)} first_order={first_order}")
            elif response.ok:
                print("  empty 200 response")
        except Exception as exc:
            print(f"- temp={temp}: ERROR {type(exc).__name__}: {exc}")

    print("\nNotes:")
    print("- summary_jsconfig/config/energy/data are the verified local data endpoints with current credentials.")
    print("- /cgi-bin/info and /cgi-bin/network currently return Access Denied with these credentials.")
    print("- Re-check info/network in the future if higher-privilege credentials become available.")


if __name__ == "__main__":
    main()
