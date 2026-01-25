
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone, timedelta
from src.ingester import Ingester
from src.config import AppConfig, ChannelConfig, FiltersConfig

# Sample Config
@pytest.fixture
def mock_config():
    return AppConfig(
        api_id=123,
        api_hash="abc",
        phone="123",
        mongo_uri="mongodb://mock",
        session_file="mock.session",
        channels=[ChannelConfig(channel_id="@test_channel", name="Test Channel")],
        filters=FiltersConfig()
    )

# Sample Message
@pytest.fixture
def mock_message():
    message = MagicMock()
    message.id = 100
    message.text = "Hello World"
    message.date = datetime.now(timezone.utc)
    message.sender_id = 999
    message.chat_id = 123456
    message.forward = None
    message.reply_to = None
    return message

@pytest.fixture
def mock_telethon_client():
    client = MagicMock()
    client.start = AsyncMock()
    client.stop = AsyncMock()
    client.run_until_disconnected = AsyncMock()
    client.get_entity = AsyncMock(return_value=MagicMock(username="test_channel", id=123456))
    
    # Mock iter_messages to return an async iterator
    async def async_iter(messages):
        for msg in messages:
            yield msg

    client.iter_messages = MagicMock(side_effect=lambda entity, **kwargs: async_iter(kwargs.get('messages', [])))
    
    # Mock the 'on' decorator
    def on_decorator(event_builder):
        def decorator(handler):
            return handler
        return decorator
    client.on = MagicMock(side_effect=on_decorator)
    
    return client

@pytest.fixture
def mock_storage():
    storage = MagicMock()
    storage.save_message = MagicMock()
    storage.delete_message = MagicMock()
    storage.get_checkpoint = MagicMock(return_value=0)
    storage.update_checkpoint = MagicMock()
    storage.get_latest_message_id = MagicMock(return_value=50)
    return storage

@pytest.fixture
def ingester(mock_config, mock_telethon_client, mock_storage):
    with patch('src.ingester.TelegramClientWrapper') as MockWrapper, \
         patch('src.ingester.Storage', return_value=mock_storage) as MockStorage:
        
        MockWrapper.return_value.get_client.return_value = mock_telethon_client
        
        ing = Ingester(mock_config)
        return ing

@pytest.mark.asyncio
async def test_run_realtime_happy_path(ingester, mock_telethon_client):
    """
    Test starting realtime mode registers handlers and waits for disconnect.
    """
    await ingester.run_realtime(catch_up=False)
    
    # Check if client started listening
    mock_telethon_client.run_until_disconnected.assert_called_once()
    assert mock_telethon_client.on.called
    
    # Capture the handler (this is a bit simplified, usually we'd capture args to .on)
    # Since we mocked .on to just return the function, we can't easily trigger it via the mock object directly
    # without more complex mocking. But verifying setup is the main "happy path" for starting the runner.
    
    # Verify catch-up was NOT called
    ingester.storage.get_latest_message_id.assert_not_called()


@pytest.mark.asyncio
async def test_run_backfill_happy_path(ingester, mock_telethon_client, mock_message):
    """
    Test backfill mode iterates messages and saves them.
    """
    # Setup mock messages
    messages = [mock_message, mock_message]
    
    # We need to properly mock iter_messages to return our list
    async def async_iter(*args, **kwargs):
        for msg in messages:
            yield msg
            
    mock_telethon_client.iter_messages = MagicMock(side_effect=async_iter)

    await ingester.run_backfill()

    # Verifications
    mock_telethon_client.get_entity.assert_called_with("@test_channel")
    # Should call get_checkpoint
    ingester.storage.get_checkpoint.assert_called_with("@test_channel")
    # Should iterate messages
    assert mock_telethon_client.iter_messages.called
    # Should save messages (2 messages)
    assert ingester.storage.save_message.call_count == 2
    # Should update checkpoint
    assert ingester.storage.update_checkpoint.called


@pytest.mark.asyncio
async def test_run_interval_happy_path(ingester, mock_telethon_client, mock_message):
    """
    Test interval mode filters messages by date.
    """
    # Create messages: one inside range, one outside (older), one outside (newer)
    now = datetime.now(timezone.utc)
    
    msg_in = MagicMock()
    msg_in.id = 1
    msg_in.text = "Inside"
    msg_in.date = now - timedelta(hours=2)
    
    msg_old = MagicMock()
    msg_old.id = 2
    msg_old.text = "Old"
    msg_old.date = now - timedelta(hours=10)
    
    msg_new = MagicMock()
    msg_new.id = 3
    msg_new.text = "New"
    msg_new.date = now + timedelta(hours=1) # Future message?

    # Target interval: 5 hours ago to 1 hour ago
    start_date = now - timedelta(hours=5)
    end_date = now - timedelta(hours=1)

    # iter_messages usually yields from newest to oldest by default
    messages = [msg_new, msg_in, msg_old]

    async def async_iter(*args, **kwargs):
        for msg in messages:
            yield msg
            
    mock_telethon_client.iter_messages = MagicMock(side_effect=async_iter)

    await ingester.run_interval(start_date=start_date, end_date=end_date)

    # Verification
    # msg_new should be skipped (date > end_date)
    # msg_in should be processed
    # msg_old should cause loop break (date < start_date)
    
    # Only msg_in should be saved
    # Note: Logic in ingester calls save_message.
    # Logic trace:
    # 1. msg_new: date > end_date -> continue (not saved)
    # 2. msg_in: date within range -> process -> save_message called (count=1)
    # 3. msg_old: date < start_date -> break loop
    
    assert ingester.storage.save_message.call_count == 1
    saved_arg = ingester.storage.save_message.call_args[0][0]
    assert saved_arg["cleaned_text"] == "Inside"
