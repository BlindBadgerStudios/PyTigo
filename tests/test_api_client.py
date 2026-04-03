from pytigo.client import TigoClient

TEST_SYSTEM_ID = 424242

LOGIN_JSON = {
    "user": {
        "user_id": 7,
        "auth": "token-abc",
        "expires": "2026-09-29T21:18:00-07:00",
        "user_type": "Basic",
    }
}
USER_JSON = {"user": {"user_id": 7, "login": "user@example.com", "first_name": "Example", "last_name": "User", "email": "user@example.com"}}
SYSTEMS_JSON = {"systems": [{"system_id": TEST_SYSTEM_ID, "name": "Example Site", "zip": "75000", "created": "2024-08-29T14:45:43-07:00"}]}
SYSTEM_JSON = {"system": {"system_id": TEST_SYSTEM_ID, "name": "Example Site", "zip": "75000", "created": "2024-08-29T14:45:43-07:00"}}
LAYOUT_JSON = {"system": {"system_id": TEST_SYSTEM_ID, "inverters": []}}
OBJECTS_JSON = {"objects": []}
OBJECT_TYPES_JSON = {"object_types": [{"object_type_id": 1, "label": "System"}]}
SOURCES_JSON = {"sources": []}
SUMMARY_JSON = {"summary": {"daily_energy_dc": 123.4, "updated_on": "2026-03-31T19:28:00.000-07:00"}}
ALERTS_JSON = {"alerts": [{"alert_id": 1, "system_id": TEST_SYSTEM_ID, "unique_id": 106, "title": "Alert", "message": "Message", "description": "Desc"}]}
ALERT_TYPES_JSON = {"alert_types": [{"alert_type_id": 24, "title": "Type", "description": "Desc", "unique_id": 300}]}
CSV_TEXT = "Datetime,1\n2026/03/31 00:00:00,5\n"


class FakeResponse:
    def __init__(self, *, text="", json_data=None, status_code=200):
        self.text = text
        self._json = json_data
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
        self.calls.append((url, kwargs))
        if url.endswith('/users/login'):
            return FakeResponse(json_data=LOGIN_JSON)
        if url.endswith('/users/7'):
            return FakeResponse(json_data=USER_JSON)
        if url.endswith('/systems'):
            return FakeResponse(json_data=SYSTEMS_JSON)
        if url.endswith('/systems/view'):
            return FakeResponse(json_data=SYSTEM_JSON)
        if url.endswith('/systems/layout'):
            return FakeResponse(json_data=LAYOUT_JSON)
        if url.endswith('/objects/system'):
            return FakeResponse(json_data=OBJECTS_JSON)
        if url.endswith('/objects/types'):
            return FakeResponse(json_data=OBJECT_TYPES_JSON)
        if url.endswith('/sources/system'):
            return FakeResponse(json_data=SOURCES_JSON)
        if url.endswith('/data/summary'):
            return FakeResponse(json_data=SUMMARY_JSON)
        if url.endswith('/data/aggregate'):
            return FakeResponse(text=CSV_TEXT)
        if url.endswith('/data/combined'):
            return FakeResponse(text=CSV_TEXT)
        if url.endswith('/alerts/system'):
            return FakeResponse(json_data=ALERTS_JSON)
        if url.endswith('/alerts/types'):
            return FakeResponse(json_data=ALERT_TYPES_JSON)
        if url.endswith('/users/logout'):
            return FakeResponse(json_data={"status": 200, "message": "Logged out user"})
        raise AssertionError(f"Unexpected GET {url}")


def test_official_client_methods():
    session = FakeSession()
    client = TigoClient(username="user@example.com", password="secret", session=session)

    auth = client.login()
    assert auth.auth_token == "token-abc"
    assert client.get_current_user().email == "user@example.com"
    assert client.list_systems().items[0].system_id == TEST_SYSTEM_ID
    assert client.get_system(TEST_SYSTEM_ID).name == "Example Site"
    assert client.get_layout(TEST_SYSTEM_ID).system_id == TEST_SYSTEM_ID
    assert client.get_objects(TEST_SYSTEM_ID) == []
    assert client.get_object_types()[0].label == "System"
    assert client.get_sources(TEST_SYSTEM_ID) == []
    assert client.get_summary(TEST_SYSTEM_ID).daily_energy_dc == 123.4
    assert client.get_aggregate(TEST_SYSTEM_ID, start="2026-03-31T00:00:00", end="2026-03-31T23:59:59").rows[0].values["1"] == 5.0
    assert client.get_combined(TEST_SYSTEM_ID, start="2026-03-31T00:00:00", end="2026-03-31T23:59:59", agg="day").rows[0].values["1"] == 5.0
    assert client.get_alerts(TEST_SYSTEM_ID).items[0].unique_id == 106
    assert client.get_alert_types()[0].unique_id == 300
    assert client.logout()["status"] == 200
    assert client.auth is None

    login_call = session.calls[0]
    assert login_call[0].endswith('/users/login')
    assert login_call[1]["auth"] == ("user@example.com", "secret")
