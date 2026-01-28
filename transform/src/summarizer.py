
import logging
from typing import List, Dict, Any, Optional
from anthropic import Anthropic, APIError
from .config import config

logger = logging.getLogger(__name__)

class Summarizer:
    def __init__(self):
        if not config.anthropic_api_key:
            logger.warning("ANTHROPIC_API_KEY is not set. Summarization will fail.")
            self.client = None
        else:
            self.client = Anthropic(api_key=config.anthropic_api_key)

    def summarize(self, messages: List[Dict[str, Any]], channel_id: Optional[str] = None) -> str:
        """
        Summarize a list of messages using Claude.
        """
        if not messages:
            return "Nothing new" # Graceful return for empty input

        if not self.client:
            return "Error: Anthropic API key is missing. Cannot generate summary."

        # 1. Get Prompt from Config or Fallback
        prompt_template = None
        if channel_id:
            prompt_template = config.get_channel_prompt(channel_id)
        
        if not prompt_template:
            prompt_template = (
                "Analyze the following news and create a brief summary.\n\n"
                "Requirements:\n"
                "1. Highlight the most important events and include links\n"
                "2. Briefly mention other events\n"
                "3. Use markdown formatting and clickable links [text](url)\n\n"
                "News:\n\n"
                "{news_text}"
            )

        # 2. Format messages for the prompt
        # We use generic labels here, but the prompt template might expect specific ones.
        # Historically we used Russian labels. Let's stick to them if it's the Russian prompt,
        # but generic ones are safer for a template.
        # However, the user's prompt in config actually HAS {news_text} placeholder.
        
        news_entries = []
        for msg in messages:
            date = msg.get('date')
            text = msg.get('cleaned_text') or msg.get('text') or "[No text]"
            link = self._extract_link(msg)
            news_entries.append(f"Date: {date}\nMessage: {text}\nLink: {link}")
        
        news_text = "\n\n".join(news_entries)
        
        # 3. Final Prompt
        try:
            prompt = prompt_template.format(news_text=news_text)
        except KeyError:
            # Fallback if {news_text} is missing in template
            prompt = prompt_template + "\n\n" + news_text

        try:
            response = self.client.messages.create(
                model=config.claude_model,
                max_tokens=config.max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            return response.content[0].text.strip()

        except APIError as e:
            logger.error(f"Anthropic API Error: {e}")
            return f"Error generating summary: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error during summarization: {e}")
            return f"Error processing request: {str(e)}"

    def _extract_link(self, message: Dict[str, Any]) -> str:
        """
        Best-effort link extraction. 
        In ingest we store detailed structure, but simply looking for http/https is a robust fallback
        if specific fields aren't populated.
        """
        # If the message object has a specific url field (depends on ingest implementation details)
        # For now, let's assume we might find it in text or return 'нет ссылки'
        # Ideally, ingest should parse and store main link. 
        # Checking 'url' field if it exists, otherwise scan text.
        
        # Check explicit fields first (if your ingest stores them)
        if message.get('url'):
            return message['url']
            
        # Scan text for first http link (naive implementation similar to PoC)
        text = message.get('cleaned_text') or message.get('text', '')
        if not text:
            return 'нет ссылки'
            
        words = text.split()
        for word in words:
            if word.startswith('http://') or word.startswith('https://'):
                return word
                
        return 'нет ссылки'
