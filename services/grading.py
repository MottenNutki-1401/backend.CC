from services.spelling import analyze_spelling
from services.grammar import analyze_grammar
from services.similarity import compute_all_similarities

def compute_grades(texts, filenames, weights):

    grammar_weight = weights.get("grammar", 40)
    spelling_weight = weights.get("spelling", 30)
    originality_weight = weights.get("originality", 30)

    # similarity results
    similarity_results = compute_all_similarities(
        texts,
        filenames
    )

    results = []

    for i in range(len(texts)):

        text = texts[i]
        filename = filenames[i]

        # grammar
        grammar_result = analyze_grammar(text, filename)

        grammar_score = grammar_result["score"]

        # spelling
        spelling_result = analyze_spelling(text, filename)

        spelling_score = spelling_result["score"]

        # similarity → originality
        similarity_score = similarity_results[i]["similarity"]

        originality_score = 100 - similarity_score

        # final grade
        final_score = (
            (grammar_score * grammar_weight / 100)
            +
            (spelling_score * spelling_weight / 100)
            +
            (originality_score * originality_weight / 100)
        )

        results.append({
            "file": filename,
            
            "total_words": len(text.split()),

            "grammar": round(grammar_score, 2),

            "spelling": round(spelling_score, 2),

            "originality": round(originality_score, 2),

            "final_score": round(final_score, 2)
        })

    return results