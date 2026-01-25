#!/usr/bin/env python3
import sys
import os
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
    
    # Collect all news items
    news_items = []
    for post in posts:
        if not post.strip():
            continue
        
        date_str, message, link = extract_post_data(post)
        
        if not date_str or not message:
            continue
        
        news_items.append({
            'date': date_str,
            'message': message,
            'link': link
        })
    
    if not news_items:
        print("No news items found.", file=sys.stderr)
        return
    
    # Prepare the prompt for Claude
    news_text = "\n\n".join([
        f"Дата: {item['date']}\nСообщение: {item['message']}\nСсылка: {item['link'] if item['link'] else 'нет ссылки'}"
        for item in news_items
    ])
    
    prompt = f"""Проанализируй следующие новости и создай краткую сводку на русском языке. 

Требования к сводке:
1. Выдели самые важные события и обязательно укажи ссылки на них
2. Кратко упомяни остальные события
3. Сводка должна быть структурированной и легко читаемой
4. Используй markdown форматирование
5. Ссылки должны быть кликабельными в формате [текст](url)

Новости:

{news_text}"""
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        # Extract and print the summary
        summary = response.content[0].text.strip()
        print(summary)
        
    except Exception as e:
        print(f"Error generating summary: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
