import math
import os
import re
from difflib import SequenceMatcher

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from services.preprocess import clean_text


# Keep these thresholds conservative so common short fragments are not surfaced.
MIN_PASSAGE_WORDS = 5
MIN_PASSAGE_CHARS = 30
MIN_NEAR_EXACT_RATIO = 0.80
SEMANTIC_SIMILARITY_THRESHOLD = float(
    os.getenv("COPYCATCH_SEMANTIC_THRESHOLD", "0.72")
)
SEMANTIC_MODEL_NAME = os.getenv(
    "COPYCATCH_SEMANTIC_MODEL",
    "sentence-transformers/paraphrase-MiniLM-L6-v2",
)
SEMANTIC_BATCH_SIZE = 64

_semantic_model = None


def _get_semantic_model():
    """Load the embedding model on first use so app startup stays lightweight."""
    global _semantic_model
    if _semantic_model is None:
        from sentence_transformers import SentenceTransformer

        _semantic_model = SentenceTransformer(SEMANTIC_MODEL_NAME)
    return _semantic_model


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


def find_paraphrased_passages(
    source_text,
    matched_text,
    threshold=SEMANTIC_SIMILARITY_THRESHOLD,
):
    """Find reciprocal nearest sentence matches using normalized embeddings.

    Spans always come from the original strings, never the scoring-cleaned text.
    """
    source_spans = [
        span for span in _sentence_spans(source_text)
        if _eligible(_passage_tokens(span[2]), span[2])
    ]
    matched_spans = [
        span for span in _sentence_spans(matched_text)
        if _eligible(_passage_tokens(span[2]), span[2])
    ]
    if not source_spans or not matched_spans:
        return []

    model = _get_semantic_model()
    source_embeddings = model.encode(
        [span[2] for span in source_spans],
        batch_size=SEMANTIC_BATCH_SIZE,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    matched_embeddings = model.encode(
        [span[2] for span in matched_spans],
        batch_size=SEMANTIC_BATCH_SIZE,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    # Dot product equals cosine similarity because embeddings are normalized.
    # Process source rows in batches to bound temporary matrix memory.
    best_matched = []
    best_source_scores = []
    best_source = [-1] * len(matched_spans)
    best_matched_scores = [-1.0] * len(matched_spans)
    for offset in range(0, len(source_spans), SEMANTIC_BATCH_SIZE):
        score_batch = source_embeddings[offset:offset + SEMANTIC_BATCH_SIZE] @ matched_embeddings.T
        for row, scores in enumerate(score_batch):
            source_index = offset + row
            matched_index = int(scores.argmax())
            score = float(scores[matched_index])
            best_matched.append(matched_index)
            best_source_scores.append(score)
            if score > best_matched_scores[matched_index]:
                best_matched_scores[matched_index] = score
                best_source[matched_index] = source_index

    matches = []
    for source_index, matched_index in enumerate(best_matched):
        score = best_source_scores[source_index]
        if score < threshold or best_source[matched_index] != source_index:
            continue
        source_span = source_spans[source_index]
        matched_span = matched_spans[matched_index]
        matches.append({
            "type": "paraphrase",
            "similarity": round(score, 4),
            "source": {
                "start": source_span[0],
                "end": source_span[1],
                "text": source_span[2],
            },
            "matched": {
                "start": matched_span[0],
                "end": matched_span[1],
                "text": matched_span[2],
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


def compute_all_similarities(texts, filenames, include_semantic_matches=True):

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
    semantic_match_cache = {}

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
        matches = (
            find_matching_passages(texts[i], texts[most_similar_index])
            if most_similar_index >= 0 else []
        )
        if most_similar_index >= 0 and include_semantic_matches:
            pair_key = tuple(sorted((i, most_similar_index)))
            if pair_key not in semantic_match_cache:
                first, second = pair_key
                semantic_match_cache[pair_key] = find_paraphrased_passages(
                    texts[first], texts[second]
                )
            semantic_matches = semantic_match_cache[pair_key]
            if i != pair_key[0]:
                semantic_matches = [
                    {
                        "type": match["type"],
                        "similarity": match["similarity"],
                        "source": match["matched"],
                        "matched": match["source"],
                    }
                    for match in semantic_matches
                ]
            matches.extend(
                match for match in semantic_matches
                if not any(
                    match["source"]["start"] < existing["source"]["end"]
                    and match["source"]["end"] > existing["source"]["start"]
                    and match["matched"]["start"] < existing["matched"]["end"]
                    and match["matched"]["end"] > existing["matched"]["start"]
                    for existing in matches
                )
            )
        result["matches"] = matches
        # Keep the unmodified extracted text alongside offsets that refer to it.
        # Similarity scoring above continues to use cleaned_texts only.
        result["original_text"] = texts[i]
        result["matched_text"] = (
            texts[most_similar_index] if most_similar_index >= 0 else ""
        )
        results.append(result)

    return results
