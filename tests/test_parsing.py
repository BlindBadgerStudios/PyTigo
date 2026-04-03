from datetime import date
import json

from pytigo.client import TigoClient
from pytigo.models import TigoSystemTopology
from pytigo.parsing import (
    extract_csrf_token,
    extract_default_system_id,
    parse_daily_energy,
    parse_info_page,
    parse_overview_page,
    parse_range_data,
    parse_summary,
    parse_system_topology,
)

LOGIN_HTML = '''
<html><body>
<form>
<input type="hidden" name="_csrf" value="csrf-token-123" />
</form>
</body></html>
'''

OVERVIEW_HTML = r'''
<html><head><title>131225 - Overview</title></head><body>
<script>
var GLOBALTIGONOCONFLICT = {"systemId":131225,"nodeAggregateUrl":"https:\/\/ei.tigoenergy.com\/api\/v4\/data\/aggregate","nodeSystemViewUrl":"\/api\/v4\/systems\/view\/131225","dataLifetimeUrl":"\/api\/v4\/fleet\/system\/overview\/data-lifetime","weatherUrl":"\/fleet\/system\/overview\/data-weather?sysid=131225","basicChartsUrl":"\/system\/charts?sysid=131225","mapOptions":{"center":["47.74632339999999","-117.4407446"]},"chart":{"baseUrl":"\/api\/v4\/data\/aggregate","oldUrl":"\/system\/overview\/e-chart-handler","system_id":131225,"agg":"hour","view":"gen","startDate":"2026-04-02","endDate":"2026-04-02","firstDate":"2024-08-29","lastDate":"2026-04-02","hasPremium":true,"hasReclaimed":true,"hasBasic":false},"tabOptions":["solar"],"calendar":{"numRestrictedWeeks":0,"numRestrictedMonths":0,"numRestrictedYears":0,"url":"\/data\/daily-energy?sysid=131225","timezone":"America\/Los_Angeles","startDate":"2024-08-29","endDate":"2026-03-31"},"settingsUrl":"\/fleet\/system\/settings\/general?sysid=131225","NODE_URI":"\/api\/v4"};
</script>
</body></html>
'''

INFO_HTML = '''
<html><body>
System
System Name
Example Solar Home
ID
131225
Install Date
2024-09-24
Peak Power
21.93 kW
Location
123 Example Rd
Spokane
WA 99208
Cloud Connect Advanced
Name
Serial
Check In
Example CCA
SERIAL123
4 minutes ago
Inverters
Serial
Label
Model
Manufacturer
Max Power
-
Inverter A
15k Limitless
Sol-Ark
15 kW
-
Inverter B
15k Limitless
Sol-Ark
15 kW
Modules
Model
Manufacturer
Max Power
Count
SIL 430
Silfab
430 W
51
</body></html>
'''

CONFIG_EDITOR_JSON = {
    "system": {
        "object_labels": {
            "1": "System",
            "2": "Panel",
            "3": "String",
            "4": "Inverter",
            "44": "Cloud Connect"
        },
        "objects": [
            {"A": 1, "B": 1, "C": "Total Production", "K": -1},
            {"A": 2, "B": 44, "C": "Example CCA", "K": 1, "T": "SERIAL123"},
            {"A": 3, "B": 4, "C": "Inverter A", "K": 1, "J": 15000},
            {"A": 4, "B": 3, "C": "String A", "K": 3},
            {"A": 5, "B": 2, "C": "A1", "K": 4, "J": 430, "M": 50, "L": 130, "T": "OPT-A1", "V": "MAC-A1"},
            {"A": 6, "B": 2, "C": "A2", "K": 4, "J": 430, "M": 100, "L": 130, "T": "OPT-A2", "V": "MAC-A2"}
        ],
        "wifi_channels": [1, 6, 11],
        "optimizer_types": ["39"]
    }
}

DAILY_ENERGY_JSON = {
    "2024-08-29": 11136.59,
    "2024-08-30": 61861.3,
    "2024-08-31": 30546.05,
}

SUMMARY_JSON = {
    "lastData": "2026-03-31T18:58",
    "currentDate": "2026-04-02",
    "dataDate": "2026-03-31",
    "dataType": "pin",
    "dataset": [],
    "dailyStats": {
        "total_agg_energy": "6541.183333333334",
        "total_agg_reclaimed": "71929.55593000000374"
    }
}

RANGE_JSON = {
    "o": {
        "y_title": "Wh",
        "date_range": "04/02/2026",
        "chart_title": "04/02/2026",
        "x_title": "04/02/2026 (Hours)",
        "has_premium": {"131225": True},
        "has_basic": {"131225": False},
        "last_data_timestamp": {"131225": "2026-03-31 18:58:00"},
        "is_premium_restricted": False,
    },
    "c": ["2026-04-02T00:00:00", "2026-04-02T01:00:00"],
    "p": None,
    "s": [{"i": "87488188", "n": "Total Energy", "v": [0, 1200.5], "p": [], "t": None, "u": "Wh"}],
}


def test_extract_login_artifacts():
    assert extract_csrf_token(LOGIN_HTML) == "csrf-token-123"
    assert extract_default_system_id("https://ei.tigoenergy.com/fleet/system/overview/index?system_id=131225") == 131225


def test_parse_overview_page():
    overview = parse_overview_page(OVERVIEW_HTML)
    assert overview.system_id == 131225
    assert overview.calendar_url == "/data/daily-energy?sysid=131225"
    assert overview.chart_view == "gen"
    assert overview.timezone == "America/Los_Angeles"


def test_parse_info_page():
    info = parse_info_page(INFO_HTML)
    assert info.system_name == "Example Solar Home"
    assert info.system_id == 131225
    assert info.location == ["123 Example Rd", "Spokane", "WA 99208"]
    assert info.cloud_connect.name == "Example CCA"
    assert info.cloud_connect.serial == "SERIAL123"
    assert len(info.inverters) == 2
    assert info.module_summary.count == 51


def test_parse_system_topology():
    topology = parse_system_topology(CONFIG_EDITOR_JSON)
    assert isinstance(topology, TigoSystemTopology)
    assert topology.root.name == "Total Production"
    assert len(topology.panels) == 2
    assert topology.panels[0].serial == "OPT-A1"
    assert topology.panels[0].mac == "MAC-A1"
    assert topology.inverters[0].name == "Inverter A"
    assert topology.strings[0].name == "String A"


def test_parse_energy_payloads():
    daily = parse_daily_energy(DAILY_ENERGY_JSON)
    assert daily[0].date == date(2024, 8, 29)
    assert daily[1].energy_wh == 61861.3

    summary = parse_summary(SUMMARY_JSON)
    assert summary.total_agg_energy_wh == 6541.183333333334
    assert summary.total_agg_reclaimed_wh == 71929.55593

    range_data = parse_range_data(RANGE_JSON)
    assert range_data.unit == "Wh"
    assert range_data.categories[1].hour == 1
    assert range_data.series[0].values == [0, 1200.5]


class FakeResponse:
    def __init__(self, text="", json_data=None, url="https://ei.tigoenergy.com/", status_code=200):
        self.text = text
        self._json = json_data
        self.url = url
        self.status_code = status_code

    def json(self):
        if self._json is not None:
            return self._json
        return json.loads(self.text)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self):
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        if url.endswith("/"):
            return FakeResponse(text=LOGIN_HTML, url=url)
        if "overview/index" in url:
            return FakeResponse(text=OVERVIEW_HTML, url=url)
        if "info/index" in url:
            return FakeResponse(text=INFO_HTML, url=url)
        if "config/editor" in url:
            return FakeResponse(json_data=CONFIG_EDITOR_JSON, url=url)
        if "data/daily-energy" in url:
            return FakeResponse(json_data=DAILY_ENERGY_JSON, url=url)
        if "data/summary" in url:
            return FakeResponse(json_data=SUMMARY_JSON, url=url)
        if "data/range-data" in url:
            return FakeResponse(json_data=RANGE_JSON, url=url)
        raise AssertionError(f"Unexpected GET {url}")

    def post(self, url, data=None, **kwargs):
        self.calls.append(("POST", url, {"data": data, **kwargs}))
        if "site/login" in url:
            return FakeResponse(text="", url="https://ei.tigoenergy.com/fleet/system/overview/index?system_id=131225")
        raise AssertionError(f"Unexpected POST {url}")


def test_client_login_and_fetch_methods():
    client = TigoClient(email="user@example.com", password="secret", session=FakeSession())
    system_id = client.login()

    assert system_id == 131225
    assert client.default_system_id == 131225
    assert client.get_overview().system_id == 131225
    assert client.get_system_info().system_name == "Example Solar Home"
    assert client.get_system_topology().panels[1].name == "A2"
    assert client.get_daily_energy()[2].energy_wh == 30546.05
    assert client.get_summary().total_agg_energy_wh == 6541.183333333334
    assert client.get_range_data().series[0].name == "Total Energy"
