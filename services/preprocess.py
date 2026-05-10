import re

def clean_text(text):
    # lowercase
    text = text.lower()

    # remove punctuation
    text = re.sub(r"[^\w\s]", "", text)

    # remove extra spaces
    text = re.sub(r"\s+", " ", text).strip()

    return text