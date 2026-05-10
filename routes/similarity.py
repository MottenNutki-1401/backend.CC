from fastapi import APIRouter
from services.similarity import compute_all_similarities

router = APIRouter()

@router.post("/similarity")
async def get_similarity(data: dict):

    texts = data["texts"]
    filenames = data["files"]

    results = compute_all_similarities(texts, filenames)

    return {
        "results": results
    }