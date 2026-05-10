from fastapi import APIRouter
from services.grammar import analyze_grammar

router = APIRouter()

@router.post("/grammar")
async def grammar_endpoint(data: dict):
    texts = data.get("texts", [])
    filenames = data.get("files", [])

    results = []

    for i in range(len(texts)):
        result = analyze_grammar(texts[i], filenames[i])
        results.append(result)

    return {
        "results": results
    }