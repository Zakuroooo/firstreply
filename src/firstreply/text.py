"""Text cleaning shared by every model, so the comparison is fair."""
import html
import re

MENTION = re.compile(r"@\w+")
URL = re.compile(r"https?://\S+")
TAG = re.compile(r"<[^>]+>")
SPACE = re.compile(r"\s+")


def clean(text):
    """Make a ticket safe and tidy: decode HTML entities, drop HTML tags, mask @handles and links."""
    if text is None:
        return ""
    text = html.unescape(str(text))
    text = TAG.sub(" ", text)
    text = URL.sub("<url>", text)
    text = MENTION.sub("@user", text)
    text = SPACE.sub(" ", text).strip()
    # leading "@user @user ..." carries no meaning
    text = re.sub(r"^(@user\s*)+", "", text).strip()
    return text
