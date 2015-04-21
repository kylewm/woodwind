import bleach
import re

bleach.ALLOWED_TAGS += [
    'a', 'img', 'p', 'br', 'marquee', 'blink',
    'audio', 'video', 'table', 'tbody', 'td', 'tr', 'div', 'span',
    'pre',
]

bleach.ALLOWED_ATTRIBUTES.update({
    'img': ['src', 'alt', 'title'],
    'audio': ['preload', 'controls', 'src'],
    'video': ['preload', 'controls', 'src'],
    'td': ['colspan'],
})


def clean(text):
    """Strip script tags and other possibly dangerous content
    """
    if text is not None:
        text = re.sub('<script.*?</script>', '', text, flags=re.DOTALL)
        return bleach.clean(text, strip=True)
