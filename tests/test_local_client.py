from pytigo.local_client import TigoCCAClient


class FakeResponse:
    def __init__(self, *, json_data=None, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self):
        self.auth = None
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        params = kwargs.get("params") or {}
        if url.endswith("/cgi-bin/summary_jsconfig"):
            return FakeResponse(json_data={"sDate": "2026-04-08"})
        if url.endswith("/cgi-bin/summary_config"):
            return FakeResponse(json_data=[
                {"id": "1", "type": 1, "label": "Local Site", "children": ["2"]},
                {"id": "2", "type": 4, "label": "Inverter 1", "children": ["3"]},
                {"id": "3", "type": 3, "label": "String A", "children": ["A1", "A2"]},
            ])
        if url.endswith("/cgi-bin/summary_energy"):
            return FakeResponse(json_data=[["2026-04-08", 1234]])
        if url.endswith("/cgi-bin/summary_data"):
            temp = params.get("temp")
            if temp in (None, "pin"):
                return FakeResponse(json_data={
                    "lastData": "2026-04-08 23:59:59.000",
                    "dataset": [
                        {
                            "order": ["A1", "A2"],
                            "data": [
                                {"t": "06:45", "d": [10, 20]},
                            ],
                        },
                        {
                            "order": ["A1", "A2"],
                            "data": [
                                {"t": "10:47", "d": [321, 320]},
                            ],
                        },
                    ],
                })
            if temp == "vin":
                return FakeResponse(json_data={
                    "lastData": "2026-04-08 23:59:59.000",
                    "dataset": [
                        {
                            "order": ["A1", "A2"],
                            "data": [
                                {"t": "06:45", "d": [330, 340]},
                            ],
                        },
                        {
                            "order": ["A1", "A2"],
                            "data": [
                                {"t": "10:47", "d": [321, 320]},
                            ],
                        },
                    ],
                })
            if temp == "rssi":
                return FakeResponse(json_data={
                    "lastData": "2026-04-08 23:59:59.000",
                    "dataset": [
                        {
                            "order": ["A1", "A2"],
                            "data": [
                                {"t": "10:47", "d": [150, 160]},
                            ],
                        }
                    ],
                })
            if temp in ("tmod", "tcell", "tamb", "power"):
                return FakeResponse(json_data={
                    "lastData": "2026-04-08 23:59:59.000",
                    "dataset": [
                        {
                            "order": ["A1", "A2"],
                            "data": [
                                {"t": "10:47", "d": [321, 320]},
                            ],
                        }
                    ],
                })
        raise AssertionError(f"Unexpected GET {url} params={params}")


def build_client() -> TigoCCAClient:
    session = FakeSession()
    client = TigoCCAClient(
        host="192.168.1.100",
        username="Tigo",
        password="$olar",
        session=session,
        enable_raw_temp_variants=True,
    )
    client.login()
    return client


def test_local_summary_uses_latest_dataset_segment():
    client = build_client()
    system = client.list_systems().items[0]
    original_utc_to_local = client._utc_to_local
    client._utc_to_local = lambda dt: __import__('datetime').datetime(2026, 4, 8, 12, 0)
    try:
        summary = client.get_summary(system.system_id)
    finally:
        client._utc_to_local = original_utc_to_local
    assert summary.daily_energy_dc == 1234.0
    assert summary.last_power_dc == 641.0
    assert str(summary.updated_on) == "2026-04-08 10:47:00"


def test_local_sources_use_latest_populated_row_for_last_checkin():
    client = build_client()
    system = client.list_systems().items[0]
    original_utc_to_local = client._utc_to_local
    client._utc_to_local = lambda dt: __import__('datetime').datetime(2026, 4, 8, 12, 0)
    try:
        sources = client.get_sources(system.system_id)
    finally:
        client._utc_to_local = original_utc_to_local
    assert len(sources) == 1
    assert str(sources[0].last_checkin) == "2026-04-08 10:47:00"


def test_local_summary_uses_device_date_and_keeps_zero_power():
    session = FakeSession()

    original_get = session.get
    def custom_get(url, **kwargs):
        params = kwargs.get('params') or {}
        if url.endswith('/cgi-bin/summary_data'):
            assert params.get('date') == '2026-04-08'
            if params.get('temp') in (None, 'pin'):
                return FakeResponse(json_data={
                    'lastData': '2026-04-08 23:59:59.000',
                    'dataset': [
                        {
                            'order': ['A1', 'A2'],
                            'data': [
                                {'t': '19:42', 'd': [0, 0]},
                            ],
                        }
                    ],
                })
        return original_get(url, **kwargs)

    session.get = custom_get
    client = TigoCCAClient(
        host='192.168.1.100',
        username='Tigo',
        password='$olar',
        session=session,
        enable_raw_temp_variants=True,
    )
    client.login()
    system = client.list_systems().items[0]

    original_utc_to_local = client._utc_to_local
    client._utc_to_local = lambda dt: __import__('datetime').datetime(2026, 4, 8, 20, 0)
    try:
        summary = client.get_summary(system.system_id)
    finally:
        client._utc_to_local = original_utc_to_local
    assert summary.daily_energy_dc == 1234.0
    assert summary.last_power_dc == 0.0
    assert str(summary.updated_on) == '2026-04-08 19:42:00'


def test_local_aggregate_merges_all_datasets_and_derives_iin():
    client = build_client()
    system = client.list_systems().items[0]

    pin = client.get_aggregate(system.system_id, start="2026-04-08T06:00:00", end="2026-04-08T11:00:00", param="Pin")
    assert len(pin.rows) == 2
    assert pin.rows[-1].values["1"] == 321.0
    assert pin.rows[-1].values["2"] == 320.0

    vin = client.get_aggregate(system.system_id, start="2026-04-08T06:00:00", end="2026-04-08T11:00:00", param="Vin")
    assert len(vin.rows) == 2
    assert vin.rows[-1].values["1"] == 32.1
    assert vin.rows[-1].values["2"] == 32.0

    iin = client.get_aggregate(system.system_id, start="2026-04-08T06:00:00", end="2026-04-08T11:00:00", param="Iin")
    assert len(iin.rows) == 2
    assert round(iin.rows[-1].values["1"], 2) == 10.0
    assert round(iin.rows[-1].values["2"], 2) == 10.0

    rssi = client.get_aggregate(system.system_id, start="2026-04-08T10:00:00", end="2026-04-08T11:00:00", param="RSSI")
    assert len(rssi.rows) == 1
    assert rssi.rows[-1].values["1"] == 150.0
    assert rssi.rows[-1].values["2"] == 160.0


def test_local_vin_auto_detects_direct_volts_without_scaling():
    session = FakeSession()

    original_get = session.get
    def custom_get(url, **kwargs):
        params = kwargs.get('params') or {}
        if url.endswith('/cgi-bin/summary_data') and params.get('temp') == 'vin':
            return FakeResponse(json_data={
                'lastData': '2026-04-08 23:59:59.000',
                'dataset': [
                    {
                        'order': ['A1', 'A2'],
                        'data': [
                            {'t': '11:43', 'd': [31, 30]},
                        ],
                    }
                ],
            })
        return original_get(url, **kwargs)

    session.get = custom_get
    client = TigoCCAClient(
        host='192.168.1.100',
        username='Tigo',
        password='$olar',
        session=session,
        enable_raw_temp_variants=True,
    )
    client.login()
    system = client.list_systems().items[0]

    vin = client.get_aggregate(system.system_id, start='2026-04-08T11:00:00', end='2026-04-08T12:00:00', param='Vin')
    assert len(vin.rows) == 1
    assert vin.rows[0].values['1'] == 31.0
    assert vin.rows[0].values['2'] == 30.0


def test_local_summary_uses_fresher_today_when_summary_jsconfig_date_is_stale():
    session = FakeSession()

    original_get = session.get
    def custom_get(url, **kwargs):
        params = kwargs.get('params') or {}
        if url.endswith('/cgi-bin/summary_jsconfig'):
            return FakeResponse(json_data={'sDate': '2026-04-08'})
        if url.endswith('/cgi-bin/summary_energy'):
            return FakeResponse(json_data=[['2026-04-08', 1234], ['2026-04-09', 1600]])
        if url.endswith('/cgi-bin/summary_data'):
            req_date = params.get('date')
            temp = params.get('temp')
            if req_date == '2026-04-08' and temp in (None, 'pin'):
                return FakeResponse(json_data={
                    'lastData': '2026-04-08 23:59:59.000',
                    'dataset': [
                        {'order': ['A1', 'A2'], 'data': [{'t': '20:43', 'd': [0, 0]}]},
                    ],
                })
            if req_date == '2026-04-09' and temp in (None, 'pin'):
                return FakeResponse(json_data={
                    'lastData': '2026-04-09 07:43:00.000',
                    'dataset': [
                        {'order': ['A1', 'A2'], 'data': [{'t': '07:43', 'd': [80, 70]}]},
                    ],
                })
        return original_get(url, **kwargs)

    session.get = custom_get
    client = TigoCCAClient(
        host='192.168.1.100',
        username='Tigo',
        password='$olar',
        session=session,
        enable_raw_temp_variants=True,
    )
    client.login()
    system = client.list_systems().items[0]

    original_utc_to_local = client._utc_to_local
    client._utc_to_local = lambda dt: __import__('datetime').datetime(2026, 4, 9, 7, 45)
    try:
        summary = client.get_summary(system.system_id)
    finally:
        client._utc_to_local = original_utc_to_local

    assert summary.daily_energy_dc == 1600.0
    assert summary.last_power_dc == 150.0
    assert str(summary.updated_on) == '2026-04-09 07:43:00'
