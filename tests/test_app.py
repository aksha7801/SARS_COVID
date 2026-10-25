from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]


def _app(monkeypatch) -> AppTest:
    monkeypatch.setenv("DASHBOARD_SAMPLE_MODE", "1")
    return AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()


def test_app_renders(monkeypatch) -> None:
    app = _app(monkeypatch)
    assert not app.exception
    assert "Reported COVID-19 deaths versus estimated excess deaths" in app.title[0].value
    assert any("Latest observation: 2021-12-31" in item.value for item in app.caption)


def test_empty_region_filter_shows_message(monkeypatch) -> None:
    app = _app(monkeypatch)
    app.multiselect(key="tracking_regions").set_value([]).run()
    assert any("No observations match" in item.value for item in app.info)


def test_rank_measure_changes_table(monkeypatch) -> None:
    app = _app(monkeypatch)
    before = app.dataframe[0].value.copy()
    app.selectbox(key="rank_measure").set_value("Excess - reported (deaths)").run()
    assert not app.exception
    assert not before.equals(app.dataframe[0].value)


def test_running_total_view_renders_for_several_countries(monkeypatch) -> None:
    app = _app(monkeypatch)
    app.multiselect(key="timeline_countries").set_value(["India", "Brazil", "France"]).run()
    app.radio(key="timeline_measure").set_value("Running total since Jan 2020 (with WHO 95% interval)").run()
    assert not app.exception
