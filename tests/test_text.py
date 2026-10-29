from firstreply.text import clean


def test_none_and_empty():
    assert clean(None) == ""
    assert clean("") == ""
    assert clean("   \n\t ") == ""


def test_html_entities_and_tags():
    assert clean("<p>My order &amp; refund</p><br/>") == "My order & refund"


def test_masks_handles_and_links():
    assert clean("@AmazonHelp @UPS where is it? https://t.co/abc") == "where is it? <url>"
    assert clean("thanks @user123 for nothing") == "thanks @user for nothing"


def test_keeps_emoji_and_hinglish():
    assert clean("mera order kab aayega 😡😡") == "mera order kab aayega 😡😡"


def test_very_long_text_is_kept_whole():
    long = "late " * 5000
    assert clean(long) == long.strip()
