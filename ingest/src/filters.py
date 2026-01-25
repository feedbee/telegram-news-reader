
import re
from typing import Dict, Any, Optional
from .config import FiltersConfig, FilterAction

class FilterEngine:
    def __init__(self, config: FiltersConfig):
        self.config = config

    def process_message(self, text: str) -> Optional[str]:
        """
        Apply filters to the message text.
        Returns cleaned text, or None if the message should be dropped.
        Example order: Drop checks first, then replacements/removals.
        This implementation applies filters sequentially. 
        """
        if not text:
            return text

        # 1. Check DROP actions first
        # String Match Drop
        for f in self.config.string:
            if f.action == "drop_message" and f.match and f.match in text:
                return None
        
        # Regex Drop
        for f in self.config.regex:
            if f.action == "drop_message" and f.pattern:
                if re.search(f.pattern, text):
                    return None

        # 2. Apply Replacements / Fragment Removals
        cleaned_text = text
        
        # String Replacements
        for f in self.config.string:
            if f.action == "remove_fragment" and f.match:
                cleaned_text = cleaned_text.replace(f.match, "")
            elif f.action == "replace_fragment" and f.match:
                cleaned_text = cleaned_text.replace(f.match, f.replacement)
        
        # Regex Replacements
        for f in self.config.regex:
            if f.action == "remove_fragment" and f.pattern:
                 cleaned_text = re.sub(f.pattern, "", cleaned_text)
            elif f.action == "replace_fragment" and f.pattern:
                 cleaned_text = re.sub(f.pattern, f.replacement, cleaned_text)

        return cleaned_text.strip()
