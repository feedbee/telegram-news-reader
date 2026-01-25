import sys

def cleanup():
    # Read entire input from STDIN
    content = sys.stdin.read()
    
    if not content:
        return

    delimiter = "--------------------"
    parts = content.split(delimiter)
    
    # The first part is the header (content before the first delimiter)
    header = parts[0]
    # Subsequent parts are the posts
    posts = parts[1:]
    
    ad_line = "[Работа](https://t.me/rabotawarszawa) | [Прислать новость](https://t.me/thewarsawbot) | [Заказать рекламу](https://t.me/thewarsawad)"
    
    cleaned_posts = []
    for post in posts:
        # Check for promotional posts
        if "#промо" in post:
            continue
            
        # Remove the specific advertisement line and the following newline
        # We look for the ad line followed by \n or \r\n
        target = ad_line + "\n"
        if target in post:
            post = post.replace(target, "")
        else:
            # Try with \r\n just in case
            target = ad_line + "\r\n"
            if target in post:
                post = post.replace(target, "")
            else:
                # If it's the last line without a newline, just remove it
                if ad_line in post:
                    post = post.replace(ad_line, "")
        
        cleaned_posts.append(post)
    
    # Output the header
    sys.stdout.write(header)
    
    # Output the remaining posts, each preceded by the delimiter
    for post in cleaned_posts:
        sys.stdout.write(delimiter)
        sys.stdout.write(post)

if __name__ == "__main__":
    cleanup()
