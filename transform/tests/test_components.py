
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone, timedelta
from src.summarizer import Summarizer
from src.storage import Storage
from src.config import Config

@pytest.fixture
def mock_config():
    with patch('src.summarizer.config') as mock_cfg:
        mock_cfg.anthropic_api_key = "fake_key"
        mock_cfg.claude_model = "claude-fake"
        mock_cfg.max_tokens = 100
        yield mock_cfg

@pytest.fixture
def mock_anthropic():
    with patch('src.summarizer.Anthropic') as MockAnthropic:
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        yield mock_client

def test_summarize_empty(mock_config, mock_anthropic):
    summarizer = Summarizer()
    result = summarizer.summarize([])
    assert result == "Nothing new"

def test_summarize_success(mock_config, mock_anthropic):
    summarizer = Summarizer()
    
    # Mock successful response
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Summary text")]
    mock_anthropic.messages.create.return_value = mock_response
    
    messages = [
        {"date": "2024-01-01", "cleaned_text": "Msg 1", "url": "http://link1"},
        {"date": "2024-01-02", "cleaned_text": "Msg 2"}
    ]
    
    result = summarizer.summarize(messages)
    assert result == "Summary text"
    
    # Verify proper call
    mock_anthropic.messages.create.assert_called_once()
    call_kwargs = mock_anthropic.messages.create.call_args[1]
    assert call_kwargs["model"] == "claude-fake"
    assert "Msg 1" in call_kwargs["messages"][0]["content"]

@pytest.fixture
def mock_mongo():
    with patch('src.storage.MongoClient') as MockClient:
        mock_db = MagicMock()
        MockClient.return_value.get_database.return_value = mock_db
        yield mock_db

def test_storage_get_messages(mock_mongo):
    storage = Storage()
    mock_collection = mock_mongo["messages"]
    
    # Mock find().sort().limit() chain
    mock_cursor = MagicMock()
    mock_cursor.sort.return_value.limit.return_value = [{"id": 1}, {"id": 2}]
    mock_collection.find.return_value = mock_cursor
    
    result = storage.get_messages_by_interval(
        "@channel", 
        datetime.now(timezone.utc), 
        datetime.now(timezone.utc)
    )
    
    assert len(result) == 2
    mock_collection.find.assert_called_once()

def test_extract_link_empty_text():
    summarizer = Summarizer()
    # Test case for Step 900 fix (AttributeError on None split)
    msg = {"date": "2024-01-01", "cleaned_text": None, "text": None}
    link = summarizer._extract_link(msg)
    assert link == 'нет ссылки'
    
    msg_empty = {"date": "2024-01-01", "cleaned_text": ""}
    assert summarizer._extract_link(msg_empty) == 'нет ссылки'
