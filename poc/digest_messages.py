#!/usr/bin/env python3
import sys
import os
import re
from datetime import datetime
from dotenv import load_dotenv
from anthropic import Anthropic

def parse_posts(content):
    """Parse the input content into individual posts."""
    delimiter = "--------------------"
    parts = content.split(delimiter)
    
    # First part is the header
    header = parts[0]
    # Subsequent parts are the posts
    posts = parts[1:]
    
    return header, posts

def extract_post_data(post):
    """Extract date, message, and link from a post."""
    lines = post.strip().split('\n')
    
    date_str = None
    message = None
    link = None
    
    for i, line in enumerate(lines):
        if line.startswith('Date: '):
            date_str = line.replace('Date: ', '').strip()
        elif line.startswith('Message: '):
            message = line.replace('Message: ', '').strip()
        elif line.startswith('http'):
            link = line.strip()
    
    return date_str, message, link

def format_date(date_str):
    """Convert date from ISO format to DD.MM.YYYY HH:MM."""
    try:
        # Parse the date string (e.g., "2026-01-01 15:01:25+00:00")
        dt = datetime.fromisoformat(date_str)
        # Format as DD.MM.YYYY HH:MM
        return dt.strftime('%d.%m.%Y %H:%M')
    except Exception as e:
        print(f"Error parsing date {date_str}: {e}", file=sys.stderr)
        return date_str

def generate_title(client, message):
    """Use Claude API to generate a concise one-sentence title."""
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[
                {
                    "role": "user",
                    "content": f"Create a concise one-sentence title (max 15 words) for this news item in Russian. Only return the title, nothing else:\n\n{message}"
                }
            ]
        )
        
        # Extract the text from the response
        title = response.content[0].text.strip()
        # Remove any quotes that might be added
        title = title.strip('"\'')
        return title
    except Exception as e:
        print(f"Error generating title: {e}", file=sys.stderr)
        # Return a truncated version of the message as fallback
        return message[:50] + "..." if len(message) > 50 else message

def main():
    # Load environment variables
    load_dotenv()
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not found in .env file", file=sys.stderr)
        sys.exit(1)
    
    # Initialize Anthropic client
    client = Anthropic(api_key=api_key)
    
    # Read input from STDIN
    content = sys.stdin.read()
    
    if not content:
        return
    
    # Parse posts
    header, posts = parse_posts(content)
    
    # Process each post
    for post in posts:
        if not post.strip():
            continue
        
        date_str, message, link = extract_post_data(post)
        
        if not date_str or not message:
            continue
        
        # Format the date
        formatted_date = format_date(date_str)
        
        # Generate title using Claude
        title = generate_title(client, message)
        
        # Output in the desired format: date – title on first line, link on second, empty line after
        print(f"{formatted_date} – {title}")
        if link:
            print(link)
        else:
            print("(no link)")
        print()  # Empty line after each news item


if __name__ == "__main__":
    main()
