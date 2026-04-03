from datetime import date, datetime

from pytigo.parsing import (
    parse_csv_table,
    parse_layout_response,
    parse_login_response,
    parse_object_types_response,
    parse_objects_response,
    parse_sources_response,
    parse_summary_response,
    parse_system_response,
    parse_systems_response,
    parse_user_response,
)

LOGIN_JSON = {
    "user": {
        "user_id": 7,
        "auth": "token-abc",
        "expires": "2026-09-29T21:18:00-07:00",
        "user_type": "Basic",
        "refresh_token": "refresh-xyz",
        "user_agreement": True,
    }
}

USER_JSON = {
    "user": {
        "user_id": 7,
        "login": "user@example.com",
        "first_name": "Example",
        "last_name": "User",
        "email": "user@example.com",
        "company": "Example Co",
        "street": "123 Example St",
        "street2": None,
        "city": "Exampletown",
        "state": "TX",
        "zip": "75000",
        "country": "United States",
        "mobile": "1231231234",
        "user_type": "Basic",
        "avatar": None,
    }
}

SYSTEMS_JSON = {
    "systems": [
        {
            "system_id": 424242,
            "external_id": None,
            "name": "Example Site",
            "street": "123 Example St",
            "city": "Exampletown",
            "state": "TX",
            "zip": "75000",
            "country": "United States",
            "country_code": "US",
            "latitude": "35.0",
            "longitude": "-100.0",
            "timezone": "America/Chicago",
            "power_rating": 12000,
            "power_rating_ac": None,
            "created": "2024-08-29T14:45:43-07:00",
            "commissioned": "2024-09-24T00:00:00-07:00",
            "decommissioned": None,
            "status": "Active",
            "turn_on_date": "2024-09-24",
            "recent_alerts_count": 0,
            "has_monitored_modules": True,
        }
    ]
}

SYSTEM_JSON = {"system": SYSTEMS_JSON["systems"][0]}

LAYOUT_JSON = {
    "system": {
        "system_id": 424242,
        "inverters": [
            {
                "inverter_id": 11,
                "inverter_type_id": 22,
                "label": "Inverter A",
                "object_id": 100,
                "source_id": 200,
                "serial": "INV-ABC",
                "mppts": [
                    {
                        "mppt_id": 33,
                        "label": "MPPT 1",
                        "strings": [
                            {
                                "string_id": 44,
                                "label": "String A",
                                "short_label": "A",
                                "object_id": 101,
                                "panels": [
                                    {
                                        "panel_id": 55,
                                        "label": "A1",
                                        "short_label": 1,
                                        "serial": "OPT-A1",
                                        "type": "TS4-A-O-700W",
                                        "source_id": 200,
                                        "object_id": 102,
                                        "panel_type_id": 66,
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        ],
    }
}

OBJECTS_JSON = {
    "objects": [
        {
            "id": 1,
            "label": "System",
            "object_type_id": 1,
            "parent_id": -1,
            "datasource": None,
            "children": [2],
            "ui": {"X": 100, "Y": 200, "MP": 5000},
        },
        {
            "id": 2,
            "label": "A1",
            "object_type_id": 2,
            "parent_id": 1,
            "datasource": "SOURCE.panels.A1",
            "children": [],
            "ui": {"X": 150, "Y": 250, "MP": 430, "OP": 1},
        },
    ]
}

OBJECT_TYPES_JSON = {
    "object_types": [
        {"object_type_id": 1, "label": "System"},
        {"object_type_id": 2, "label": "Panel"},
    ]
}

SOURCES_JSON = {
    "sources": [
        {
            "source_id": 200,
            "name": "Example CCA",
            "serial": "SOURCE-1",
            "gateway_count": 1,
            "created_on": "2024-07-29T16:19:26-07:00",
            "control_state": "on",
            "last_checkin": "2026-02-16T23:19:06-08:00",
            "timezone": "America/Chicago",
            "sw_version": "ffs-2.4.0-image.img",
            "sets": [
                {
                    "set_name": "panels_avg",
                    "last_raw": "2026-03-20T16:43:00-07:00",
                    "last_min": "2026-03-31T18:58:00-07:00",
                    "last_day": "2026-02-14T00:00:00-08:00",
                }
            ],
            "system_id": 424242,
            "object_id": 999,
            "panel_count": 51,
            "unit_type_id": 8,
            "is_discovery_complete": True,
        }
    ]
}

SUMMARY_JSON = {
    "summary": {
        "lifetime_energy_dc": 40918712.12,
        "ytd_energy_dc": 4114728.35,
        "daily_energy_dc": 105885.47,
        "last_power_dc": 1,
        "updated_on": "2026-03-31T19:28:00.000-07:00",
    }
}

CSV_TEXT = "Datetime,1,2\n2026/03/31 00:00:00,2078.8,2069.77\n2026/03/31 00:01:00,,2060\n"


def test_parse_login_and_user():
    auth = parse_login_response(LOGIN_JSON)
    assert auth.user_id == 7
    assert auth.auth_token == "token-abc"
    assert auth.user_type == "Basic"

    user = parse_user_response(USER_JSON)
    assert user.email == "user@example.com"
    assert user.city == "Exampletown"


def test_parse_systems_and_system():
    systems = parse_systems_response(SYSTEMS_JSON)
    assert len(systems) == 1
    assert systems[0].system_id == 424242
    assert systems[0].turn_on_date == date(2024, 9, 24)

    system = parse_system_response(SYSTEM_JSON)
    assert system.name == "Example Site"
    assert system.timezone == "America/Chicago"


def test_parse_layout_objects_sources_summary_and_csv():
    layout = parse_layout_response(LAYOUT_JSON)
    assert layout.system_id == 424242
    assert layout.inverters[0].mppts[0].strings[0].panels[0].serial == "OPT-A1"

    objects = parse_objects_response(OBJECTS_JSON)
    assert objects[1].datasource == "SOURCE.panels.A1"
    assert objects[1].ui.x == 150

    object_types = parse_object_types_response(OBJECT_TYPES_JSON)
    assert object_types[1].label == "Panel"

    sources = parse_sources_response(SOURCES_JSON)
    assert sources[0].serial == "SOURCE-1"
    assert sources[0].sets[0].set_name == "panels_avg"

    summary = parse_summary_response(SUMMARY_JSON)
    assert summary.daily_energy_dc == 105885.47

    csv_table = parse_csv_table(CSV_TEXT)
    assert csv_table.headers == ["Datetime", "1", "2"]
    assert csv_table.rows[0].values["1"] == 2078.8
    assert csv_table.rows[1].values["1"] is None
    assert csv_table.rows[1].values["2"] == 2060.0
