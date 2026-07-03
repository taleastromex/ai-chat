"""Unit tests for AppState."""

from app.enums import ModelStatus
from app.state import AppState


def test_initial_state_is_starting() -> None:
    state = AppState()
    assert state.status is ModelStatus.STARTING
    assert not state.is_ready
    assert state.error == ""
    assert state.progress == ""


def test_set_updates_status() -> None:
    state = AppState()
    state.set(ModelStatus.READY)
    assert state.status is ModelStatus.READY
    assert state.is_ready


def test_set_records_error_without_clearing_on_subsequent_calls() -> None:
    state = AppState()
    state.set(ModelStatus.ERROR, error="boom")
    assert state.error == "boom"

    # A later transition without an explicit error keeps the last one around
    state.set(ModelStatus.PULLING)
    assert state.error == "boom"


def test_set_records_progress() -> None:
    state = AppState()
    state.set(ModelStatus.PULLING, progress="downloading (42.0%)")
    assert state.progress == "downloading (42.0%)"
