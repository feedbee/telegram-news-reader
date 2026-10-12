import json

import pytest

from src.config import Config


@pytest.mark.parametrize("channel_id", ["@news", "-100123456"])
def test_channel_message_limit_override(tmp_path, channel_id):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"channels": [
        {"channel_id": channel_id, "max_messages_per_request": 250},
        {"channel_id": "@default"},
    ]}))
    config = Config(config_path=str(path))
    assert config.get_channel_message_limit(channel_id) == 250
    assert config.get_channel_message_limit("@default") == 100
    assert config.get_channel_message_limit("@unknown") == 100


@pytest.mark.parametrize("value", [0, -1, True, "250", 1.5, None])
def test_invalid_message_limit_uses_default(tmp_path, value):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"channels": [
        {"channel_id": "@news", "max_messages_per_request": value},
    ]}))
    assert Config(config_path=str(path)).get_channel_message_limit("@news") == 100


def test_missing_config_uses_default(tmp_path):
    assert Config(config_path=str(tmp_path / "missing.json")).get_channel_message_limit("@news") == 100


@pytest.mark.parametrize("selection", ["default", "interval", "cursor"])
@pytest.mark.parametrize("interface", ["api", "cli"])
def test_interfaces_apply_channel_override(tmp_path, selection, interface):
    import asyncio
    from fastapi import Response
    from argparse import Namespace
    from importlib import import_module
    from unittest.mock import MagicMock, patch

    path = tmp_path / "config.json"
    path.write_text(json.dumps({"channels": [
        {"channel_id": "@news", "max_messages_per_request": 250},
    ]}))
    config = Config(config_path=str(path))
    with patch("src.storage.Storage"), patch("src.summarizer.Summarizer"):
        module = import_module("src." + interface)
    storage = MagicMock()
    storage.get_messages_by_interval.return_value = []
    storage.get_messages_from_id.return_value = []
    storage.get_total_message_count.return_value = 0
    storage.get_total_message_count_from_id.return_value = 0
    summarizer = MagicMock()
    summarizer.summarize.return_value = "Nothing new"
    from_date = "2026-10-01" if selection == "interval" else None
    last_id = 42 if selection == "cursor" else None
    with patch.object(module, "config", config):
        if interface == "api":
            with patch.object(module, "storage", storage), patch.object(module, "summarizer", summarizer):
                asyncio.run(module.summarize(Response(), "@news", from_date, None, last_id, "JSON"))
        else:
            cli = module.CLI.__new__(module.CLI)
            cli.storage = storage
            cli.summarizer = summarizer
            cli.handle_summarize(Namespace(channel_id="@news", from_date=from_date,
                to_date=None, last_message_id=last_id, format="JSON"))
    method = storage.get_messages_from_id if last_id else storage.get_messages_by_interval
    assert method.call_args.kwargs["limit"] == 250
