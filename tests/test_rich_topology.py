from pytigo import TigoClient
from pytigo.parsing import (
    parse_agg_energy,
    parse_calendar_optimized,
    parse_status_page,
    parse_system_inventory,
)

TEST_SYSTEM_ID = 424242

CONFIG_EDITOR_JSON = {
    "system": {
        "object_labels": {
            "1": "System",
            "2": "Panel",
            "3": "String",
            "4": "Inverter",
            "10": "Line",
            "22": "Gateway",
            "44": "Cloud Connect",
            "67": "Temperature",
            "69": "Panel RSSI",
            "71": "Energy",
        },
        "objects": [
            {"A": 1, "B": 1, "C": "Example Site", "K": -1, "M": 50, "L": 100},
            {"A": 2, "B": 44, "C": "Gateway CCA", "K": 1, "U": 119515, "T": "CCA-SERIAL", "M": 15, "L": 15},
            {"A": 3, "B": 4, "C": "Inverter A", "K": 1, "J": 15000, "U": 233085},
            {"A": 4, "B": 3, "C": "String A", "K": 3, "U": 526489},
            {"A": 5, "B": 2, "C": "A1", "K": 4, "J": 430, "M": 50, "L": 130, "N": "CCA-SERIAL", "V": "MAC-A1", "U": 6783349, "T": "OPT-A1", "S": 39, "X": 1, "Z": False, "W": 5, "P": 0},
            {"A": 6, "B": 2, "C": "A2", "K": 4, "J": 430, "M": 100, "L": 130, "N": "CCA-SERIAL", "V": "MAC-A2", "U": 6783350, "T": "OPT-A2", "S": 39, "X": 1, "Z": False, "W": 6, "P": 0},
        ],
        "wifi_channels": ["CCA-SERIAL.17"],
        "optimizer_types": {
            "39": {"id": 39, "model": "TS4-A-O", "cover_type": 4}
        },
    }
}

STATUS_HTML = rf'''
<html><body>
<script>
var GLOBALTIGONOCONFLICT = {{"NODE_URI":"\/api\/v4","systemId":{TEST_SYSTEM_ID}}};
</script>
Equipment Status
Gateway CCA
Last check in 4 minutes ago
Inverter A
Normal
Panels online 2
</body></html>
'''

CALENDAR_OPTIMIZED_JSON = [
    ["2026-03-29", 101.5],
    ["2026-03-30", 202.5],
]

AGG_ENERGY_JSON = {
    "system_id": TEST_SYSTEM_ID,
    "dataDate": "2026-03-31",
    "dataType": "energy",
    "dataset": [1.0, 2.0, 3.0],
    "lastData": "2026-03-31 18:58:00",
}


class FakeResponse:
    def __init__(self, json_data=None, text="", url="https://ei.tigoenergy.com/", status_code=200):
        self._json = json_data
        self.text = text
        self.url = url
        self.status_code = status_code

    def json(self):
        return self._json

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
        if "config/editor" in url:
            return FakeResponse(json_data=CONFIG_EDITOR_JSON, url=url)
        if "fleet/system/status/index" in url:
            return FakeResponse(text=STATUS_HTML, url=url)
        if "data/calendar-optimized" in url:
            return FakeResponse(json_data=CALENDAR_OPTIMIZED_JSON, url=url)
        if "data/agg-energy" in url:
            return FakeResponse(json_data=AGG_ENERGY_JSON, url=url)
        raise AssertionError(f"Unexpected GET {url}")

    def post(self, url, data=None, **kwargs):
        self.calls.append(("POST", url, kwargs))
        if "site/login" in url:
            return FakeResponse(text="", url=f"https://ei.tigoenergy.com/fleet/system/overview/index?system_id={TEST_SYSTEM_ID}")
        raise AssertionError(f"Unexpected POST {url}")


def test_parse_system_inventory():
    inventory = parse_system_inventory(CONFIG_EDITOR_JSON)
    assert inventory.system_name == "Example Site"
    assert inventory.gateway.serial == "CCA-SERIAL"
    assert inventory.gateway.wifi_channels == ["CCA-SERIAL.17"]
    assert len(inventory.panels) == 2
    assert inventory.panels[0].string_name == "String A"
    assert inventory.panels[0].inverter_name == "Inverter A"
    assert inventory.panels[0].gateway_serial == "CCA-SERIAL"
    assert inventory.panels[0].optimizer_model == "TS4-A-O"
    assert inventory.panels[0].layout_x == 50
    assert inventory.panels[0].layout_y == 130


def test_parse_status_page():
    status = parse_status_page(STATUS_HTML)
    assert status.system_id == TEST_SYSTEM_ID
    assert status.has_equipment_status is True
    assert "Gateway CCA" in status.tokens


def test_parse_calendar_and_agg_energy():
    cal = parse_calendar_optimized(CALENDAR_OPTIMIZED_JSON)
    assert cal[0].energy_wh == 101.5
    agg = parse_agg_energy(AGG_ENERGY_JSON)
    assert agg.system_id == TEST_SYSTEM_ID
    assert agg.dataset == [1.0, 2.0, 3.0]


def test_client_rich_methods():
    client = TigoClient(email="user@example.com", password="secret", session=FakeSession())
    client.login()
    inventory = client.get_system_inventory()
    assert inventory.gateway.name == "Gateway CCA"
    assert client.get_status().has_equipment_status is True
    assert client.get_calendar_optimized()[1].energy_wh == 202.5
    assert client.get_agg_energy("2026-03-31").last_data is not None
