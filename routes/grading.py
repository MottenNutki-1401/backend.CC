from fastapi import APIRouter
from services.grading import compute_grades

router = APIRouter()

@router.post("/grading")
async def grading_endpoint(data: dict):

    texts = data.get("texts", [])
    filenames = data.get("files", [])
    weights = data.get("weights", {})

    results = compute_grades(
        texts,
        filenames,
        weights
    )

    return {
        "results": results
    }