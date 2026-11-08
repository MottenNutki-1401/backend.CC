import math
import re
from difflib import SequenceMatcher

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from services.preprocess import clean_text


# Keep these thresholds conservative so common short fragments are not surfaced.
MIN_PASSAGE_WORDS = 5
MIN_PASSAGE_CHARS = 30
MIN_NEAR_EXACT_RATIO = 0.80


def _sentence_spans(text):
    """Return sentence-like spans into the original text (end is exclusive)."""
    spans = []
    start = 0
    for boundary in re.finditer(r"(?<=[.!?])\s+|\n+", text):
        end = boundary.start()
        while start < end and text[start].isspace():
            start += 1
        while end > start and text[end - 1].isspace():
            end -= 1
        if start < end:
            spans.append((start, end, text[start:end]))
        start = boundary.end()

    end = len(text)
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    if start < end:
        spans.append((start, end, text[start:end]))
    return spans


def _passage_tokens(text):
    return re.findall(r"\w+", text.casefold())


def _eligible(tokens, text):
    return len(tokens) >= MIN_PASSAGE_WORDS and len(text.strip()) >= MIN_PASSAGE_CHARS


def find_matching_passages(source_text, matched_text):
    """Find exact and near-exact sentence pairs, retaining original-text offsets."""
    source_sentences = _sentence_spans(source_text)
    matched_sentences = _sentence_spans(matched_text)
    matches = []

    for source_start, source_end, source_excerpt in source_sentences:
        source_tokens = _passage_tokens(source_excerpt)
        if not _eligible(source_tokens, source_excerpt):
            continue

        for matched_start, matched_end, matched_excerpt in matched_sentences:
            matched_tokens = _passage_tokens(matched_excerpt)
            if not _eligible(matched_tokens, matched_excerpt):
                continue

            if source_tokens == matched_tokens:
                match_type = "exact"
            else:
                ratio = SequenceMatcher(None, source_tokens, matched_tokens).ratio()
                matcher = SequenceMatcher(None, source_tokens, matched_tokens)
                matching_tokens = sum(block.size for block in matcher.get_matching_blocks())
                required_shared = max(
                    MIN_PASSAGE_WORDS,
                    math.ceil(0.75 * min(len(source_tokens), len(matched_tokens))),
                )
                if ratio < MIN_NEAR_EXACT_RATIO or matching_tokens < required_shared:
                    continue
                match_type = "near_exact"

            matches.append({
                "type": match_type,
                "source": {
                    "start": source_start,
                    "end": source_end,
                    "text": source_excerpt,
                },
                "matched": {
                    "start": matched_start,
                    "end": matched_end,
                    "text": matched_excerpt,
                },
            })

    return matches


# JACCARD SIMILARITY
def jaccard_similarity(text1, text2):

    set1 = set(text1.split())

    set2 = set(text2.split())

    intersection = len(set1.intersection(set2))

    union = len(set1.union(set2))

    if union == 0:
        return 0

    return intersection / union


def compute_all_similarities(texts, filenames):

    # clean txt (only for similarity)
    cleaned_texts = [clean_text(t) for t in texts]

    # TF-IDF + NGRAMS
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2)
    )

    tfidf_matrix = vectorizer.fit_transform(cleaned_texts)

    # COSINE SIMILARITY
    cosine_matrix = cosine_similarity(tfidf_matrix)

    results = []

    # LOOP FILES
    for i in range(len(filenames)):

        most_similar_index = -1

        highest_score = 0

        # compare with other files
        for j in range(len(filenames)):

            if i != j:

                # cosine score
                cosine_score = cosine_matrix[i][j]

                # jaccard score
                jaccard_score = jaccard_similarity(
                    cleaned_texts[i],
                    cleaned_texts[j]
                )

                # COMBINED SCORE
                final_score = (
                    cosine_score * 0.7 +
                    jaccard_score * 0.3
                )

                # highest match
                if final_score > highest_score:

                    highest_score = final_score

                    most_similar_index = j

        # status logic
        if highest_score >= 0.7:
            status = "High Risk"

        elif highest_score >= 0.4:
            status = "Moderate"

        else:
            status = "Safe"

        result = {

            "file": filenames[i],

            "status": status,

            "most_similar":
                filenames[most_similar_index],

            "similarity":
                round(highest_score * 100, 2)
        }
        result["matches"] = (
            find_matching_passages(texts[i], texts[most_similar_index])
            if most_similar_index >= 0 else []
        )
        results.append(result)

    return results
