import logging
from datetime import datetime

import pytest
from test_api_client import TEST_SYSTEM_ID, FakeSession

from pytigo.client import TigoClient
from pytigo.local_client import _parse_iso
from pytigo.models import CLOUD_AGGREGATE_PARAMS


def _client(**kwargs):
    session = FakeSession()
    client = TigoClient("user", "pass", session=session, **kwargs)
    client.login()
    return client, session


@pytest.mark.parametrize("level", ["minute", "min", "day"])
def test_aggregate_accepts_supported_levels_and_sends_them_verbatim(level):
    client, session = _client()
    client.get_aggregate(
        TEST_SYSTEM_ID,
        start="2026-03-31T00:00:00",
        end="2026-03-31T01:00:00",
        level=level,
    )
    assert session.calls[-1][1]["params"]["level"] == level


@pytest.mark.parametrize("level", ["hour", "raw", ""])
def test_aggregate_rejects_unknown_level_before_request(level):
    client, session = _client()
    before = len(session.calls)
    with pytest.raises(ValueError, match="Unsupported level"):
        client.get_aggregate(TEST_SYSTEM_ID, start="a", end="b", level=level)  # type: ignore[arg-type]
    assert len(session.calls) == before


def test_combined_rejects_hour():
    client, _ = _client()
    with pytest.raises(ValueError, match="Unsupported agg"):
        client.get_combined(TEST_SYSTEM_ID, start="a", end="b", agg="hour")  # type: ignore[arg-type]


def test_unknown_param_warns_but_is_sent_by_default(caplog):
    client, session = _client()
    with caplog.at_level(logging.WARNING, logger="pytigo.client"):
        client.get_aggregate(TEST_SYSTEM_ID, start="a", end="b", param="Temp")
    assert session.calls[-1][1]["params"]["param"] == "Temp"
    assert any("Temp" in r.getMessage() for r in caplog.records)


def test_known_params_do_not_warn(caplog):
    client, _ = _client()
    with caplog.at_level(logging.WARNING, logger="pytigo.client"):
        for param in sorted(CLOUD_AGGREGATE_PARAMS):
            client.get_aggregate(TEST_SYSTEM_ID, start="a", end="b", param=param)
    assert not caplog.records


def test_strict_params_raises_for_unknown_param():
    client, session = _client(strict_params=True)
    before = len(session.calls)
    with pytest.raises(ValueError, match="Tmod"):
        client.get_aggregate(TEST_SYSTEM_ID, start="a", end="b", param="Tmod")
    assert len(session.calls) == before


def test_parse_iso_converts_aware_values_to_naive_utc():
    assert _parse_iso("2026-03-31T12:00:00+00:00") == datetime(2026, 3, 31, 12, 0, 0)
    assert _parse_iso("2026-03-31T05:00:00-07:00") == datetime(2026, 3, 31, 12, 0, 0)
    assert _parse_iso("2026-03-31T12:00:00") == datetime(2026, 3, 31, 12, 0, 0)
    assert _parse_iso("not a date") is None
