"""Tests for /health, /info, and /ready."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.dependencies import get_state
from app.enums import ModelStatus
from app.state import AppState


def test_health_reports_not_ready_by_default(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200

    body = response.json()
    assert body["model_loaded"] is False
    assert body["model_status"] == ModelStatus.STARTING.value


def test_health_reports_ready(app: FastAPI, client: TestClient, state: AppState) -> None:
    app.dependency_overrides[get_state] = lambda: state
    state.set(ModelStatus.READY)

    response = client.get("/health")
    body = response.json()

    assert body["status"] == "ok"
    assert body["model_loaded"] is True


def test_info_returns_configured_model(client: TestClient) -> None:
    response = client.get("/info")
    assert response.status_code == 200

    body = response.json()
    assert body["model_id"] == "test-model:latest"
    assert body["backend"] == "ollama"


def test_ready_returns_503_while_loading(client: TestClient) -> None:
    response = client.get("/ready")
    assert response.status_code == 503


def test_ready_returns_200_once_ready(app: FastAPI, client: TestClient, state: AppState) -> None:
    app.dependency_overrides[get_state] = lambda: state
    state.set(ModelStatus.READY)

    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"ready": True}


def test_ready_returns_500_on_error(app: FastAPI, client: TestClient, state: AppState) -> None:
    app.dependency_overrides[get_state] = lambda: state
    state.set(ModelStatus.ERROR, error="pull failed: disk full")

    response = client.get("/ready")
    assert response.status_code == 500
    assert "disk full" in response.json()["detail"]
