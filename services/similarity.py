from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from services.preprocess import clean_text


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

        results.append({

            "file": filenames[i],

            "status": status,

            "most_similar":
                filenames[most_similar_index],

            "similarity":
                round(highest_score * 100, 2)
        })

    return results