import importlib
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def api():
    with patch("src.storage.Storage"), patch("src.summarizer.Summarizer"):
        module = importlib.import_module("src.api")
    module.storage.get_total_message_count.return_value = 1
    module.storage.get_messages_by_interval.return_value = [
        {"message_id": 42, "date": datetime(2026, 9, 6, tzinfo=timezone.utc), "cleaned_text": "News"}
    ]
    module.summarizer.summarize.return_value = "# Summary"
    with TestClient(module.app) as client:
        yield client


@pytest.mark.parametrize("query", ["", "?channel_id=@news&format=HTML"])
def test_invalid_query_is_rejected(api, query):
    assert api.get("/summarize" + query).status_code == 422


def test_markdown_response_includes_cursor(api):
    response = api.get("/summarize?channel_id=@news")
    assert response.status_code == 200
    assert response.text == "# Summary"
    assert response.headers["content-type"].startswith("text/markdown")
    assert response.headers["X-META-LAST-MESSAGE-ID"] == "42"


def test_json_response_preserves_metadata(api):
    response = api.get("/summarize?channel_id=@news&format=JSON")
    assert response.status_code == 200
    body = response.json()
    assert body["summary"] == "# Summary"
    assert body["last_message_id"] == 42
    assert body["messages"] == {"total": 1, "processed": 1}
