from django import template
import re

register = template.Library()

@register.filter(name='youtube_embed_url')
def youtube_embed_url(value):
    """
    Converts a YouTube URL to its embeddable version for iframe.
    Example:
    Input: https://www.youtube.com/watch?v=dQw4w9WgXcQ
    Output: https://www.youtube.com/embed/dQw4w9WgXcQ
    """
    youtube_regex = (
        r'(https?://)?(www\.)?'
        '(youtube|youtu|youtube-nocookie)\.(com|be)/'
        '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')

    match = re.match(youtube_regex, value)
    if match:
        video_id = match.group(6)
        return f'https://www.youtube.com/embed/{video_id}'
    return value
