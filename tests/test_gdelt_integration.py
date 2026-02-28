import io
import zipfile

import pytest

from mitigation_module.gdelt_service import GDELTService
from mitigation_module import dynamic_network as dn
from mitigation_module.mitigation_solver import solve_guardian_plan


class _MockResponse:
    def __init__(self, text="", content=b"", status_code=200):
        self.text = text
        self.content = content
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP error: {self.status_code}")


@pytest.fixture(autouse=True)
def _reset_dynamic_routes():
    dn.reset_dynamic_routes()
    yield
    dn.reset_dynamic_routes()


def _build_gkg_zip() -> bytes:
    tsv_data = (
        "DATE\tV2Themes\tV2Locations\tDocumentIdentifier\n"
        "20260228000000\tTRANSPORTATION,PORT\t"
        "1#Mumbai#IN#IN16#19.0760#72.8777#123#Mumbai;"
        "1#Navi Mumbai#IN#IN16#19.0330#73.0297#456#Navi Mumbai\t"
        "https://example.com/article-1\n"
        "20260228001500\tSPORTS\t1#Boston#US#USMA#42.3601#-71.0589#111#Boston\t"
        "https://example.com/article-2\n"
    )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr("sample.gkg.csv", tsv_data)
    return buffer.getvalue()


def test_gdelt_pipeline_fetches_and_filters_disruptions(monkeypatch):
    service = GDELTService(cache_ttl_seconds=120)

    master_text = (
        "123 100 http://data.gdeltproject.org/gdeltv2/20260228000000.gkg.csv.zip\n"
    )
    zipped_payload = _build_gkg_zip()

    def _mock_get(url, timeout):
        if "masterfilelist" in url:
            return _MockResponse(text=master_text)
        if url.endswith(".zip"):
            return _MockResponse(content=zipped_payload)
        raise AssertionError(f"Unexpected URL fetched: {url}")

    monkeypatch.setattr(service.session, "get", _mock_get)

    events = service.get_disruptions_from_gdelt(force_refresh=True)

    assert events, "Expected at least one disruption event from mocked GDELT feed"
    assert any("TRANSPORTATION" in event.get("themes", []) for event in events)

    mumbai_risk = service.get_city_risk("Mumbai")
    assert mumbai_risk is not None
    assert mumbai_risk["source"] == "gdelt"
    assert mumbai_risk["multiplier"] >= 10.0


def test_gdelt_cache_reduces_network_calls(monkeypatch):
    service = GDELTService(cache_ttl_seconds=120)
    zipped_payload = _build_gkg_zip()

    calls = {"count": 0}

    def _mock_get(url, timeout):
        calls["count"] += 1
        if "masterfilelist" in url:
            return _MockResponse(
                text="123 100 http://data.gdeltproject.org/gdeltv2/20260228000000.gkg.csv.zip\n"
            )
        return _MockResponse(content=zipped_payload)

    monkeypatch.setattr(service.session, "get", _mock_get)

    first = service.get_disruptions_from_gdelt(force_refresh=True)
    second = service.get_disruptions_from_gdelt(force_refresh=False)

    assert first == second
    assert calls["count"] == 2, "Expected only master+zip fetch once due to cache"


def test_solver_prefers_live_gdelt_risk_when_enabled(monkeypatch):
    class _StubGdelt:
        def get_city_risk(self, city_name):
            return {
                "city": city_name,
                "multiplier": 20.0,
                "reason": f"ENV_FLOOD signal in {city_name}",
                "source": "gdelt",
            }

    monkeypatch.setattr(
        "mitigation_module.mitigation_solver.scan_news_for_risk",
        lambda city_name: {
            "city": city_name,
            "multiplier": 2.0,
            "reason": "fallback static risk",
            "source": "static",
        },
    )

    _, _, risk_info, destination, _ = solve_guardian_plan(
        "Ship 200 units to Boston",
        use_live_gdelt=True,
        gdelt_service=_StubGdelt(),
    )

    assert destination == "Boston"
    assert "Source: GDELT" in risk_info
    assert "20.0x" in risk_info


def test_solver_falls_back_to_static_monitor_when_live_returns_none(monkeypatch):
    class _StubGdelt:
        def get_city_risk(self, city_name):
            return None

    monkeypatch.setattr(
        "mitigation_module.mitigation_solver.scan_news_for_risk",
        lambda city_name: {
            "city": city_name,
            "multiplier": 5.0,
            "reason": "STRIKE reported in static monitor",
            "source": "static",
        },
    )

    _, _, risk_info, destination, _ = solve_guardian_plan(
        "Ship 100 units to Chicago",
        use_live_gdelt=True,
        gdelt_service=_StubGdelt(),
    )

    assert destination == "Chicago"
    assert "Source: STATIC" in risk_info
    assert "5.0x" in risk_info
