from spellchecker import SpellChecker
import re

spell = SpellChecker()

def clean_text(text):
    # Convert curly apostrophes to normal ones
    text = text.replace("’", "'")

    # Replace dashes
    text = re.sub(r"[—–-]", " ", text)

    # Fix broken words
    for _ in range(2):
        text = re.sub(r"\b(\w)\s+(\w)\b", r"\1\2", text)

    # Extract proper words with contractions
    words = re.findall(r"\b[a-zA-Z]+(?:'[a-zA-Z]+)?\b", text)

    return [word.lower() for word in words]

def analyze_spelling(text, filename):
    all_words = clean_text(text)

    # Count ALL words (correct total)
    total_words = len(all_words)

    #Only filter for spellchecking
    check_words = [w for w in all_words if len(w) > 1]

    misspelled = spell.unknown(check_words)
    print("Misspelled words:", misspelled)

    misspelled_count = len(misspelled)

    score = ((total_words - misspelled_count) / total_words) * 100 if total_words else 0

    return {
        "file": filename,
        "misspelled": misspelled_count,
        "total_words": total_words,
        "score": round(score, 2),
        "misspelled_words": list(misspelled),
        "original_text": text
    }