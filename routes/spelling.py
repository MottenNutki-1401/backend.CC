from fastapi import APIRouter
from services.spelling import analyze_spelling

router = APIRouter()

@router.post("/spelling")
async def get_spelling(data: dict):

    texts = data["texts"]
    filenames = data["files"]

    results = []

    for i in range(len(texts)):
        result = analyze_spelling(texts[i], filenames[i])
        results.append(result)

    return {
        "results": results
    }