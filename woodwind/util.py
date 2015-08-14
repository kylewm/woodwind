import bleach
import re
import requests

bleach.ALLOWED_TAGS += [
    'a', 'img', 'p', 'br', 'marquee', 'blink',
    'audio', 'video', 'table', 'tbody', 'td', 'tr', 'div', 'span',
    'pre', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
]

bleach.ALLOWED_ATTRIBUTES.update({
    'img': ['src', 'alt', 'title'],
    'audio': ['preload', 'controls', 'src'],
    'video': ['preload', 'controls', 'src'],
    'td': ['colspan'],
})

USER_AGENT = 'Woodwind (https://github.com/kylewm/woodwind)'


def requests_get(url, **kwargs):
    kwargs.setdefault('headers', {})['User-Agent'] = USER_AGENT
    return requests.get(url, **kwargs)

    
def clean(text):
    """Strip script tags and other possibly dangerous content
    """
    if text is not None:
        text = re.sub('<script.*?</script>', '', text, flags=re.DOTALL)
        return bleach.clean(text, strip=True)
