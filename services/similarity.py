from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from services.preprocess import clean_text  

def compute_all_similarities(texts, filenames):

    # clean txt (only for similarity)
    cleaned_texts = [clean_text(t) for t in texts]

    # convert all documents into vectors
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(cleaned_texts)

    # compute similarity matrix
    similarity_matrix = cosine_similarity(tfidf_matrix)

    results = []

    # loop through each file
    for i in range(len(filenames)):

        most_similar_index = -1
        highest_score = 0

        # compare with all other files
        for j in range(len(filenames)):
            if i != j:
                score = similarity_matrix[i][j]

                if score > highest_score:
                    highest_score = score
                    most_similar_index = j

        results.append({
            "file": filenames[i],
            "most_similar": filenames[most_similar_index],
            "similarity": round(highest_score * 100, 2)
        })

    return results