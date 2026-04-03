from datetime import date, datetime
import json

from pytigo import TigoClient
from pytigo.parsing import (
    parse_advanced_data,
    parse_alerts_page,
    parse_date_info,
    parse_minute_data,
    parse_system_view_page,
)

TEST_SYSTEM_ID = 424242

DATE_INFO_JSON = {
    "2026-03-31": {
        "sunrise": 23.45,
        "sunset": 12.316666666666666,
        "sunrise_time": "23:27",
        "sunset_time": "12:19",
        "light": 21.683333333333334,
        "dark": 14.1,
        "timezone": "America/Chicago",
    }
}

MINUTE_DATA_JSON = {
    "lastData": "2026-03-31 18:58:00",
    "dataDate": "2026-03-31 20:26:35",
    "dataType": "pin",
    "sunrise": 23.45,
    "sunset": 12.316666666667,
    "light": 21.683333333333,
    "dark": 14.1,
    "dataset": [],
}

ADVANCED_JSON = {
    "s": [
        {
            "h": ["A1_Pin", "A2_Pin", "A3_Pin"]
        }
    ]
}

VIEW_HTML = rf'''
<html><body>
<script>
var arrayConfig = {{"hasMonitoredModules":true,"date":"2026-03-31 19:21:33","latest":"2026-03-31 19:21:33","minutes":null,"channel":"energy","timeframe":1,"timezone":"America\/Chicago","display":1,"sun_direction":-1,"has_basic":false,"first_day":"2024-08-29 14:45:43.169598","last_day_with_data":"2026-03-31 18:58:00"}};
    var config_url  = "\/config\/array?sysid={TEST_SYSTEM_ID}";
    var rangedata_url    = "\/data\/range-data?sysid={TEST_SYSTEM_ID}";
    var monthdata_url    = "\/data\/calendar-optimized?sysid={TEST_SYSTEM_ID}";
    var dateinfo_url = "\/data\/date-info?sysid={TEST_SYSTEM_ID}";
    var minutedata_url   = "\/data\/minute-data?sysid={TEST_SYSTEM_ID}";
    var datedata_url = "\/data\/summary?sysid={TEST_SYSTEM_ID}";
    var aggEnergyUrl = "\/data\/agg-energy?sysid={TEST_SYSTEM_ID}";
    var chartdownload_url = "\/data\/advanced?sysid={TEST_SYSTEM_ID}";
    var urgent_url  = "\/data\/urgent?sysid={TEST_SYSTEM_ID}";
    var background_update_url = "/system/summary/background?sysid={TEST_SYSTEM_ID}";
var GLOBALTIGONOCONFLICT = {{"is_mobile":false,"data_api":"\/api\/v4"}};
</script>
</body></html>
'''

ALERTS_HTML = rf'''
<html><body>
<script>
var csrf_param  = "_csrf";var csrf_token="token-123";var sysid  = "{TEST_SYSTEM_ID}";
var ALERTSNOCONFLICT = {{"detail_url":"\/system\/alerts\/detail?sysid={TEST_SYSTEM_ID}","archive_url":"\/system\/alerts\/archive"}};
var TIGO_ALERTS = [];
</script>
Alerts
Edit Alerts
Download Alerts
No alerts for this system
</body></html>
'''


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
            return FakeResponse(text='<input type="hidden" name="_csrf" value="csrf-token-123" />', url=url)
        if "data/date-info" in url:
            return FakeResponse(json_data=DATE_INFO_JSON, url=url)
        if "data/minute-data" in url:
            return FakeResponse(json_data=MINUTE_DATA_JSON, url=url)
        if "data/advanced" in url:
            return FakeResponse(json_data=ADVANCED_JSON, url=url)
        if "fleet/system/view/index" in url:
            return FakeResponse(text=VIEW_HTML, url=url)
        if "fleet/system/alerts/index" in url:
            return FakeResponse(text=ALERTS_HTML, url=url)
        raise AssertionError(f"Unexpected GET {url}")

    def post(self, url, data=None, **kwargs):
        self.calls.append(("POST", url, {"data": data, **kwargs}))
        if "site/login" in url:
            return FakeResponse(text="", url=f"https://ei.tigoenergy.com/fleet/system/overview/index?system_id={TEST_SYSTEM_ID}")
        raise AssertionError(f"Unexpected POST {url}")


def test_parse_date_info():
    parsed = parse_date_info(DATE_INFO_JSON)
    assert parsed.date == date(2026, 3, 31)
    assert parsed.timezone == "America/Chicago"
    assert parsed.sunrise_time == "23:27"


def test_parse_minute_data():
    parsed = parse_minute_data(MINUTE_DATA_JSON)
    assert parsed.last_data == datetime(2026, 3, 31, 18, 58, 0)
    assert parsed.data_type == "pin"
    assert parsed.dataset == []


def test_parse_advanced_data():
    parsed = parse_advanced_data(ADVANCED_JSON)
    assert parsed.headers == ["A1_Pin", "A2_Pin", "A3_Pin"]


def test_parse_system_view_page():
    parsed = parse_system_view_page(VIEW_HTML)
    assert parsed.timezone == "America/Chicago"
    assert parsed.date_info_url == f"/data/date-info?sysid={TEST_SYSTEM_ID}"
    assert parsed.advanced_data_url == f"/data/advanced?sysid={TEST_SYSTEM_ID}"


def test_parse_alerts_page():
    parsed = parse_alerts_page(ALERTS_HTML)
    assert parsed.system_id == TEST_SYSTEM_ID
    assert parsed.detail_url == f"/system/alerts/detail?sysid={TEST_SYSTEM_ID}"
    assert parsed.no_alerts is True


def test_client_endpoint_helpers():
    client = TigoClient(email="user@example.com", password="secret", session=FakeSession())
    client.login()

    assert client.get_date_info("2026-03-31").timezone == "America/Chicago"
    assert client.get_minute_data("2026-03-31", minute="12:00").data_type == "pin"
    assert client.get_advanced_data("2026-03-31").headers[0] == "A1_Pin"
    assert client.get_system_view().channel == "energy"
    assert client.get_alerts_metadata().no_alerts is True
