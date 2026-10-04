import importlib
import json
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import firebase_admin
import httpx
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def gateway(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    firebase_app = firebase_admin.initialize_app(options={"projectId": "test-project"})
    with patch("storage.MongoClient"):
        sys.modules.pop("main", None)
        main = importlib.import_module("main")
    with TestClient(main.app) as client:
        yield main, client
    main.app.dependency_overrides.clear()
    firebase_admin.delete_app(firebase_app)


def test_health_and_runtime_config(gateway):
    main, client = gateway
    assert client.get("/health").json() == {"status": "ok"}
    response = client.get("/config.js")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/javascript")
    assert response.text == f"window.FIREBASE_CONFIG = {json.dumps(main.FIREBASE_CONFIG)};"


def test_channels_require_authentication(gateway):
    _, client = gateway
    assert client.get("/api/channels").status_code == 401


def test_verified_user_can_list_active_channels(gateway, tmp_path):
    main, client = gateway
    channels = [{"channel_id": "@active"}, {"channel_id": "@hidden", "is_active": False}]
    (tmp_path / "config.json").write_text(json.dumps({"channels": channels}))
    with patch("auth.auth.verify_id_token", return_value={"uid": "reader"}):
        response = client.get("/api/channels", headers={"Authorization": "Bearer test-token"})
    assert response.status_code == 200
    assert response.json() == [channels[0]]


def test_invalid_token_is_rejected(gateway):
    _, client = gateway
    with patch("auth.auth.verify_id_token", side_effect=ValueError("invalid token")):
        response = client.get("/api/channels", headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401


def test_summary_proxy_preserves_body_and_updates_cursor(gateway):
    main, client = gateway
    main.app.dependency_overrides[main.get_current_user] = lambda: {"uid": "reader"}
    main.storage = MagicMock()
    main.storage.get_user_metadata.return_value = {"last_message_ids": {"@news": 10}}
    upstream = AsyncMock()
    upstream.get.return_value = httpx.Response(
        200, text="# Summary", headers={"content-type": "text/markdown", "X-META-LAST-MESSAGE-ID": "20"}
    )
    with patch.object(main.httpx, "AsyncClient") as factory:
        factory.return_value.__aenter__.return_value = upstream
        response = client.get("/api/summarize?channel_id=@news")
    assert response.status_code == 200
    assert response.text == "# Summary"
    assert response.headers["X-META-LAST-MESSAGE-ID"] == "20"
    assert upstream.get.call_args.kwargs["params"]["last_message_id"] == "10"
    factory.assert_called_once_with(timeout=main.TRANSFORM_TIMEOUT_SECONDS)
    assert main.TRANSFORM_TIMEOUT_SECONDS == 120.0
    main.storage.update_user_metadata.assert_called_once_with("reader", "last_message_ids.@news", 20)


def test_sync_returns_user_metadata(gateway):
    main, client = gateway
    main.app.dependency_overrides[main.get_current_user] = lambda: {"uid": "reader"}
    main.storage.upsert_user = MagicMock(return_value={"metadata": {"last_message_ids": {"@news": 20}}})
    response = client.post("/api/users/sync")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "metadata": {"last_message_ids": {"@news": 20}}}
